from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exc
from typing import List, Optional
from app.db.base import get_db
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskUpdate,
    TaskDependencyCreate, TaskDependencyResponse,
    CommentCreate, CommentResponse
)
from app.models.task import Task, TaskDependency, Comment, TaskStatus
from app.models.project import Project
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.core.deps import get_current_user, check_workspace_access
from app.algorithms.graph import build_task_graph
from app.realtime.connection_manager import manager


router = APIRouter(prefix="/tasks", tags=["Tasks"])


def verify_project_access(project_id: str, user: User, db: Session) -> Project:
    """Verify user has access to project and return project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    check_workspace_access(project.workspace_id, user, db)
    return project


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task"""
    
    project = verify_project_access(task_data.project_id, current_user, db)
    check_workspace_access(project.workspace_id, current_user, db, min_role=WorkspaceRole.MEMBER)
    
    # Get max position for the status column
    max_position = db.query(Task).filter(
        Task.project_id == task_data.project_id,
        Task.status == task_data.status
    ).count()
    
    new_task = Task(
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assignee_id=task_data.assignee_id,
        created_by_id=current_user.id,
        due_date=task_data.due_date,
        estimated_hours=task_data.estimated_hours,
        position=max_position
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_project(
        task_data.project_id,
        {
            "type": "task_created",
            "task_id": new_task.id,
            "task": {
                "id": new_task.id,
                "title": new_task.title,
                "status": new_task.status,
                "priority": new_task.priority,
                "position": new_task.position,
                "version": new_task.version
            }
        }
    )
    
    return new_task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    project_id: str,
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tasks in a project"""
    
    verify_project_access(project_id, current_user, db)
    
    query = db.query(Task).filter(Task.project_id == project_id)
    
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(Task.position).all()
    
    return tasks


@router.post("/dependencies", response_model=TaskDependencyResponse, status_code=status.HTTP_201_CREATED)
async def create_task_dependency(
    dependency_data: TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a task dependency. Validates that no circular dependencies are created.
    """
    
    task = db.query(Task).filter(Task.id == dependency_data.task_id).first()
    depends_on = db.query(Task).filter(Task.id == dependency_data.depends_on_id).first()
    
    if not task or not depends_on:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.project_id != depends_on.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasks must be in the same project"
        )
    
    verify_project_access(task.project_id, current_user, db)
    
    # Check if dependency already exists
    existing = db.query(TaskDependency).filter(
        TaskDependency.task_id == dependency_data.task_id,
        TaskDependency.depends_on_id == dependency_data.depends_on_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dependency already exists"
        )
    
    # Validate no circular dependencies using graph algorithm
    # Get all tasks and dependencies for this project
    tasks = db.query(Task).filter(Task.project_id == task.project_id).all()
    dependencies = db.query(TaskDependency).join(
        Task, TaskDependency.task_id == Task.id
    ).filter(Task.project_id == task.project_id).all()
    
    # Build graph with new dependency
    task_dicts = [{"id": t.id, "estimated_hours": t.estimated_hours or 0} for t in tasks]
    dep_dicts = [{"task_id": d.task_id, "depends_on_id": d.depends_on_id} for d in dependencies]
    # Add the new dependency to check
    dep_dicts.append({"task_id": dependency_data.task_id, "depends_on_id": dependency_data.depends_on_id})
    
    graph = build_task_graph(task_dicts, dep_dicts)
    
    if graph.has_cycle():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adding this dependency would create a circular dependency"
        )
    
    # Create dependency
    new_dependency = TaskDependency(
        task_id=dependency_data.task_id,
        depends_on_id=dependency_data.depends_on_id
    )
    
    db.add(new_dependency)
    db.commit()
    db.refresh(new_dependency)
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_project(
        task.project_id,
        {
            "type": "dependency_added",
            "dependency_id": new_dependency.id,
            "task_id": new_dependency.task_id,
            "depends_on_id": new_dependency.depends_on_id
        }
    )
    
    return new_dependency


@router.get("/dependencies", response_model=List[TaskDependencyResponse])
async def list_task_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all task dependencies for a project"""
    
    verify_project_access(project_id, current_user, db)
    
    dependencies = db.query(TaskDependency).join(
        Task, TaskDependency.task_id == Task.id
    ).filter(Task.project_id == project_id).all()
    
    return dependencies


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task dependency"""
    
    dependency = db.query(TaskDependency).filter(TaskDependency.id == dependency_id).first()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found"
        )
    
    task = db.query(Task).filter(Task.id == dependency.task_id).first()
    verify_project_access(task.project_id, current_user, db)
    
    project_id = task.project_id
    
    db.delete(dependency)
    db.commit()
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_project(
        project_id,
        {
            "type": "dependency_removed",
            "dependency_id": dependency_id,
            "task_id": dependency.task_id,
            "depends_on_id": dependency.depends_on_id
        }
    )


# Comments

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task details"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    verify_project_access(task.project_id, current_user, db)
    
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update task with optimistic concurrency control"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    project = verify_project_access(task.project_id, current_user, db)
    check_workspace_access(project.workspace_id, current_user, db, min_role=WorkspaceRole.MEMBER)
    
    # Optimistic concurrency control
    if task.version != task_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task was modified by another user. Current version: {task.version}, provided: {task_data.version}"
        )
    
    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        old_status = task.status
        task.status = task_data.status
        # If status changed, update position
        if old_status != task_data.status:
            max_position = db.query(Task).filter(
                Task.project_id == task.project_id,
                Task.status == task_data.status
            ).count()
            task.position = max_position
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.assignee_id is not None:
        task.assignee_id = task_data.assignee_id
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.estimated_hours is not None:
        task.estimated_hours = task_data.estimated_hours
    if task_data.position is not None:
        task.position = task_data.position
    
    # Increment version
    task.version += 1
    
    db.commit()
    db.refresh(task)
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_project(
        task.project_id,
        {
            "type": "task_updated",
            "task_id": task.id,
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "position": task.position,
                "version": task.version,
                "assignee_id": task.assignee_id
            }
        }
    )
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete task"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    project = verify_project_access(task.project_id, current_user, db)
    check_workspace_access(project.workspace_id, current_user, db, min_role=WorkspaceRole.MEMBER)
    
    project_id = task.project_id
    task_id = task.id
    
    db.delete(task)
    db.commit()
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_project(
        project_id,
        {
            "type": "task_deleted",
            "task_id": task_id
        }
    )


