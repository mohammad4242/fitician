from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProgramMessage(Base):
    __tablename__ = "program_messages"
    __table_args__ = (
        UniqueConstraint("sender_id", "request_id", name="uq_program_message_request"),
        CheckConstraint(
            "(workout_review_id IS NULL) <> (nutrition_review_id IS NULL)",
            name="ck_program_message_reference",
        ),
        CheckConstraint(
            "char_length(btrim(body)) BETWEEN 1 AND 2000", name="ck_program_message_body"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workout_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workout_plan_reviews.id", ondelete="CASCADE"), index=True
    )
    nutrition_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("nutrition_plan_physician_reviews.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProgramMessageRead(Base):
    __tablename__ = "program_message_reads"
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
