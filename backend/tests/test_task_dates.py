"""
Tests for task date handling and validation.
"""

import pytest
from datetime import datetime, date
from app.schemas.task import TaskCreate, TaskUpdate
from app.models.task import TaskStatus, TaskPriority


def test_task_create_with_date_string():
    """Test creating task with date string (YYYY-MM-DD)"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "status": TaskStatus.TODO,
        "priority": TaskPriority.HIGH,
        "due_date": "2026-11-27"
    }
    
    task = TaskCreate(**task_data)
    
    assert task.title == "Test Task"
    assert task.due_date is not None
    assert isinstance(task.due_date, datetime)
    assert task.due_date.year == 2026
    assert task.due_date.month == 11
    assert task.due_date.day == 27
    assert task.due_date.hour == 0
    assert task.due_date.minute == 0
    assert task.due_date.second == 0


def test_task_create_with_datetime_string():
    """Test creating task with full datetime string"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": "2026-11-27T14:30:00"
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date is not None
    assert task.due_date.hour == 14
    assert task.due_date.minute == 30


def test_task_create_with_datetime_object():
    """Test creating task with datetime object"""
    due = datetime(2026, 11, 27, 10, 30)
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": due
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date == due


def test_task_create_with_date_object():
    """Test creating task with date object"""
    due = date(2026, 11, 27)
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": due
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date is not None
    assert isinstance(task.due_date, datetime)
    assert task.due_date.year == 2026
    assert task.due_date.month == 11
    assert task.due_date.day == 27
    assert task.due_date.hour == 0


def test_task_create_with_no_due_date():
    """Test creating task without due date"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123"
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date is None


def test_task_create_with_empty_due_date():
    """Test creating task with empty string due date"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": ""
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date is None


def test_task_create_with_none_due_date():
    """Test creating task with None due date"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": None
    }
    
    task = TaskCreate(**task_data)
    
    assert task.due_date is None


def test_task_create_with_invalid_date():
    """Test creating task with invalid date string"""
    task_data = {
        "title": "Test Task",
        "project_id": "project-123",
        "due_date": "invalid-date"
    }
    
    with pytest.raises(ValueError):
        TaskCreate(**task_data)


def test_task_update_with_date_string():
    """Test updating task with date string"""
    update_data = {
        "due_date": "2026-12-01",
        "version": 1
    }
    
    task_update = TaskUpdate(**update_data)
    
    assert task_update.due_date is not None
    assert isinstance(task_update.due_date, datetime)
    assert task_update.due_date.year == 2026
    assert task_update.due_date.month == 12
    assert task_update.due_date.day == 1


def test_task_update_clear_due_date():
    """Test clearing due date in update"""
    update_data = {
        "due_date": None,
        "version": 1
    }
    
    task_update = TaskUpdate(**update_data)
    
    assert task_update.due_date is None
