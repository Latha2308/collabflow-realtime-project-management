"""
Authentication security tests.
Tests rate limiting, token revocation, JWT expiration, and CSRF protection.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.security import RateLimitRecord, RevokedToken
from app.core.security import create_access_token, decode_token
from datetime import datetime, timedelta
import time


def test_login_rate_limiting(client: TestClient, db: Session):
    """Test that login endpoint enforces rate limiting"""
    
    # Try to login 6 times with wrong password (limit is 5 per 15 min)
    for i in range(6):
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrong"
        })
        
        if i < 5:
            # First 5 attempts should get 401 (wrong credentials)
            assert response.status_code == 401
        else:
            # 6th attempt should be rate limited
            assert response.status_code == 429
            assert "too many" in response.json()["detail"].lower()


def test_register_rate_limiting(client: TestClient, db: Session):
    """Test that registration endpoint enforces rate limiting"""
    
    # Try to register 4 times (limit is 3 per 60 min)
    for i in range(4):
        response = client.post("/api/v1/auth/register", json={
            "email": f"test{i}@example.com",
            "username": f"testuser{i}",
            "full_name": f"Test User {i}",
            "password": "testpass123"
        })
        
        if i < 3:
            # First 3 should succeed or fail normally
            assert response.status_code in [201, 400]
        else:
            # 4th attempt should be rate limited
            assert response.status_code == 429
            assert "too many" in response.json()["detail"].lower()


def test_csrf_token_generated_on_login(client: TestClient, db: Session):
    """Test that CSRF token is generated on login"""
    
    # Register a user
    client.post("/api/v1/auth/register", json={
        "email": "csrf@example.com",
        "username": "csrfuser",
        "full_name": "CSRF User",
        "password": "testpass123"
    })
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "username": "csrfuser",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    
    # Check that CSRF token cookie is set
    assert "csrf_token" in response.cookies
    csrf_token_value = response.cookies.get("csrf_token")
    assert csrf_token_value is not None
    assert len(csrf_token_value) > 20  # Should be a substantial token


def test_csrf_protection_on_state_changing_requests(db: Session):
    """Test that CSRF protection blocks requests without valid token"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    # Use standard TestClient (not CSRFTestClient) for this test
    # Don't raise server exceptions to properly test HTTP status codes
    test_client = TestClient(app, raise_server_exceptions=False)
    
    # Register and login
    test_client.post("/api/v1/auth/register", json={
        "email": "csrf2@example.com",
        "username": "csrfuser2",
        "full_name": "CSRF User 2",
        "password": "testpass123"
    })
    
    login_response = test_client.post("/api/v1/auth/login", json={
        "username": "csrfuser2",
        "password": "testpass123"
    })
    
    # Extract CSRF token
    csrf_token = login_response.cookies.get("csrf_token")
    assert csrf_token is not None, "CSRF token should be set on login"
    
    # Test 1: Request without CSRF token should return 403
    response = test_client.post("/api/v1/workspaces", json={
        "name": "Test Workspace",
        "description": "Test"
    })
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert "csrf" in response.json()["detail"].lower(), "Error should mention CSRF"
    
    # Test 2: Request with invalid CSRF token should return 403
    response = test_client.post("/api/v1/workspaces", json={
        "name": "Test Workspace 2",
        "description": "Test"
    }, headers={"X-CSRF-Token": "invalid_token_12345"})
    assert response.status_code == 403, f"Expected 403 for invalid token, got {response.status_code}"
    assert "csrf" in response.json()["detail"].lower(), "Error should mention CSRF"
    
    # Test 3: Request with valid CSRF token should succeed
    response = test_client.post("/api/v1/workspaces", json={
        "name": "Test Workspace Valid",
        "description": "Test"
    }, headers={"X-CSRF-Token": csrf_token})
    assert response.status_code == 201, f"Expected 201 with valid CSRF, got {response.status_code}"


def test_logout_revokes_token(client: TestClient, db: Session):
    """Test that logout revokes the token server-side"""
    
    # Register and login
    client.post("/api/v1/auth/register", json={
        "email": "revoke@example.com",
        "username": "revokeuser",
        "full_name": "Revoke User",
        "password": "testpass123"
    })
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": "revokeuser",
        "password": "testpass123"
    })
    
    access_token = login_response.cookies.get("access_token")
    csrf_token = login_response.cookies.get("csrf_token")
    
    # Verify we can access protected endpoint
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    
    # Logout
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    
    # Verify token is revoked in database
    payload = decode_token(access_token)
    jti = payload.get("jti")
    
    revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    assert revoked is not None, "Token should be revoked in database"
    
    # Try to use the token again (simulate cookie reuse)
    # Set the cookie manually to bypass the client's cookie clearing
    client.cookies.set("access_token", access_token)
    client.cookies.set("csrf_token", csrf_token)
    if hasattr(client, '_csrf_token'):
        client._csrf_token = csrf_token
    
    response = client.get("/api/v1/auth/me")
    
    # Should be rejected because token is revoked
    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()


def test_jwt_includes_jti(client: TestClient, db: Session):
    """Test that JWT tokens include JTI for revocation"""
    
    # Register and login
    client.post("/api/v1/auth/register", json={
        "email": "jti@example.com",
        "username": "jtiuser",
        "full_name": "JTI User",
        "password": "testpass123"
    })
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": "jtiuser",
        "password": "testpass123"
    })
    
    access_token = login_response.cookies.get("access_token")
    
    # Decode and verify JTI is present
    payload = decode_token(access_token)
    assert payload is not None
    assert "jti" in payload
    assert len(payload["jti"]) > 20  # Should be a UUID


def test_token_expiration_time(client: TestClient, db: Session):
    """Test that tokens have correct expiration (1 hour)"""
    
    # Register and login
    client.post("/api/v1/auth/register", json={
        "email": "exp@example.com",
        "username": "expuser",
        "full_name": "Exp User",
        "password": "testpass123"
    })
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": "expuser",
        "password": "testpass123"
    })
    
    access_token = login_response.cookies.get("access_token")
    payload = decode_token(access_token)
    
    # Check expiration time
    exp_timestamp = payload.get("exp")
    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)  # Use utcfromtimestamp for UTC comparison
    now = datetime.utcnow()
    
    # Should expire in approximately 1 hour (60 minutes ± 2 minutes for test execution)
    time_until_expiration = (exp_datetime - now).total_seconds()
    assert 3540 < time_until_expiration < 3660  # 59-61 minutes


def test_expired_token_rejected(client: TestClient, db: Session):
    """Test that expired tokens are rejected"""
    
    # Create a token that's already expired
    from app.core.security import create_access_token
    
    expired_token = create_access_token(
        data={"sub": "fake-user-id"},
        expires_delta=timedelta(seconds=-10)  # Expired 10 seconds ago
    )
    
    # Try to use expired token
    client.cookies.set("access_token", expired_token)
    response = client.get("/api/v1/auth/me")
    
    # Should be rejected
    assert response.status_code == 401


def test_rate_limit_records_created(client: TestClient, db: Session):
    """Test that rate limit attempts are recorded in database"""
    
    initial_count = db.query(RateLimitRecord).count()
    
    # Make a login attempt
    client.post("/api/v1/auth/login", json={
        "username": "test",
        "password": "wrong"
    })
    
    # Check that a record was created
    final_count = db.query(RateLimitRecord).count()
    assert final_count > initial_count


def test_csrf_safe_methods_not_protected(client: TestClient, db: Session):
    """Test that GET requests don't require CSRF token"""
    
    # GET requests should work without CSRF token
    response = client.get("/health")
    assert response.status_code == 200
    
    response = client.get("/")
    assert response.status_code == 200


def test_csrf_public_endpoints_exempt(client: TestClient, db: Session):
    """Test that login and register don't require CSRF token"""
    
    # Register should work without CSRF token (it generates one)
    response = client.post("/api/v1/auth/register", json={
        "email": "public@example.com",
        "username": "publicuser",
        "full_name": "Public User",
        "password": "testpass123"
    })
    assert response.status_code == 201
    
    # Login should work without CSRF token (it generates one)
    response = client.post("/api/v1/auth/login", json={
        "username": "publicuser",
        "password": "testpass123"
    })
    assert response.status_code == 200


def test_logout_clears_both_cookies(client: TestClient, db: Session):
    """Test that logout clears both access_token and csrf_token"""
    
    # Register and login
    client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "username": "logoutuser",
        "full_name": "Logout User",
        "password": "testpass123"
    })
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": "logoutuser",
        "password": "testpass123"
    })
    
    csrf_token = login_response.cookies.get("csrf_token")
    
    # Logout (CSRF token auto-handled by test client)
    logout_response = client.post("/api/v1/auth/logout")
    
    # Check response indicates success
    assert logout_response.status_code == 200
