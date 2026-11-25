from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.models.user import User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    revoke_token
)
from app.core.deps import get_current_user
from app.core.rate_limit import login_rate_limiter, register_rate_limiter
from app.core.csrf import generate_csrf_token, set_csrf_cookie
from datetime import datetime, timedelta
from app.core.config import settings
from typing import Optional


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Register a new user with rate limiting"""
    
    # Rate limiting by IP
    client_id = register_rate_limiter.get_client_identifier(request)
    register_rate_limiter.check_rate_limit(db, client_id, "register")
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        # Still record attempt for rate limiting
        register_rate_limiter.record_attempt(db, client_id, "register")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        register_rate_limiter.record_attempt(db, client_id, "register")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Record successful registration attempt (for rate limiting)
    register_rate_limiter.record_attempt(db, client_id, "register")
    
    # Generate and set CSRF token for the new user session
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login with rate limiting and CSRF token generation"""
    
    # Rate limiting by IP
    client_id = login_rate_limiter.get_client_identifier(request)
    login_rate_limiter.check_rate_limit(db, client_id, "login")
    
    # Find user by username
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        # Record failed attempt
        login_rate_limiter.record_attempt(db, client_id, "login")
        # Also rate limit by username to prevent targeted attacks
        login_rate_limiter.record_attempt(db, f"user:{user_credentials.username}", "login")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        login_rate_limiter.record_attempt(db, client_id, "login")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    # Set HttpOnly cookie with environment-based security settings
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,              # Cannot be accessed by JavaScript
        secure=settings.get_cookie_secure(),  # HTTPS only in production
        samesite=settings.get_cookie_samesite(),  # Strict in prod, Lax in dev
        max_age=settings.COOKIE_MAX_AGE,
        path="/",                   # Available for all paths
        domain=None                 # Same origin only
    )
    
    # Generate and set CSRF token
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    
    # Record successful login (for rate limiting cleanup)
    login_rate_limiter.record_attempt(db, client_id, "login")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Logout by revoking token and clearing cookies"""
    
    # Revoke the token if present
    if access_token:
        payload = decode_token(access_token)
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                # Convert exp timestamp to datetime
                expires_at = datetime.fromtimestamp(exp)
                revoke_token(jti, expires_at, db)
    
    # Clear both cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user
