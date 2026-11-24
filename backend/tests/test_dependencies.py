"""
Tests for task dependency management API endpoints.
Tests CRUD operations, circular dependency prevention, and validation.
"""

import pytest
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskPriority
from app.core.security import get_password_hash


@pytest.fixture
def test_data(client, db):
    """Create test user, workspace, project, and tasks"""
    # Create user
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("test123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create workspace
    workspace = Workspace(name="Test Workspace", description="Test")
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    # Add user to workspace
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db.add(member)
    db.commit()
    
    # Create project
    project = Project(
        workspace_id=workspace.id,
        name="Test Project",
        description="Test"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create three tasks
    task1 = Task(
        project_id=project.id,
        title="Task 1",
        description="First task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        created_by_id=user.id,
        estimated_hours=5
    )
    task2 = Task(
        project_id=project.id,
        title="Task 2",
        description="Second task",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        created_by_id=user.id,
        estimated_hours=3
    )
    task3 = Task(
        project_id=project.id,
        title="Task 3",
        description="Third task",
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        created_by_id=user.id,
        estimated_hours=2
    )
    db.add_all([task1, task2, task3])
    db.commit()
    db.refresh(task1)
    db.refresh(task2)
    db.refresh(task3)
    
    # Extract IDs before closing session to avoid detached instance errors
    result = {
        "user_id": user.id,
        "workspace_id": workspace.id,
        "project_id": project.id,
        "task1_id": task1.id,
        "task2_id": task2.id,
        "task3_id": task3.id
    }
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "test123"}
    )
    assert response.status_code == 200
    
    return result


def test_create_dependency(client, test_data):
    """Test creating a task dependency"""
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == test_data["task2_id"]
    assert data["depends_on_id"] == test_data["task1_id"]
    assert "id" in data
    assert "created_at" in data


def test_create_duplicate_dependency(client, test_data):
    """Test that duplicate dependencies are rejected"""
    # Create first dependency
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    
    # Try to create same dependency again
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_create_circular_dependency(client, test_data):
    """Test that circular dependencies are prevented"""
    # Create dependency: task2 depends on task1
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    
    # Try to create reverse dependency: task1 depends on task2 (would create cycle)
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task1_id"],
            "depends_on_id": test_data["task2_id"]
        }
    )
    assert response.status_code == 400
    assert "circular" in response.json()["detail"].lower()


def test_create_indirect_circular_dependency(client, test_data):
    """Test that indirect circular dependencies are prevented"""
    # Create chain: task3 -> task2 -> task1
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task3_id"],
            "depends_on_id": test_data["task2_id"]
        }
    )
    
    # Try to create: task1 depends on task3 (would create cycle)
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task1_id"],
            "depends_on_id": test_data["task3_id"]
        }
    )
    assert response.status_code == 400
    assert "circular" in response.json()["detail"].lower()


def test_list_dependencies(client, test_data):
    """Test listing all dependencies for a project"""
    # Store project_id before accessing it multiple times
    project_id = test_data["project_id"]
    task2_id = test_data["task2_id"]
    task3_id = test_data["task3_id"]
    task1_id = test_data["task1_id"]
    
    # Create two dependencies
    response1 = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": task2_id,
            "depends_on_id": task1_id
        }
    )
    assert response1.status_code == 201
    
    response2 = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": task3_id,
            "depends_on_id": task2_id
        }
    )
    assert response2.status_code == 201
    
    # List dependencies
    response = client.get(
        f"/api/v1/tasks/dependencies?project_id={project_id}"
    )
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(d["task_id"] == task2_id for d in data)
    assert any(d["task_id"] == task3_id for d in data)


def test_delete_dependency(client, test_data):
    """Test deleting a task dependency"""
    project_id = test_data["project_id"]
    task2_id = test_data["task2_id"]
    task1_id = test_data["task1_id"]
    
    # Create dependency
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": task2_id,
            "depends_on_id": task1_id
        }
    )
    dependency_id = response.json()["id"]
    
    # Delete dependency
    response = client.delete(f"/api/v1/tasks/dependencies/{dependency_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(
        f"/api/v1/tasks/dependencies?project_id={project_id}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_dependency_with_nonexistent_task(client, test_data):
    """Test creating dependency with nonexistent task"""
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": "nonexistent-id",
            "depends_on_id": test_data["task1_id"]
        }
    )
    assert response.status_code == 404


def test_dependency_cascade_delete(client, test_data):
    """Test that dependencies are deleted when task is deleted"""
    project_id = test_data["project_id"]
    task2_id = test_data["task2_id"]
    task1_id = test_data["task1_id"]
    
    # Create dependency
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": task2_id,
            "depends_on_id": task1_id
        }
    )
    
    # Delete task1
    client.delete(f"/api/v1/tasks/{task1_id}")
    
    # Verify dependency is gone
    response = client.get(
        f"/api/v1/tasks/dependencies?project_id={project_id}"
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_graph_analysis_with_dependencies(client, test_data):
    """Test that graph analysis works correctly with dependencies"""
    # Create dependency chain: task3 -> task2 -> task1
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task2_id"],
            "depends_on_id": test_data["task1_id"]
        }
    )
    client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": test_data["task3_id"],
            "depends_on_id": test_data["task2_id"]
        }
    )
    
    # Get graph analysis
    response = client.get(
        f"/api/v1/analytics/projects/{test_data['project_id']}/graph-analysis"
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check critical path includes all three tasks
    assert len(data["critical_path"]) > 0
    assert data["critical_path_duration"] == 10  # 5 + 3 + 2 hours
    
    # Check blocked tasks
    assert test_data["task2_id"] in data["blocked_tasks"]
    assert test_data["task3_id"] in data["blocked_tasks"]
    
    # Check no cycle
    assert data["has_cycle"] is False
