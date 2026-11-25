"""
CollabFlow - Real-Time Collaborative Project Management Platform
Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, workspaces, projects, tasks, analytics
from app.realtime import websocket
from app.core.csrf import CSRFProtectionMiddleware
from app.core.rate_limit import login_rate_limiter, register_rate_limiter
from app.db.base import SessionLocal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-time collaborative project management platform with advanced task dependency management"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add CSRF protection middleware (must be after CORS)
app.add_middleware(CSRFProtectionMiddleware)

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(workspaces.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

# Include WebSocket router
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CollabFlow API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Log security validation status in production (without exposing secrets)
    if settings.ENVIRONMENT == "production":
        logger.info("✅ Production security configuration validated")
        logger.info("✅ Secure cookie settings enabled (Secure=True, SameSite=Strict)")
        logger.info("✅ CSRF protection enabled")
        logger.info("✅ Rate limiting enabled (login: 5/15min, register: 3/60min)")
        logger.info("✅ Token revocation enabled (1 hour expiration)")
    
    # Clean up old rate limit records (older than 7 days)
    db = SessionLocal()
    try:
        deleted_count = login_rate_limiter.cleanup_old_records(db, days_old=7)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old rate limit records")
    except Exception as e:
        logger.error(f"Error cleaning up rate limit records: {e}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down CollabFlow")
