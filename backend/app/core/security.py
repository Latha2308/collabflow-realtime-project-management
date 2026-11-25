from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import uuid


# Configure passlib with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with JTI (JWT ID) for revocation support.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add unique JTI for token revocation
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "jti": jti
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def is_token_revoked(jti: str, db=None) -> bool:
    """
    Check if a token has been revoked.
    This function is imported in deps.py to avoid circular imports.
    Can accept an existing db session or create a new one.
    """
    from app.db.base import SessionLocal, get_db
    from app.models.security import RevokedToken
    
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        return revoked is not None
    finally:
        if should_close:
            db.close()


def revoke_token(jti: str, expires_at: datetime, db=None):
    """
    Revoke a token by storing its JTI.
    Can accept an existing db session or create a new one.
    """
    from app.db.base import SessionLocal
    from app.models.security import RevokedToken
    
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Check if already revoked
        existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if existing:
            return
        
        revoked_token = RevokedToken(
            jti=jti,
            expires_at=expires_at
        )
        db.add(revoked_token)
        db.commit()
    finally:
        if should_close:
            db.close()

