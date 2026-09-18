from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import lru_cache

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings


def get_engine(database_url_or_settings: str | Settings) -> Engine:
    if isinstance(database_url_or_settings, Settings):
        settings = database_url_or_settings
        return _get_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
            statement_timeout_ms=settings.db_statement_timeout_ms,
        )
    return _get_engine(database_url_or_settings)


@lru_cache(maxsize=32)
def _get_engine(
    database_url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 5,
    pool_timeout: float = 30.0,
    pool_recycle: int = 1800,
    statement_timeout_ms: int = 30000,
) -> Engine:
    if database_url.startswith("sqlite"):
        return create_engine(database_url, pool_pre_ping=True)
    connect_args: dict[str, object] = {}
    if statement_timeout_ms > 0 and database_url.startswith("postgresql"):
        connect_args["options"] = f"-c statement_timeout={statement_timeout_ms}"
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        connect_args=connect_args,
    )


def get_db(settings: Settings = Depends(get_settings)) -> Iterator[Session]:  # noqa: B008
    with Session(get_engine(settings)) as session:
        yield session


@contextmanager
def isolated_session(
    settings: Settings,
    *,
    session_factory: Callable[[], Session] | None = None,
) -> Iterator[Session]:
    """Create a transaction boundary that is never owned by an API request."""
    factory = session_factory or (lambda: Session(get_engine(settings)))
    with factory() as session:
        yield session
