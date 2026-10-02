from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.support.enums import SupportCategory, SupportStatus


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_support_ticket_request"),
        CheckConstraint(
            "category IN ('technical', 'account', 'billing', 'workout', 'nutrition', "
            "'body_analysis', 'feature_request', 'other')",
            name="ck_support_ticket_category",
        ),
        CheckConstraint(
            "status IN ('open', 'awaiting_user', 'resolved', 'closed')",
            name="ck_support_ticket_status",
        ),
        CheckConstraint(
            "char_length(btrim(subject)) BETWEEN 1 AND 160", name="ck_support_ticket_subject"
        ),
        CheckConstraint(
            "(status IN ('resolved', 'closed')) = (resolved_at IS NOT NULL)",
            name="ck_support_ticket_resolution",
        ),
        Index("ix_support_ticket_owner_activity", "user_id", "last_activity_at", "id"),
        Index("ix_support_ticket_status_activity", "status", "last_activity_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    creation_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[SupportCategory] = mapped_column(
        Enum(
            SupportCategory,
            native_enum=False,
            create_constraint=False,
            values_callable=lambda items: [item.value for item in items],
            name="ck_support_ticket_category",
        ),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[SupportStatus] = mapped_column(
        Enum(
            SupportStatus,
            native_enum=False,
            create_constraint=False,
            values_callable=lambda items: [item.value for item in items],
            name="ck_support_ticket_status",
        ),
        nullable=False,
        default=SupportStatus.OPEN,
    )
    troubleshooting_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (
        UniqueConstraint("sender_id", "request_id", name="uq_support_message_request"),
        CheckConstraint(
            "sender_role IN ('member', 'admin')", name="ck_support_message_sender_role"
        ),
        CheckConstraint(
            "char_length(btrim(body)) BETWEEN 1 AND 4000", name="ck_support_message_body"
        ),
        Index("ix_support_message_ticket_created", "ticket_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sender_role: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SupportMessageRead(Base):
    __tablename__ = "support_message_reads"
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("support_messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class SupportStatusEvent(Base):
    __tablename__ = "support_status_events"
    __table_args__ = (
        UniqueConstraint("actor_id", "request_id", name="uq_support_status_request"),
        Index("ix_support_status_ticket_created", "ticket_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
