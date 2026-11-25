"""
Security models for token revocation and rate limiting.
"""

from sqlalchemy import Column, String, DateTime, Integer
from datetime import datetime
from app.db.base import Base
import uuid


class RevokedToken(Base):
    """
    Store revoked JWT tokens (JTI - JWT ID).
    Tokens are added here on logout or when compromised.
    """
    __tablename__ = "revoked_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    jti = Column(String, unique=True, nullable=False, index=True)  # JWT ID
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # When the token would naturally expire


class RateLimitRecord(Base):
    """
    Track rate limit attempts for authentication endpoints.
    Uses a sliding window approach.
    """
    __tablename__ = "rate_limit_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String, nullable=False, index=True)  # IP or username
    endpoint = Column(String, nullable=False)  # e.g., "login", "register"
    attempt_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # For cleanup - we can delete old records periodically
    # Records older than the rate limit window can be removed
