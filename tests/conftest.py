"""
Shared test fixtures for bid_service unit tests.
Uses an in-memory SQLite database so no real DB or Service Bus is needed.
"""
import sys
import os
import types
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker, declarative_base


TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


_Base = declarative_base()

_db_mod = types.ModuleType("database")
_db_mod.engine = TEST_ENGINE
_db_mod.SessionLocal = TestSession
_db_mod.Base = _Base
_db_mod.SCHEMA = None 

def _get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

_db_mod.get_db = _get_db
_db_mod.create_schema = lambda: None

sys.modules["database"] = _db_mod

_cfg_mod = types.ModuleType("config")
_cfg_mod.SERVICE_BUS_SEND_CONNECTION_STRING = ""
_cfg_mod.QUEUE_NAME = "test-queue"
sys.modules["config"] = _cfg_mod

_ms_mod = types.ModuleType("message_sender")
_mock_sender = MagicMock()
_mock_sender.send_message = MagicMock(return_value=True)
_ms_mod.message_sender = _mock_sender
_ms_mod.MessageSender = MagicMock
sys.modules["message_sender"] = _ms_mod

_seed_mod = types.ModuleType("seed")
_seed_mod.seed_data = lambda: None
sys.modules["seed"] = _seed_mod


from models import Auction, Bid  
from database import Base        
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _setup_tables():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def db_session():
    """Provide a transactional DB session for a test."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def mock_message_sender():
    """Return the mocked message_sender so tests can assert on calls."""
    _mock_sender.reset_mock()
    return _mock_sender


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with mocked dependencies for bid service tests."""
    from main import app
    
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[_db_mod.get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
