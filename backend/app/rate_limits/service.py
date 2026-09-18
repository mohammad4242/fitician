from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import DistributedRateLimitCounter


class DistributedRateLimitError(Exception):
    """Base error for the generic limiter."""


class DistributedRateLimitExceeded(DistributedRateLimitError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)


def hash_actor(actor: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), actor.encode("utf-8"), hashlib.sha256).hexdigest()


def consume_rate_limit(
    db: Session,
    *,
    namespace: str,
    actor: str,
    operation: str,
    limit: int,
    window_seconds: int,
    hmac_secret: str,
    now: datetime | None = None,
) -> None:
    if limit < 1 or window_seconds < 1:
        raise ValueError("Rate-limit limit and window must be positive")
    current = now or datetime.now(UTC)
    epoch = int(current.timestamp())
    window_epoch = epoch - (epoch % window_seconds)
    window_start = datetime.fromtimestamp(window_epoch, UTC)
    table = cast(Table, DistributedRateLimitCounter.__table__)
    statement = (
        insert(table)
        .values(
            id=uuid4(),
            namespace=namespace,
            actor_hash=hash_actor(actor, hmac_secret),
            operation=operation,
            window_started_at=window_start,
            request_count=1,
        )
        .on_conflict_do_update(
            constraint="uq_distributed_rate_limit_window",
            set_={
                "request_count": table.c.request_count + 1,
                "updated_at": current,
            },
        )
        .returning(table.c.request_count)
    )
    count = int(db.execute(statement).scalar_one())
    db.commit()
    if count > limit:
        raise DistributedRateLimitExceeded(window_epoch + window_seconds - epoch)

