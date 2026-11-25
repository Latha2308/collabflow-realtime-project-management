"""
Rate limiting implementation using PostgreSQL.
Database-backed approach works across multiple backend instances.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.security import RateLimitRecord
from fastapi import HTTPException, status, Request
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    PostgreSQL-backed rate limiter for authentication endpoints.
    Tracks attempts in database for multi-instance compatibility.
    """
    
    def __init__(
        self,
        endpoint: str,
        max_attempts: int = 5,
        window_minutes: int = 15
    ):
        self.endpoint = endpoint
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        Uses direct connection IP, not X-Forwarded-For (untrusted).
        """
        # In production behind a trusted proxy, configure this appropriately
        # For now, use direct client IP
        return request.client.host if request.client else "unknown"
    
    def check_rate_limit(
        self,
        db: Session,
        identifier: str,
        endpoint: str = None
    ) -> None:
        """
        Check if rate limit has been exceeded.
        Raises HTTPException 429 if limit exceeded.
        """
        endpoint = endpoint or self.endpoint
        window_start = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        
        # Count attempts in the time window
        attempt_count = db.query(RateLimitRecord).filter(
            RateLimitRecord.identifier == identifier,
            RateLimitRecord.endpoint == endpoint,
            RateLimitRecord.attempt_time >= window_start
        ).count()
        
        if attempt_count >= self.max_attempts:
            logger.warning(
                f"Rate limit exceeded for {endpoint} from {identifier}: "
                f"{attempt_count} attempts in {self.window_minutes} minutes"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many {endpoint} attempts. Please try again in {self.window_minutes} minutes."
            )
    
    def record_attempt(
        self,
        db: Session,
        identifier: str,
        endpoint: str = None
    ) -> None:
        """
        Record a rate limit attempt.
        """
        endpoint = endpoint or self.endpoint
        
        record = RateLimitRecord(
            identifier=identifier,
            endpoint=endpoint,
            attempt_time=datetime.utcnow()
        )
        db.add(record)
        db.commit()
    
    def cleanup_old_records(self, db: Session, days_old: int = 7) -> int:
        """
        Clean up old rate limit records.
        Should be called periodically (e.g., via cron or startup).
        Returns number of deleted records.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        deleted = db.query(RateLimitRecord).filter(
            RateLimitRecord.attempt_time < cutoff
        ).delete()
        
        db.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old rate limit records")
        
        return deleted


# Pre-configured rate limiters for auth endpoints
login_rate_limiter = RateLimiter(
    endpoint="login",
    max_attempts=5,
    window_minutes=15
)

register_rate_limiter = RateLimiter(
    endpoint="register",
    max_attempts=3,
    window_minutes=60  # Stricter for registration
)
