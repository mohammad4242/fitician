from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .content import build_notification_payload
from .models import NotificationInboxItem
from .outbox import enqueue_notification_event
from .schemas import NotificationInboxPage, NotificationInboxResponse


def publish_inbox_notification(
    db: Session,
    user_id: UUID,
    event_type: str,
    category: str,
    deduplication_key: str,
    data: dict[str, object],
    *,
    due_at: datetime | None = None,
) -> None:
    payload = build_notification_payload(event_type, data=data)
    inserted = db.scalar(
        insert(NotificationInboxItem)
        .values(
            id=uuid4(),
            user_id=user_id,
            event_type=event_type,
            category=category,
            deduplication_key=deduplication_key,
            payload=payload,
        )
        .on_conflict_do_nothing(constraint="uq_notification_inbox_dedup")
        .returning(NotificationInboxItem.id)
    )
    if inserted is not None:
        enqueue_notification_event(
            db,
            user_id=user_id,
            event_type=event_type,
            category=category,
            deduplication_key=deduplication_key,
            payload=payload,
            available_at=due_at,
        )


def inbox_page(
    db: Session, user_id: UUID, before: UUID | None, limit: int
) -> NotificationInboxPage:
    query = select(NotificationInboxItem).where(NotificationInboxItem.user_id == user_id)
    if before is not None:
        cursor = db.scalar(query.where(NotificationInboxItem.id == before))
        if cursor is None:
            from fastapi import HTTPException

            raise HTTPException(404, detail={"code": "NOTIFICATION_NOT_FOUND"})
        query = query.where(
            tuple_(NotificationInboxItem.created_at, NotificationInboxItem.id)
            < tuple_(literal(cursor.created_at), literal(cursor.id))
        )
    rows = db.scalars(
        query.order_by(
            NotificationInboxItem.created_at.desc(), NotificationInboxItem.id.desc()
        ).limit(limit + 1)
    ).all()
    count = (
        db.scalar(
            select(func.count())
            .select_from(NotificationInboxItem)
            .where(
                NotificationInboxItem.user_id == user_id, NotificationInboxItem.read_at.is_(None)
            )
        )
        or 0
    )
    return NotificationInboxPage(
        items=[NotificationInboxResponse.model_validate(row) for row in rows[:limit]],
        unread_count=count,
        older_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def mark_inbox_read(db: Session, user_id: UUID, item_id: UUID) -> None:
    item = db.scalar(
        select(NotificationInboxItem)
        .where(NotificationInboxItem.user_id == user_id, NotificationInboxItem.id == item_id)
        .with_for_update()
    )
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(404, detail={"code": "NOTIFICATION_NOT_FOUND"})
    item.read_at = item.read_at or datetime.now(UTC)
    db.commit()
