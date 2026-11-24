from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate,
    WorkspaceMemberCreate, WorkspaceMemberResponse, WorkspaceMemberUpdate
)
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.core.deps import get_current_user, check_workspace_access


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new workspace and assign creator as owner"""
    
    new_workspace = Workspace(
        name=workspace_data.name,
        description=workspace_data.description
    )
    
    db.add(new_workspace)
    db.flush()
    
    # Add creator as owner
    membership = WorkspaceMember(
        workspace_id=new_workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER
    )
    db.add(membership)
    
    db.commit()
    db.refresh(new_workspace)
    
    return new_workspace


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all workspaces the current user is a member of"""
    
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == current_user.id
    ).all()
    
    workspace_ids = [m.workspace_id for m in memberships]
    workspaces = db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()
    
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workspace details"""
    
    check_workspace_access(workspace_id, current_user, db)
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update workspace (requires admin or owner role)"""
    
    check_workspace_access(workspace_id, current_user, db, min_role=WorkspaceRole.ADMIN)
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if workspace_data.name is not None:
        workspace.name = workspace_data.name
    if workspace_data.description is not None:
        workspace.description = workspace_data.description
    
    db.commit()
    db.refresh(workspace)
    
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete workspace (requires owner role)"""
    
    check_workspace_access(workspace_id, current_user, db, min_role=WorkspaceRole.OWNER)
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    db.delete(workspace)
    db.commit()


# Workspace member management

@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: str,
    member_data: WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a member to workspace (requires admin or owner role)"""
    
    check_workspace_access(workspace_id, current_user, db, min_role=WorkspaceRole.ADMIN)
    
    # Check if user exists
    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already a member
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == member_data.user_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member"
        )
    
    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=member_data.user_id,
        role=member_data.role
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return new_member


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all members of a workspace"""
    
    check_workspace_access(workspace_id, current_user, db)
    
    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id
    ).all()
    
    return members


@router.patch("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberResponse)
async def update_workspace_member(
    workspace_id: str,
    member_id: str,
    member_data: WorkspaceMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update workspace member role (requires admin or owner role)"""
    
    check_workspace_access(workspace_id, current_user, db, min_role=WorkspaceRole.ADMIN)
    
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    member.role = member_data.role
    db.commit()
    db.refresh(member)
    
    return member


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from workspace (requires admin or owner role)"""
    
    check_workspace_access(workspace_id, current_user, db, min_role=WorkspaceRole.ADMIN)
    
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    db.delete(member)
    db.commit()
