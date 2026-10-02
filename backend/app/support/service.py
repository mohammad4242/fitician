import hashlib
import json
from datetime import UTC, datetime
from typing import NoReturn
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.models import User
from app.notifications.inbox import publish_inbox_notification
from app.support.enums import SupportCategory, SupportStatus
from app.support.models import SupportMessage, SupportMessageRead, SupportStatusEvent, SupportTicket
from app.support.schemas import (
    ReplyInput,
    StatusInput,
    SupportMessageResponse,
    TicketDetail,
    TicketInput,
    TicketPage,
    TicketResponse,
)


def fail(code: str, status: int = 404) -> NoReturn:
    raise HTTPException(status, detail={"code": code})


def owned_ticket(
    db: Session, user: User, ticket_id: UUID, *, admin: bool = False, lock: bool = False
) -> SupportTicket:
    query = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if not admin:
        query = query.where(SupportTicket.user_id == user.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    ticket = db.scalar(query)
    if ticket is None:
        fail("SUPPORT_TICKET_NOT_FOUND")
    return ticket


def lock_actor(db: Session, user: User) -> None:
    # Serialize sender request IDs across tickets, including concurrent create/reply.
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())


def create_ticket(db: Session, user: User, payload: TicketInput) -> TicketResponse:
    lock_actor(db, user)
    digest = hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    existing = db.scalar(
        select(SupportTicket).where(
            SupportTicket.user_id == user.id, SupportTicket.request_id == payload.request_id
        )
    )
    if existing is not None:
        if existing.creation_digest != digest:
            fail("SUPPORT_REQUEST_CONFLICT", 409)
        return TicketResponse.model_validate(existing)
    if db.scalar(
        select(SupportMessage.id).where(
            SupportMessage.sender_id == user.id, SupportMessage.request_id == payload.request_id
        )
    ):
        fail("SUPPORT_REQUEST_CONFLICT", 409)
    now = datetime.now(UTC)
    ticket = SupportTicket(
        user_id=user.id,
        request_id=payload.request_id,
        creation_digest=digest,
        category=payload.category,
        subject=payload.subject,
        status=SupportStatus.OPEN,
        troubleshooting_metadata=payload.metadata.model_dump(mode="json")
        if payload.metadata
        else {},
        created_at=now,
        updated_at=now,
        last_activity_at=now,
    )
    db.add(ticket)
    db.flush()
    db.add(
        SupportMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            sender_role="member",
            request_id=payload.request_id,
            body=payload.description,
            created_at=now,
        )
    )
    db.commit()
    return TicketResponse.model_validate(ticket)


def list_tickets(
    db: Session,
    user: User,
    *,
    admin: bool,
    status: SupportStatus | None,
    category: SupportCategory | None,
    search: str | None,
    before: UUID | None,
    limit: int,
) -> TicketPage:
    scope = select(SupportTicket)
    if not admin:
        scope = scope.where(SupportTicket.user_id == user.id)
    opened = (
        db.scalar(
            select(func.count()).select_from(
                scope.where(
                    SupportTicket.status.in_([SupportStatus.OPEN, SupportStatus.AWAITING_USER])
                ).subquery()
            )
        )
        or 0
    )
    filtered = scope
    if status is not None:
        filtered = filtered.where(SupportTicket.status == status)
    if category is not None:
        filtered = filtered.where(SupportTicket.category == category)
    if search:
        filtered = filtered.where(SupportTicket.subject.icontains(search, autoescape=True))
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    if before:
        cursor = db.scalar(scope.where(SupportTicket.id == before))
        if cursor is None:
            fail("SUPPORT_TICKET_NOT_FOUND")
        filtered = filtered.where(
            tuple_(SupportTicket.last_activity_at, SupportTicket.id)
            < tuple_(literal(cursor.last_activity_at), literal(cursor.id))
        )
    rows = db.scalars(
        filtered.order_by(SupportTicket.last_activity_at.desc(), SupportTicket.id.desc()).limit(
            limit + 1
        )
    ).all()
    return TicketPage(
        items=[TicketResponse.model_validate(row) for row in rows[:limit]],
        total=total,
        open_count=opened,
        older_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def read_ticket(
    db: Session, user: User, ticket_id: UUID, *, admin: bool, before: UUID | None, limit: int
) -> TicketDetail:
    ticket = owned_ticket(db, user, ticket_id, admin=admin)
    query = select(SupportMessage).where(SupportMessage.ticket_id == ticket.id)
    if before:
        cursor = db.scalar(query.where(SupportMessage.id == before))
        if cursor is None:
            fail("SUPPORT_MESSAGE_NOT_FOUND")
        query = query.where(
            tuple_(SupportMessage.created_at, SupportMessage.id)
            < tuple_(literal(cursor.created_at), literal(cursor.id))
        )
    rows = db.scalars(
        query.order_by(SupportMessage.created_at.desc(), SupportMessage.id.desc()).limit(limit + 1)
    ).all()
    unread = (
        db.scalar(
            select(func.count())
            .select_from(SupportMessage)
            .where(
                SupportMessage.ticket_id == ticket.id,
                SupportMessage.sender_role != ("admin" if admin else "member"),
                ~select(SupportMessageRead.message_id)
                .where(
                    SupportMessageRead.message_id == SupportMessage.id,
                    SupportMessageRead.user_id == user.id,
                )
                .exists(),
            )
        )
        or 0
    )
    return TicketDetail(
        ticket=TicketResponse.model_validate(ticket),
        viewer_id=user.id,
        messages=[SupportMessageResponse.model_validate(row) for row in reversed(rows[:limit])],
        unread_count=unread,
        older_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def send_reply(
    db: Session, user: User, ticket_id: UUID, payload: ReplyInput, *, admin: bool
) -> SupportMessageResponse:
    lock_actor(db, user)
    ticket = owned_ticket(db, user, ticket_id, admin=admin, lock=True)
    previous = db.scalar(
        select(SupportMessage).where(
            SupportMessage.sender_id == user.id, SupportMessage.request_id == payload.request_id
        )
    )
    if previous is not None:
        if (
            previous.ticket_id != ticket.id
            or previous.body != payload.body
            or previous.sender_role != ("admin" if admin else "member")
        ):
            fail("SUPPORT_REQUEST_CONFLICT", 409)
        return SupportMessageResponse.model_validate(previous)
    if ticket.status == SupportStatus.CLOSED:
        fail("SUPPORT_TICKET_CLOSED", 409)
    now = datetime.now(UTC)
    message = SupportMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        sender_role="admin" if admin else "member",
        body=payload.body,
        request_id=payload.request_id,
        created_at=now,
    )
    db.add(message)
    db.flush()
    ticket.status = SupportStatus.AWAITING_USER if admin else SupportStatus.OPEN
    ticket.resolved_at = None
    ticket.last_activity_at = ticket.updated_at = now
    if admin:
        publish_inbox_notification(
            db,
            ticket.user_id,
            "support_ticket_reply",
            "messages",
            f"support-message:{message.id}",
            {"ticket_id": ticket.id},
        )
    db.commit()
    return SupportMessageResponse.model_validate(message)


def change_status(db: Session, user: User, ticket_id: UUID, payload: StatusInput) -> TicketResponse:
    lock_actor(db, user)
    ticket = owned_ticket(db, user, ticket_id, admin=True, lock=True)
    event = db.scalar(
        select(SupportStatusEvent).where(
            SupportStatusEvent.actor_id == user.id,
            SupportStatusEvent.request_id == payload.request_id,
        )
    )
    if event is not None:
        if event.ticket_id != ticket.id or event.status != payload.status:
            fail("SUPPORT_REQUEST_CONFLICT", 409)
        return TicketResponse.model_validate(ticket)
    now = datetime.now(UTC)
    db.add(
        SupportStatusEvent(
            ticket_id=ticket.id,
            actor_id=user.id,
            request_id=payload.request_id,
            previous_status=ticket.status,
            status=payload.status,
            created_at=now,
        )
    )
    ticket.status = payload.status
    ticket.resolved_at = (
        (ticket.resolved_at or now)
        if payload.status in {SupportStatus.RESOLVED, SupportStatus.CLOSED}
        else None
    )
    ticket.updated_at = ticket.last_activity_at = now
    db.commit()
    return TicketResponse.model_validate(ticket)


def mark_read(db: Session, user: User, ticket_id: UUID, message_id: UUID, *, admin: bool) -> None:
    ticket = owned_ticket(db, user, ticket_id, admin=admin)
    cursor = db.scalar(
        select(SupportMessage).where(
            SupportMessage.ticket_id == ticket.id, SupportMessage.id == message_id
        )
    )
    if cursor is None:
        fail("SUPPORT_MESSAGE_NOT_FOUND")
    ids = select(SupportMessage.id, literal(user.id)).where(
        SupportMessage.ticket_id == ticket.id,
        tuple_(SupportMessage.created_at, SupportMessage.id)
        <= tuple_(literal(cursor.created_at), literal(cursor.id)),
    )
    db.execute(
        insert(SupportMessageRead)
        .from_select(["message_id", "user_id"], ids)
        .on_conflict_do_nothing()
    )
    db.commit()
