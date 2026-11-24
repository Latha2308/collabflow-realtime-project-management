"""
Tests for graph algorithms module.
Tests cycle detection, topological sorting, and critical path calculation.
"""

import pytest
from app.algorithms.graph import TaskGraph, build_task_graph


def test_empty_graph():
    """Test empty graph behavior"""
    graph = TaskGraph()
    
    assert graph.has_cycle() == False
    assert graph.topological_sort() == []
    path, duration = graph.critical_path()
    assert path == []
    assert duration == 0


def test_single_task():
    """Test graph with single task"""
    graph = TaskGraph()
    graph.add_task("task1", 5)
    
    assert graph.has_cycle() == False
    assert graph.topological_sort() == ["task1"]
    path, duration = graph.critical_path()
    assert path == ["task1"]
    assert duration == 5


def test_linear_dependencies():
    """Test linear chain of dependencies: A -> B -> C"""
    tasks = [
        {"id": "A", "estimated_hours": 2},
        {"id": "B", "estimated_hours": 3},
        {"id": "C", "estimated_hours": 4},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "B"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == False
    
    topo = graph.topological_sort()
    assert topo is not None
    assert topo.index("A") < topo.index("B")
    assert topo.index("B") < topo.index("C")
    
    path, duration = graph.critical_path()
    assert "A" in path and "B" in path and "C" in path
    assert duration == 2 + 3 + 4


def test_branching_dependencies():
    """
    Test branching dependencies:
         A
        / \
       B   C
        \ /
         D
    """
    tasks = [
        {"id": "A", "estimated_hours": 2},
        {"id": "B", "estimated_hours": 3},
        {"id": "C", "estimated_hours": 5},
        {"id": "D", "estimated_hours": 2},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "A"},
        {"task_id": "D", "depends_on_id": "B"},
        {"task_id": "D", "depends_on_id": "C"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == False
    
    topo = graph.topological_sort()
    assert topo is not None
    assert topo.index("A") < topo.index("B")
    assert topo.index("A") < topo.index("C")
    assert topo.index("B") < topo.index("D")
    assert topo.index("C") < topo.index("D")
    
    path, duration = graph.critical_path()
    # Critical path should go through C (longer branch)
    assert "A" in path and "C" in path and "D" in path
    assert duration == 2 + 5 + 2


def test_circular_dependency_simple():
    """Test simple circular dependency: A -> B -> A"""
    tasks = [
        {"id": "A", "estimated_hours": 2},
        {"id": "B", "estimated_hours": 3},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "A", "depends_on_id": "B"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == True
    assert graph.topological_sort() is None


def test_circular_dependency_complex():
    """Test complex circular dependency: A -> B -> C -> D -> B"""
    tasks = [
        {"id": "A", "estimated_hours": 1},
        {"id": "B", "estimated_hours": 2},
        {"id": "C", "estimated_hours": 3},
        {"id": "D", "estimated_hours": 4},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "B"},
        {"task_id": "D", "depends_on_id": "C"},
        {"task_id": "B", "depends_on_id": "D"},  # Creates cycle
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == True
    assert graph.topological_sort() is None


def test_disconnected_components():
    """Test graph with disconnected components"""
    tasks = [
        {"id": "A", "estimated_hours": 2},
        {"id": "B", "estimated_hours": 3},
        {"id": "C", "estimated_hours": 4},
        {"id": "D", "estimated_hours": 5},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "D", "depends_on_id": "C"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == False
    
    topo = graph.topological_sort()
    assert topo is not None
    assert len(topo) == 4
    assert topo.index("A") < topo.index("B")
    assert topo.index("C") < topo.index("D")


def test_blocked_tasks():
    """Test identification of blocked tasks"""
    tasks = [
        {"id": "A", "estimated_hours": 2},
        {"id": "B", "estimated_hours": 3},
        {"id": "C", "estimated_hours": 4},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "B"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    blocked = graph.get_blocked_tasks()
    
    assert "A" not in blocked
    assert "B" in blocked
    assert "A" in blocked["B"]
    assert "C" in blocked
    assert "A" in blocked["C"]
    assert "B" in blocked["C"]


def test_zero_duration_tasks():
    """Test tasks with zero estimated hours"""
    tasks = [
        {"id": "A", "estimated_hours": 0},
        {"id": "B", "estimated_hours": 0},
        {"id": "C", "estimated_hours": 5},
    ]
    dependencies = [
        {"task_id": "B", "depends_on_id": "A"},
        {"task_id": "C", "depends_on_id": "B"},
    ]
    
    graph = build_task_graph(tasks, dependencies)
    
    assert graph.has_cycle() == False
    
    path, duration = graph.critical_path()
    assert duration == 5
    assert "C" in path
