from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.db.base import get_db
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.project import Project
from app.models.user import User
from app.core.deps import get_current_user
from app.algorithms.graph import build_task_graph


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def verify_project_access(project_id: str, user: User, db: Session) -> Project:
    """Verify user has access to project"""
    from app.core.deps import check_workspace_access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    check_workspace_access(project.workspace_id, user, db)
    return project


@router.get("/projects/{project_id}/overview")
async def get_project_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive analytics for a project"""
    
    verify_project_access(project_id, current_user, db)
    
    # Total task counts
    total_tasks = db.query(Task).filter(Task.project_id == project_id).count()
    
    # Tasks by status
    status_counts = db.query(
        Task.status,
        func.count(Task.id)
    ).filter(
        Task.project_id == project_id
    ).group_by(Task.status).all()
    
    tasks_by_status = {status.value: 0 for status in TaskStatus}
    for status, count in status_counts:
        tasks_by_status[status.value] = count
    
    # Tasks by priority
    priority_counts = db.query(
        Task.priority,
        func.count(Task.id)
    ).filter(
        Task.project_id == project_id
    ).group_by(Task.priority).all()
    
    tasks_by_priority = {priority.value: 0 for priority in TaskPriority}
    for priority, count in priority_counts:
        tasks_by_priority[priority.value] = count
    
    # Completion metrics
    completed_tasks = tasks_by_status.get("done", 0)
    in_progress_tasks = tasks_by_status.get("in_progress", 0)
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Overdue tasks
    now = datetime.utcnow()
    overdue_tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.due_date < now,
        Task.status != TaskStatus.DONE
    ).count()
    
    # Team workload - tasks per assignee
    workload = db.query(
        Task.assignee_id,
        func.count(Task.id)
    ).filter(
        Task.project_id == project_id,
        Task.assignee_id.isnot(None),
        Task.status != TaskStatus.DONE
    ).group_by(Task.assignee_id).all()
    
    team_workload = [
        {"assignee_id": assignee_id, "task_count": count}
        for assignee_id, count in workload
    ]
    
    # Recent completion trend (last 7 days)
    seven_days_ago = now - timedelta(days=7)
    daily_completions = db.query(
        func.date(Task.updated_at).label('date'),
        func.count(Task.id).label('count')
    ).filter(
        Task.project_id == project_id,
        Task.status == TaskStatus.DONE,
        Task.updated_at >= seven_days_ago
    ).group_by(func.date(Task.updated_at)).all()
    
    completion_trend = [
        {"date": str(date), "completed": count}
        for date, count in daily_completions
    ]
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": round(completion_rate, 2),
        "tasks_by_status": tasks_by_status,
        "tasks_by_priority": tasks_by_priority,
        "team_workload": team_workload,
        "completion_trend": completion_trend
    }


@router.get("/projects/{project_id}/graph-analysis")
async def get_graph_analysis(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform graph algorithm analysis on project tasks.
    Returns topological sort, critical path, and blocked tasks.
    """
    
    verify_project_access(project_id, current_user, db)
    
    # Get all tasks and dependencies
    from app.models.task import TaskDependency
    
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    dependencies = db.query(TaskDependency).join(
        Task, TaskDependency.task_id == Task.id
    ).filter(Task.project_id == project_id).all()
    
    if not tasks:
        return {
            "topological_order": [],
            "critical_path": [],
            "critical_path_duration": 0,
            "blocked_tasks": {},
            "has_cycle": False
        }
    
    # Build task graph
    task_dicts = [{"id": t.id, "estimated_hours": t.estimated_hours or 0} for t in tasks]
    dep_dicts = [{"task_id": d.task_id, "depends_on_id": d.depends_on_id} for d in dependencies]
    
    graph = build_task_graph(task_dicts, dep_dicts)
    
    # Check for cycles
    has_cycle = graph.has_cycle()
    
    # Topological sort
    topo_order = graph.topological_sort() if not has_cycle else []
    
    # Critical path
    critical_path, duration = graph.critical_path() if not has_cycle else ([], 0)
    
    # Blocked tasks
    blocked_tasks = graph.get_blocked_tasks()
    
    return {
        "topological_order": topo_order or [],
        "critical_path": critical_path,
        "critical_path_duration": duration,
        "blocked_tasks": blocked_tasks,
        "has_cycle": has_cycle
    }
