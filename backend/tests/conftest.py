"""
Shared pytest configuration and fixtures for all tests.
This ensures consistent database setup across all test files.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base, get_db

# Create a single test database engine shared across all tests
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Set the override once at module level
app.dependency_overrides[get_db] = override_get_db

# Create tables once
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def reset_database():
    """
    Reset database for each test to ensure isolation.
    This runs automatically before each test function.
    """
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


class CSRFTestClient(TestClient):
    """
    Extended TestClient that automatically handles CSRF tokens.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._csrf_token = None
    
    def request(self, method, url, **kwargs):
        """Override request to automatically include CSRF token for protected requests"""
        # Add CSRF token header if we have one and it's a protected method
        if self._csrf_token and method.upper() in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Don't add CSRF for login/register/logout endpoints (they are exempt or generate tokens)
            exempt_paths = ['/auth/login', '/auth/register', '/auth/logout', '/health']
            is_exempt = any(exempt in url for exempt in exempt_paths)
            
            if not is_exempt:
                headers = kwargs.get('headers', {})
                if headers is None:
                    headers = {}
                if isinstance(headers, dict):
                    headers['X-CSRF-Token'] = self._csrf_token
                    kwargs['headers'] = headers
        
        # Make the request
        response = super().request(method, url, **kwargs)
        
        # Update CSRF token if set in response cookies
        if 'csrf_token' in response.cookies:
            self._csrf_token = response.cookies['csrf_token']
        
        return response


@pytest.fixture(scope="function")
def client():
    """
    Create a test client for each test.
    The client uses the overridden database dependency and handles CSRF automatically.
    """
    return CSRFTestClient(app)


@pytest.fixture(scope="function")
def db():
    """
    Provide a database session for direct database access in tests.
    """
    database = next(override_get_db())
    yield database
    database.close()
