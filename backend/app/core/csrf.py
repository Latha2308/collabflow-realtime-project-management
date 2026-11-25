"""
CSRF protection for cookie-authenticated requests.
Uses double-submit cookie pattern with signed tokens.
"""

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import secrets
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for state-changing requests.
    
    Approach:
    1. Generate CSRF token on login, send as separate cookie
    2. Frontend must send token in X-CSRF-Token header
    3. Verify token matches cookie value
    4. Additional Origin/Referer validation for defense-in-depth
    """
    
    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Paths that don't require CSRF (public endpoints)
    EXEMPT_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",    # Login generates CSRF token
        "/api/v1/auth/register", # Registration generates CSRF token
        "/api/v1/auth/logout",   # Logout clears cookies (safe operation)
        "/ws/",                   # WebSocket connections (use their own auth)
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods and exempt paths
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)
        
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # Check if user is authenticated (has access_token cookie)
        access_token = request.cookies.get("access_token")
        if not access_token:
            # Not authenticated, no CSRF protection needed
            return await call_next(request)
        
        # Verify CSRF token
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        
        if not csrf_cookie or not csrf_header:
            logger.warning(f"CSRF token missing for {request.method} {path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing"}
            )
        
        # Verify tokens match
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            logger.warning(f"CSRF token mismatch for {request.method} {path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token invalid"}
            )
        
        # Additional Origin validation for defense-in-depth
        origin = request.headers.get("origin")
        if origin:
            allowed_origins = settings.get_cors_origins_list()
            # Also allow HTTPS version of allowed origins in production
            if settings.ENVIRONMENT == "production":
                https_origins = [o.replace("http://", "https://") for o in allowed_origins]
                allowed_origins.extend(https_origins)
            
            if origin not in allowed_origins:
                logger.warning(f"Invalid origin for CSRF-protected request: {origin}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid origin"}
                )
        
        return await call_next(request)


def generate_csrf_token() -> str:
    """
    Generate a random CSRF token.
    """
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    """
    Set CSRF token cookie.
    Not HttpOnly so JavaScript can read it to send in header.
    """
    from app.core.config import settings
    
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Must be readable by JavaScript
        secure=settings.get_cookie_secure(),
        samesite=settings.get_cookie_samesite(),
        max_age=settings.COOKIE_MAX_AGE,
        path="/"
    )
