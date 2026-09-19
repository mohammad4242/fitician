import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_db
from app.main import create_app
from tests.database_lifecycle import (
    ensure_database_exists,
    hold_database_lock,
    reset_public_schema,
    upgrade_database,
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://fitician:fitician@localhost:5432/fitician_test",
)


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    expected_database = make_url(TEST_DATABASE_URL).database or "fitician_test"
    ensure_database_exists(TEST_DATABASE_URL, expected_database=expected_database)
    with hold_database_lock(TEST_DATABASE_URL, expected_database=expected_database):
        reset_public_schema(TEST_DATABASE_URL, expected_database=expected_database)
        upgrade_database(TEST_DATABASE_URL, expected_database=expected_database)
        yield


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(TEST_DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL,
        frontend_origin="http://localhost:5173",
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
        session_ttl_seconds=604800,
        media_root=tmp_path / "media",
        sms_provider="fake",
        email_provider="fake",
        _env_file=None,
    )


@pytest.fixture
def client(db: Session, test_settings: Settings) -> Iterator[TestClient]:
    app = create_app(test_settings)

    def override_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.state.rate_limit_session_factory = lambda: Session(
        bind=db.connection(),
        join_transaction_mode="create_savepoint",
    )
    with TestClient(app) as test_client:
        test_client.app.state.cache = None
        test_client.app.state.rate_limiter = None
        yield test_client
    app.dependency_overrides.clear()
