"""
WebSocket endpoint for real-time collaboration.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.realtime.connection_manager import manager
from app.core.security import decode_token
from app.models.user import User
from app.models.project import Project
from app.core.deps import check_workspace_access
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> User:
    """Authenticate user from token"""
    payload = decode_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user if user and user.is_active else None


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time project collaboration.
    
    Authentication via HttpOnly cookie (access_token).
    Messages are broadcast to all connected clients viewing the same project.
    
    Event types:
    - task_created: New task was created
    - task_updated: Task was modified
    - task_deleted: Task was deleted
    - task_moved: Task was moved to different status/position
    - comment_added: New comment was added
    - dependency_added: New task dependency was added
    - dependency_removed: Task dependency was removed
    """
    
    # Extract token from Cookie header
    cookie_header = websocket.headers.get("cookie", "")
    token = None
    
    # Parse cookies (format: "key1=value1; key2=value2")
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if cookie.startswith("access_token="):
            token = cookie.split("=", 1)[1]
            break
    
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        logger.warning(f"WebSocket connection rejected for project {project_id}: No access_token cookie")
        return
    
    # Validate origin for additional security
    origin = websocket.headers.get("origin")
    if origin:
        from app.core.config import settings
        allowed_origins = settings.get_cors_origins_list()
        if origin not in allowed_origins:
            await websocket.close(code=1008, reason="Invalid origin")
            logger.warning(f"WebSocket connection rejected from origin: {origin}")
            return
    
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Verify project access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        await websocket.close(code=1008, reason="Project not found")
        return
    
    try:
        check_workspace_access(project.workspace_id, user, db)
    except Exception:
        await websocket.close(code=1008, reason="Access denied")
        return
    
    # Connect to project room
    await manager.connect(websocket, project_id, user.id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Validate message structure
            if "type" not in data:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid message format"},
                    websocket
                )
                continue
            
            # Echo back confirmation
            await manager.send_personal_message(
                {"type": "ack", "original_type": data["type"]},
                websocket
            )
            
            # Broadcast to other users in the project
            broadcast_data = {
                **data,
                "user_id": user.id,
                "timestamp": data.get("timestamp")
            }
            
            await manager.broadcast_to_project(
                project_id,
                broadcast_data,
                exclude=websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # Notify other users
        await manager.broadcast_to_project(
            project_id,
            {
                "type": "user_left",
                "user_id": user.id,
                "project_id": project_id
            }
        )
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
