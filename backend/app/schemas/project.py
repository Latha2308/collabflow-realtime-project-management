from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    workspace_id: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class ProjectResponse(ProjectBase):
    id: str
    workspace_id: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
