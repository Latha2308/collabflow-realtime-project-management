"""
WebSocket connection manager for real-time collaboration.

Manages WebSocket connections, authentication, and message broadcasting.
Supports project-based rooms for efficient message routing.
"""

from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time collaboration.
    
    Connections are organized by project_id to enable efficient broadcasting
    to all users viewing the same project.
    """
    
    def __init__(self):
        # project_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> user_id mapping
        self.connection_users: Dict[WebSocket, str] = {}
        # websocket -> project_id mapping
        self.connection_projects: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str, user_id: str):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            project_id: ID of the project the user is viewing
            user_id: ID of the authenticated user
        """
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        
        self.active_connections[project_id].add(websocket)
        self.connection_users[websocket] = user_id
        self.connection_projects[websocket] = project_id
        
        logger.info(f"User {user_id} connected to project {project_id}")
        
        # Notify other users in the project
        await self.broadcast_to_project(
            project_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "project_id": project_id
            },
            exclude=websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection and clean up.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        project_id = self.connection_projects.get(websocket)
        user_id = self.connection_users.get(websocket)
        
        if project_id and project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            
            # Clean up empty project rooms
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
            
            logger.info(f"User {user_id} disconnected from project {project_id}")
        
        self.connection_users.pop(websocket, None)
        self.connection_projects.pop(websocket, None)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Dictionary to send as JSON
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_project(
        self,
        project_id: str,
        message: dict,
        exclude: Optional[WebSocket] = None
    ):
        """
        Broadcast a message to all connections in a project.
        
        Args:
            project_id: ID of the project to broadcast to
            message: Dictionary to send as JSON
            exclude: Optional WebSocket to exclude from broadcast (e.g., sender)
        """
        if project_id not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[project_id]:
            if connection == exclude:
                continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    def get_project_connections(self, project_id: str) -> int:
        """
        Get the number of active connections for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(project_id, set()))
    
    def get_connection_user(self, websocket: WebSocket) -> Optional[str]:
        """
        Get the user ID associated with a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            
        Returns:
            User ID or None if not found
        """
        return self.connection_users.get(websocket)


# Global connection manager instance
manager = ConnectionManager()
