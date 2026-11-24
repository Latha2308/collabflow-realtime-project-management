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


@pytest.fixture(scope="function")
def client():
    """
    Create a test client for each test.
    The client uses the overridden database dependency.
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def db():
    """
    Provide a database session for direct database access in tests.
    """
    database = next(override_get_db())
    yield database
    database.close()
