"""
API tests for CollabFlow backend.
Tests authentication, authorization, and basic CRUD operations.
"""

import pytest
from app.models.user import User
from app.core.security import get_password_hash


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "test123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data


def test_register_duplicate_email(client):
    """Test registering with duplicate email fails"""
    # First registration
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "user1",
            "full_name": "User One",
            "password": "pass123"
        }
    )
    
    # Try to register with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "user2",
            "full_name": "User Two",
            "password": "pass123"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_success(client):
    """Test successful login"""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "full_name": "Login User",
            "password": "login123"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "loginuser",
            "password": "login123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Test login with wrong password fails"""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@example.com",
            "username": "wrongpwuser",
            "full_name": "Wrong PW User",
            "password": "correct123"
        }
    )
    
    # Try login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "wrongpwuser",
            "password": "wrong123"
        }
    )
    assert response.status_code == 401


def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_create_workspace_requires_auth(client):
    """Test that creating workspace requires authentication"""
    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "Test Workspace",
            "description": "Test description"
        }
    )
    assert response.status_code == 401
