"""
Test to reproduce the dependency inconsistency bug reported by the user.

Bug description:
1. Create two tasks in the same project
2. Add a dependency: Dashboard depends on Authentication
3. Frontend shows "Dependency already exists" error
4. But also shows "Blocked By (0)" and "This task has no dependencies"
5. After refresh, dependency still not displayed
"""

import pytest
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskPriority, TaskDependency
from app.core.security import get_password_hash


@pytest.fixture
def test_setup(client, db):
    """Create the exact scenario from the bug report"""
    # Create user
    user = User(
        email="latha@example.com",
        username="LK",
        full_name="Latha Kolluri",
        hashed_password=get_password_hash("latha123")
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
    
    # Create the two tasks from the bug report
    auth_task = Task(
        project_id=project.id,
        title="Implement User Authentication",
        description="Must be completed first",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        created_by_id=user.id,
        estimated_hours=8
    )
    dashboard_task = Task(
        project_id=project.id,
        title="Build Project Dashboard",
        description="Depends on authentication",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        created_by_id=user.id,
        estimated_hours=12
    )
    db.add_all([auth_task, dashboard_task])
    db.commit()
    db.refresh(auth_task)
    db.refresh(dashboard_task)
    
    # Store IDs before closing session
    result = {
        "user_id": user.id,
        "workspace_id": workspace.id,
        "project_id": project.id,
        "auth_task_id": auth_task.id,
        "dashboard_task_id": dashboard_task.id
    }
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "LK", "password": "latha123"}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    
    return result


def test_reproduce_dependency_bug(client, db, test_setup):
    """
    Reproduce the exact bug:
    1. Create dependency: Dashboard depends on Authentication
    2. Verify it was created
    3. List dependencies for the project
    4. Verify the dependency appears in the list
    """
    project_id = test_setup["project_id"]
    auth_task_id = test_setup["auth_task_id"]
    dashboard_task_id = test_setup["dashboard_task_id"]
    
    print(f"\n=== Bug Reproduction Test ===")
    print(f"Project ID: {project_id}")
    print(f"Auth Task ID: {auth_task_id}")
    print(f"Dashboard Task ID: {dashboard_task_id}")
    
    # Step 1: Create the dependency (Dashboard depends on Authentication)
    print("\n1. Creating dependency...")
    create_response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": dashboard_task_id,
            "depends_on_id": auth_task_id
        }
    )
    print(f"   Status: {create_response.status_code}")
    if create_response.status_code == 201:
        print(f"   Created: {create_response.json()}")
    else:
        print(f"   Error: {create_response.json()}")
    assert create_response.status_code == 201, "Failed to create dependency"
    
    created_dep = create_response.json()
    dep_id = created_dep["id"]
    
    # Step 2: Verify in database
    print("\n2. Verifying in database...")
    db_dep = db.query(TaskDependency).filter(TaskDependency.id == dep_id).first()
    assert db_dep is not None, "Dependency not found in database!"
    print(f"   Found in DB: task_id={db_dep.task_id}, depends_on_id={db_dep.depends_on_id}")
    
    # Step 3: List dependencies for the project (THIS IS WHERE THE BUG OCCURS)
    print("\n3. Listing dependencies for project...")
    list_response = client.get(
        f"/api/v1/tasks/dependencies?project_id={project_id}"
    )
    print(f"   Status: {list_response.status_code}")
    
    if list_response.status_code != 200:
        print(f"   ERROR: {list_response.json()}")
        # This is likely the bug - the endpoint returns 404 or other error
        
    assert list_response.status_code == 200, f"Failed to list dependencies: {list_response.json()}"
    
    deps_list = list_response.json()
    print(f"   Dependencies returned: {len(deps_list)}")
    for dep in deps_list:
        print(f"     - {dep}")
    
    # Step 4: Verify the dependency is in the list
    assert len(deps_list) > 0, "No dependencies returned!"
    assert any(d["id"] == dep_id for d in deps_list), "Created dependency not in list!"
    
    # Step 5: Try to create duplicate (should fail)
    print("\n4. Testing duplicate prevention...")
    duplicate_response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": dashboard_task_id,
            "depends_on_id": auth_task_id
        }
    )
    print(f"   Status: {duplicate_response.status_code}")
    print(f"   Response: {duplicate_response.json()}")
    assert duplicate_response.status_code == 400, "Should reject duplicate"
    assert "already exists" in duplicate_response.json()["detail"].lower()
    
    # Step 6: Delete the dependency
    print("\n5. Deleting dependency...")
    delete_response = client.delete(f"/api/v1/tasks/dependencies/{dep_id}")
    print(f"   Status: {delete_response.status_code}")
    assert delete_response.status_code == 204, "Failed to delete dependency"
    
    # Step 7: Verify it's gone from the list
    print("\n6. Verifying deletion...")
    list_after_delete = client.get(
        f"/api/v1/tasks/dependencies?project_id={project_id}"
    )
    assert list_after_delete.status_code == 200
    deps_after = list_after_delete.json()
    print(f"   Dependencies after delete: {len(deps_after)}")
    assert len(deps_after) == 0, "Dependency not deleted!"
    
    print("\n=== Test Passed! ===")


def test_dependency_direction(client, test_setup):
    """
    Test that dependency direction is correct:
    - task_id is the dependent task (the one that is blocked)
    - depends_on_id is the prerequisite task (the one that must be completed first)
    """
    project_id = test_setup["project_id"]
    auth_task_id = test_setup["auth_task_id"]
    dashboard_task_id = test_setup["dashboard_task_id"]
    
    # Create: Dashboard (dependent) depends on Authentication (prerequisite)
    response = client.post(
        "/api/v1/tasks/dependencies",
        json={
            "task_id": dashboard_task_id,  # This task is blocked
            "depends_on_id": auth_task_id  # This task must be done first
        }
    )
    assert response.status_code == 201
    
    # Get the dependency
    deps = client.get(f"/api/v1/tasks/dependencies?project_id={project_id}").json()
    assert len(deps) == 1
    
    dep = deps[0]
    # Verify the direction is correct
    assert dep["task_id"] == dashboard_task_id, "task_id should be the dependent task (Dashboard)"
    assert dep["depends_on_id"] == auth_task_id, "depends_on_id should be the prerequisite (Auth)"


def test_multiple_dependencies_same_task(client, db, test_setup):
    """Test that a task can have multiple prerequisites"""
    project_id = test_setup["project_id"]
    auth_task_id = test_setup["auth_task_id"]
    dashboard_task_id = test_setup["dashboard_task_id"]
    
    # Create a third task
    third_task = Task(
        project_id=project_id,
        title="Setup Database",
        description="Another prerequisite",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        created_by_id=test_setup["user_id"],
        estimated_hours=4
    )
    db.add(third_task)
    db.commit()
    db.refresh(third_task)
    third_task_id = third_task.id
    
    # Dashboard depends on both Auth and Database
    client.post(
        "/api/v1/tasks/dependencies",
        json={"task_id": dashboard_task_id, "depends_on_id": auth_task_id}
    )
    client.post(
        "/api/v1/tasks/dependencies",
        json={"task_id": dashboard_task_id, "depends_on_id": third_task_id}
    )
    
    # List dependencies
    deps = client.get(f"/api/v1/tasks/dependencies?project_id={project_id}").json()
    assert len(deps) == 2
    
    # Both should have dashboard as task_id
    dashboard_deps = [d for d in deps if d["task_id"] == dashboard_task_id]
    assert len(dashboard_deps) == 2
