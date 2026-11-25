"""
Dependencies for FastAPI routes.
Handles authentication and authorization.
"""

from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from app.db.base import get_db
from app.core.security import decode_token, is_token_revoked
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole


async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the access token cookie.
    Checks token revocation.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Check if token has been revoked
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    if is_token_revoked(jti, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def check_workspace_access(
    workspace_id: str,
    user: User,
    db: Session,
    min_role: WorkspaceRole = WorkspaceRole.VIEWER
) -> WorkspaceMember:
    """
    Check if user has access to workspace with minimum required role.
    Returns the workspace membership.
    """
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this workspace"
        )
    
    # Role hierarchy: owner > admin > member > viewer
    role_hierarchy = {
        WorkspaceRole.OWNER: 4,
        WorkspaceRole.ADMIN: 3,
        WorkspaceRole.MEMBER: 2,
        WorkspaceRole.VIEWER: 1
    }
    
    if role_hierarchy[membership.role] < role_hierarchy[min_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {min_role.value} role or higher"
        )
    
    return membership
