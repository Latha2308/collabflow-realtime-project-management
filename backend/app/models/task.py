from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import uuid
import enum


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.BACKLOG)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    assignee_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    created_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    due_date = Column(DateTime)
    estimated_hours = Column(Integer)  # Estimated duration in hours
    position = Column(Integer, default=0, nullable=False)  # For ordering within a column
    version = Column(Integer, default=1, nullable=False)  # For optimistic concurrency control
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    
    # Task dependencies - tasks this task depends on
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # Tasks that depend on this task
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan"
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_id], back_populates="dependents")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
