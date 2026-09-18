from __future__ import annotations

from app.config import Settings
from app.database.session import get_engine


def test_get_engine_applies_configured_pool_limits() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://fitician:fitician@localhost:5432/fitician_pool_test",
        db_pool_size=3,
        db_max_overflow=2,
        db_pool_timeout_seconds=7,
        db_pool_recycle_seconds=123,
        db_statement_timeout_ms=17000,
        _env_file=None,
    )
    engine = get_engine(settings)
    try:
        assert engine.pool.size() == 3
        assert engine.pool._max_overflow == 2
        assert engine.pool._timeout == 7
        assert engine.pool._recycle == 123
        assert engine.pool._pre_ping is True
    finally:
        engine.dispose()
