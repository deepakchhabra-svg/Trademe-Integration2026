
import os
import sys
import pytest
from unittest.mock import patch
from contextlib import contextmanager
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from retail_os.core.database import Base, get_db_session
from services.api.main import app

# Ensure repo root is importable when running tests from any cwd.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

@pytest.fixture(scope="session", autouse=True)
def test_env_setup():
    """
    Set environment variables for testing.
    """
    # Allow headers to define role (e.g. X-RetailOS-Role: power)
    os.environ["RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES"] = "true"
    os.environ["RETAIL_OS_DEFAULT_ROLE"] = "power"
    yield

@pytest.fixture(scope="session")
def engine():
    # Use in-memory SQLite for speed and isolation
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Enable FKs for SQLite (optional, good for rigor)
    @event.listens_for(e, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)

@pytest.fixture
def db_session(engine):
    """
    Creates a new session for each test, rolling back at the end.
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def mock_db_session_global(db_session):
    """
    Globally patch get_db_session context manager in all known locations.
    """
    @contextmanager
    def mock_val():
        yield db_session

    # Locations to patch
    targets = [
        "retail_os.core.database.get_db_session",
        "services.api.routers.ops.get_db_session",
        "services.api.routers.vaults.get_db_session",
        "services.api.main.get_db_session",
    ]
    
    patches = [patch(t, side_effect=mock_val) for t in targets]
    
    for p in patches:
        p.start()
    
    yield
    
    for p in patches:
        p.stop()

@pytest.fixture
def client(db_session):
    """
    FastAPI TestClient with DB session overridden.
    """
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()
