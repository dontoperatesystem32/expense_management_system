import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from main import app, get_session

# Set default async fixture scope
pytestmark = pytest.mark.asyncio(scope="function")

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, echo=True)


# Override the database dependency
def override_get_session():
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def setup_db():
    # Create all tables before each test
    SQLModel.metadata.create_all(engine)
    yield
    # Drop all tables after each test
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture():
    # Override the dependency
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    # Clean up overrides
    app.dependency_overrides.clear()
