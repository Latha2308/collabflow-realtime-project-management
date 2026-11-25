"""
Tests for production security configuration validation.
Ensures weak secrets are rejected in production mode.
"""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


class TestProductionSecretKeyValidation:
    """Test SECRET_KEY validation in production mode"""
    
    def test_production_rejects_placeholder_patterns(self):
        """Production should reject SECRET_KEY with placeholder patterns"""
        insecure_keys = [
            'dev_secret_key_at_least_32_chars_long_for_jwt_signing',
            'test_secret_key_for_automated_testing_1234567890123456789012',
            'demo_key_replace_this_with_real_value_12345678901234567890123',
            'example_secret_key_change_me_123456789012345678901234567890',
            'sample_key_not_for_production_use_1234567890123456789012345',
            'changeme_secret_key_12345678901234567890123456789012345678901',
            'default_secret_key_1234567890123456789012345678901234567890123',
            'placeholder_key_1234567890123456789012345678901234567890123456',
            'replace_this_secret_123456789012345678901234567890123456789012',
        ]
        
        for key in insecure_keys:
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    DATABASE_URL="postgresql://user:strongrandompassword123456@localhost/db",
                    SECRET_KEY=key,
                    ENVIRONMENT="production"
                )
            
            error_msg = str(exc_info.value).lower()
            assert "placeholder" in error_msg or "openssl" in error_msg
    
    def test_production_rejects_docker_compose_default(self):
        """Production should reject docker-compose.yml default SECRET_KEY"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user:strongrandompassword123456@localhost/db",
                SECRET_KEY="local_dev_only_insecure_key_min_64_chars_replace_in_production_now",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "placeholder" in error_msg or "insecure" in error_msg
    
    def test_production_rejects_short_secret_key(self):
        """Production should reject SECRET_KEY shorter than 64 characters"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user:strongrandompassword123456@localhost/db",
                SECRET_KEY="short_key_12345",  # Only 17 characters
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "too short" in error_msg or "64" in error_msg
    
    def test_production_accepts_secure_secret_key(self):
        """Production should accept properly generated SECRET_KEY"""
        # Simulate openssl rand -base64 64 output (88 characters)
        secure_key = "X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m"
        
        settings = Settings(
            DATABASE_URL="postgresql://user:Kj8Hf92Lp3Mn5Qr7St9W@localhost/db",
            SECRET_KEY=secure_key,
            ENVIRONMENT="production"
        )
        
        assert settings.SECRET_KEY == secure_key
        assert settings.ENVIRONMENT == "production"
    
    def test_development_accepts_any_secret_key(self):
        """Development mode should accept any SECRET_KEY (no validation)"""
        settings = Settings(
            DATABASE_URL="postgresql://user:password@localhost/db",
            SECRET_KEY="dev_key",  # Short, insecure, but OK in development
            ENVIRONMENT="development"
        )
        
        assert settings.SECRET_KEY == "dev_key"
        assert settings.ENVIRONMENT == "development"


class TestProductionDatabasePasswordValidation:
    """Test DATABASE_URL password validation in production mode"""
    
    def test_production_rejects_placeholder_database_passwords(self):
        """Production should reject database passwords with placeholder patterns"""
        insecure_urls = [
            "postgresql://collabflow:dev_password@localhost/db",
            "postgresql://user:test_password_123@localhost/db",
            "postgresql://user:demo_pass_123456789@localhost/db",
            "postgresql://user:example_password_12@localhost/db",
            "postgresql://user:sample_pass_1234567@localhost/db",
            "postgresql://user:changeme_12345678901@localhost/db",
            "postgresql://user:default_pass_123456@localhost/db",
            "postgresql://user:placeholder_12345@localhost/db",
            "postgresql://user:replace_this_12345@localhost/db",
        ]
        
        secure_key = "X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m"
        
        for url in insecure_urls:
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    DATABASE_URL=url,
                    SECRET_KEY=secure_key,
                    ENVIRONMENT="production"
                )
            
            error_msg = str(exc_info.value).lower()
            assert "placeholder" in error_msg or "password" in error_msg
            # Ensure actual password is NOT in error message
            assert "dev_password" not in error_msg
            assert "test_password" not in error_msg
    
    def test_production_rejects_common_weak_passwords(self):
        """Production should reject common weak database passwords"""
        weak_urls = [
            "postgresql://user:password@localhost/db",
            "postgresql://user:password123@localhost/db",
            "postgresql://user:admin123456789012@localhost/db",
            "postgresql://user:secret123456789012@localhost/db",
            "postgresql://user:root12345678901234@localhost/db",
            "postgresql://user:123456789012345678901@localhost/db",
        ]
        
        secure_key = "X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m"
        
        for url in weak_urls:
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    DATABASE_URL=url,
                    SECRET_KEY=secure_key,
                    ENVIRONMENT="production"
                )
            
            error_msg = str(exc_info.value).lower()
            assert "weak" in error_msg or "password" in error_msg or "common" in error_msg
    
    def test_production_rejects_docker_compose_database_default(self):
        """Production should reject docker-compose.yml default database password"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://collabflow:local_dev_only_not_for_production@postgres:5432/collabflow_db",
                SECRET_KEY="X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "placeholder" in error_msg or "dev" in error_msg
    
    def test_production_rejects_short_database_password(self):
        """Production should reject database passwords shorter than 20 characters"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user:shortpass@localhost/db",
                SECRET_KEY="X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "too short" in error_msg or "20" in error_msg
    
    def test_production_rejects_missing_database_password(self):
        """Production should reject DATABASE_URL without password"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user@localhost/db",
                SECRET_KEY="X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "missing password" in error_msg or "password" in error_msg
    
    def test_production_accepts_secure_database_password(self):
        """Production should accept strong random database password"""
        secure_url = "postgresql://collabflow:Kj8Hf92Lp3Mn5Qr7St9Wv1Xz3Bc5Df7Gh9Jk1@postgres:5432/collabflow_db"
        secure_key = "X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m"
        
        settings = Settings(
            DATABASE_URL=secure_url,
            SECRET_KEY=secure_key,
            ENVIRONMENT="production"
        )
        
        assert settings.DATABASE_URL == secure_url
        assert settings.ENVIRONMENT == "production"
    
    def test_development_accepts_weak_database_password(self):
        """Development mode should accept weak database passwords (no validation)"""
        settings = Settings(
            DATABASE_URL="postgresql://collabflow:password@localhost/db",
            SECRET_KEY="dev_key",
            ENVIRONMENT="development"
        )
        
        assert "password" in settings.DATABASE_URL


class TestValidationErrorMessages:
    """Test that validation errors are helpful and don't expose secrets"""
    
    def test_error_includes_remediation_instructions(self):
        """Validation errors should include clear fix instructions"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user:strongrandompassword123456@localhost/db",
                SECRET_KEY="short",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value)
        assert "openssl rand -base64 64" in error_msg
        assert "64" in error_msg
    
    def test_error_does_not_expose_secret_values(self):
        """Validation errors should NOT contain actual secret values"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="postgresql://user:dev_password_12345@localhost/db",
                SECRET_KEY="dev_secret_key_12345678901234567890123456789012345678901234",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value)
        
        # Should NOT contain the actual secret values
        assert "dev_password_12345" not in error_msg
        assert "dev_secret_key_123456" not in error_msg
        
        # Should mention patterns in generic terms
        assert "placeholder" in error_msg.lower() or "insecure" in error_msg.lower()
    
    def test_database_url_parsing_error_does_not_expose_url(self):
        """DATABASE_URL parsing errors should not expose the full URL"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_URL="invalid://this-is-not-a-valid-url",
                SECRET_KEY="X7fJ2KpL9mN4qR6sT8vW0yZ3aB5cD7eF9gH1iJ3kL5mN7oP9qR1sT3uV5wX7yZ9aB1cD3eF5gH7iJ9kL1m",
                ENVIRONMENT="production"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "invalid" in error_msg or "format" in error_msg
        # Should not expose the actual invalid URL
        assert "invalid://this-is-not-a-valid-url" not in error_msg


class TestDevelopmentEnvironmentBackwardCompatibility:
    """Test that development environment is not affected by validation"""
    
    def test_development_accepts_all_patterns(self):
        """Development should accept all previously valid configurations"""
        development_configs = [
            {
                'DATABASE_URL': 'postgresql://collabflow:collabflow_dev_password@localhost:5432/collabflow_db',
                'SECRET_KEY': 'dev_secret_key_at_least_32_chars_long_for_jwt_signing',
            },
            {
                'DATABASE_URL': 'postgresql://user:password@localhost/db',
                'SECRET_KEY': 'test',
            },
            {
                'DATABASE_URL': 'postgresql://user:123456@localhost/db',
                'SECRET_KEY': 'my_secret_key',
            },
        ]
        
        for config in development_configs:
            # Should not raise exception in development
            settings = Settings(
                ENVIRONMENT="development",
                **config
            )
            assert settings.ENVIRONMENT == "development"
