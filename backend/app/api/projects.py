from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.models.project import Project
from app.models.workspace import WorkspaceRole
from app.models.user import User
from app.core.deps import get_current_user, check_workspace_access


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project (requires member role or higher)"""
    
    check_workspace_access(project_data.workspace_id, current_user, db, min_role=WorkspaceRole.MEMBER)
    
    new_project = Project(
        workspace_id=project_data.workspace_id,
        name=project_data.name,
        description=project_data.description
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects in a workspace"""
    
    check_workspace_access(workspace_id, current_user, db)
    
    projects = db.query(Project).filter(
        Project.workspace_id == workspace_id,
        Project.is_archived == False
    ).all()
    
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project details"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    check_workspace_access(project.workspace_id, current_user, db)
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project (requires member role or higher)"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    check_workspace_access(project.workspace_id, current_user, db, min_role=WorkspaceRole.MEMBER)
    
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.is_archived is not None:
        project.is_archived = project_data.is_archived
    
    db.commit()
    db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete project (requires admin role or higher)"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    check_workspace_access(project.workspace_id, current_user, db, min_role=WorkspaceRole.ADMIN)
    
    db.delete(project)
    db.commit()
