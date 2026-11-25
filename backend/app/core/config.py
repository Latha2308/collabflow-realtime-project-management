from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union
from pydantic import field_validator, model_validator
from urllib.parse import urlparse
import re


class Settings(BaseSettings):
    """Application settings"""
    
    PROJECT_NAME: str = "CollabFlow"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (production-safe)
    
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Cookie settings
    COOKIE_SECURE: bool = False  # Override in production
    COOKIE_SAMESITE: str = "lax"  # Override in production to "strict"
    COOKIE_MAX_AGE: int = 60 * 60  # 1 hour (matches token expiration)
    
    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def get_cookie_secure(self) -> bool:
        """Get secure cookie flag based on environment"""
        if self.ENVIRONMENT == "production":
            return True
        return self.COOKIE_SECURE
    
    def get_cookie_samesite(self) -> str:
        """Get SameSite policy based on environment"""
        if self.ENVIRONMENT == "production":
            return "strict"
        return self.COOKIE_SAMESITE
    
    @model_validator(mode='after')
    def validate_production_secrets(self):
        """
        Validate secrets are secure in production environment.
        Uses model_validator to ensure ENVIRONMENT is available.
        """
        if self.ENVIRONMENT != "production":
            # Skip validation in development/staging
            return self
        
        # Validate SECRET_KEY
        secret_key = self.SECRET_KEY
        
        # Known insecure patterns
        insecure_patterns = [
            'dev',
            'test',
            'demo',
            'example',
            'sample',
            'changeme',
            'change_me',
            'replace',
            'placeholder',
            'insecure',
            'default',
        ]
        
        secret_lower = secret_key.lower()
        for pattern in insecure_patterns:
            if pattern in secret_lower:
                raise ValueError(
                    f"SECRET_KEY contains placeholder pattern in production environment. "
                    f"Generate a secure random key with: openssl rand -base64 64"
                )
        
        # Check minimum length (64 chars = 512 bits minimum)
        if len(secret_key) < 64:
            raise ValueError(
                f"SECRET_KEY is too short for production ({len(secret_key)} characters). "
                f"Minimum 64 characters required. Generate with: openssl rand -base64 64"
            )
        
        # Validate DATABASE_URL password
        try:
            parsed = urlparse(self.DATABASE_URL)
            db_password = parsed.password
            
            if not db_password:
                raise ValueError(
                    "DATABASE_URL missing password in production environment"
                )
            
            # Check password against insecure patterns
            password_lower = db_password.lower()
            for pattern in insecure_patterns:
                if pattern in password_lower:
                    raise ValueError(
                        "Database password contains placeholder pattern in production environment. "
                        "Use a strong random password (minimum 32 characters)"
                    )
            
            # Check common weak passwords
            common_weak = ['password', 'admin', '123456', 'secret', 'root']
            for weak in common_weak:
                if weak in password_lower:
                    raise ValueError(
                        "Database password contains common weak pattern in production environment. "
                        "Use a strong random password (minimum 32 characters)"
                    )
            
            # Check minimum length
            if len(db_password) < 20:
                raise ValueError(
                    f"Database password is too short for production ({len(db_password)} characters). "
                    f"Minimum 20 characters required"
                )
        
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception:
            # If URL parsing fails, raise generic error without exposing URL
            raise ValueError(
                "DATABASE_URL format is invalid. Expected: postgresql://user:password@host:port/database"
            )
        
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()
