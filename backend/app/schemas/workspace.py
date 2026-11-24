from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.workspace import WorkspaceRole


class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(WorkspaceBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkspaceMemberBase(BaseModel):
    user_id: str
    role: WorkspaceRole


class WorkspaceMemberCreate(WorkspaceMemberBase):
    pass


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    joined_at: datetime
    
    class Config:
        from_attributes = True
