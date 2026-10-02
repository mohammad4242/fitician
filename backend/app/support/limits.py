from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.config import Settings
from app.database.session import isolated_session
from app.infrastructure.rate_limiter import RedisRateLimitUnavailable
from app.rate_limits.service import DistributedRateLimitExceeded, consume_rate_limit
from app.support.models import SupportMessage, SupportTicket


async def limit_write(
    request: Request, db: Session, settings: Settings, user: User, request_id: UUID, *, create: bool
) -> None:
    model = SupportTicket if create else SupportMessage
    owner = SupportTicket.user_id if create else SupportMessage.sender_id
    if db.scalar(select(model.id).where(owner == user.id, model.request_id == request_id)):
        return  # Replays and payload conflicts must reach idempotency validation.
    operation = "create" if create else "reply"
    limit = settings.support_ticket_create_limit if create else settings.support_ticket_reply_limit
    retry_after = None
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is not None:
        try:
            result = await limiter.consume(
                namespace="support",
                actor=str(user.id),
                operation=operation,
                limit=limit,
                window_seconds=settings.support_rate_limit_window_seconds,
            )
            if result.allowed:
                return
            retry_after = result.retry_after_seconds
        except RedisRateLimitUnavailable:
            pass
    if retry_after is None:
        try:
            with isolated_session(
                settings,
                session_factory=getattr(request.app.state, "rate_limit_session_factory", None),
            ) as fallback:
                consume_rate_limit(
                    fallback,
                    namespace="support",
                    actor=str(user.id),
                    operation=operation,
                    limit=limit,
                    window_seconds=settings.support_rate_limit_window_seconds,
                    hmac_secret=settings.phone_otp_hmac_secret.get_secret_value(),
                )
            return
        except DistributedRateLimitExceeded as error:
            retry_after = error.retry_after_seconds
        except SQLAlchemyError:
            raise HTTPException(503, detail={"code": "RATE_LIMIT_UNAVAILABLE"}) from None
    raise HTTPException(
        429, detail={"code": "SUPPORT_RATE_LIMITED"}, headers={"Retry-After": str(retry_after)}
    )
