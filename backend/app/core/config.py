from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    PROJECT_NAME: str = "CollabFlow"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Cookie settings
    COOKIE_SECURE: bool = False  # Override in production
    COOKIE_SAMESITE: str = "lax"  # Override in production to "strict"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 7  # 7 days
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()
