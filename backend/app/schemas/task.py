from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import Optional, Union
from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[int] = None
    
    @field_validator('due_date', mode='before')
    @classmethod
    def parse_due_date(cls, v):
        """Accept date strings (YYYY-MM-DD) or datetime objects.
        Convert date strings to datetime at start of day (00:00:00)."""
        if v is None or v == '':
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        if isinstance(v, str):
            # Try parsing as date first (YYYY-MM-DD)
            try:
                parsed_date = date.fromisoformat(v)
                return datetime.combine(parsed_date, datetime.min.time())
            except ValueError:
                # If that fails, try parsing as full datetime
                return datetime.fromisoformat(v)
        return v


class TaskCreate(TaskBase):
    project_id: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[int] = None
    position: Optional[int] = None
    version: int  # Required for optimistic concurrency control
    
    @field_validator('due_date', mode='before')
    @classmethod
    def parse_due_date(cls, v):
        """Accept date strings (YYYY-MM-DD) or datetime objects.
        Convert date strings to datetime at start of day (00:00:00)."""
        if v is None or v == '':
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        if isinstance(v, str):
            # Try parsing as date first (YYYY-MM-DD)
            try:
                parsed_date = date.fromisoformat(v)
                return datetime.combine(parsed_date, datetime.min.time())
            except ValueError:
                # If that fails, try parsing as full datetime
                return datetime.fromisoformat(v)
        return v


class TaskResponse(TaskBase):
    id: str
    project_id: str
    created_by_id: str
    position: int
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskDependencyCreate(BaseModel):
    task_id: str
    depends_on_id: str


class TaskDependencyResponse(BaseModel):
    id: str
    task_id: str
    depends_on_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    task_id: str


class CommentResponse(CommentBase):
    id: str
    task_id: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
