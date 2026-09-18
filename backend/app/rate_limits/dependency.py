from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.session import get_engine
from app.infrastructure.rate_limiter import RedisRateLimitUnavailable

from .service import DistributedRateLimitExceeded, consume_rate_limit


class DistributedRateLimitUnavailable(RuntimeError):
    """Redis and the PostgreSQL fallback are both unavailable."""


def rate_limit_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, DistributedRateLimitExceeded):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED"},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "RATE_LIMIT_UNAVAILABLE"},
    )


async def enforce_distributed_rate_limit(
    request: Request,
    db: Session,
    settings: Settings,
    *,
    namespace: str,
    operation: str,
    limit: int,
    window_seconds: int,
    user_id: UUID,
) -> None:
    actors = (f"ip:{_client_ip(request)}", f"user:{user_id}")
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is not None:
        try:
            for actor in actors:
                result = await limiter.consume(
                    namespace=namespace,
                    actor=actor,
                    operation=operation,
                    limit=limit,
                    window_seconds=window_seconds,
                )
                if not result.allowed:
                    raise DistributedRateLimitExceeded(result.retry_after_seconds)
            return
        except DistributedRateLimitExceeded:
            raise
        except RedisRateLimitUnavailable:
            pass

    try:
        if getattr(settings, "app_env", None) == "test":
            _consume_fallback(db, actors, settings, namespace, operation, limit, window_seconds)
        else:
            with Session(get_engine(settings)) as fallback_db:
                _consume_fallback(
                    fallback_db, actors, settings, namespace, operation, limit, window_seconds
                )
    except DistributedRateLimitExceeded:
        raise
    except SQLAlchemyError:
        raise DistributedRateLimitUnavailable from None


def _client_ip(request: Request) -> str:
    client = request.client
    return client.host if client is not None else "unknown"


def _consume_fallback(
    db: Session,
    actors: tuple[str, ...],
    settings: Settings,
    namespace: str,
    operation: str,
    limit: int,
    window_seconds: int,
) -> None:
    for actor in actors:
        consume_rate_limit(
            db,
            namespace=namespace,
            actor=actor,
            operation=operation,
            limit=limit,
            window_seconds=window_seconds,
            hmac_secret=settings.phone_otp_hmac_secret.get_secret_value(),
        )
