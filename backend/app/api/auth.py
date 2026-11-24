from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
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
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login and receive access token as HttpOnly cookie"""
    
    # Find user by username
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    from app.core.config import settings
    
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
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Logout by clearing the access token cookie"""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user
