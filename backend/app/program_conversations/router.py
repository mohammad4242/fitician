from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, literal, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.elements import ColumnElement

from app.auth.dependencies import require_authenticated_mutation
from app.body_analysis.enums import SpecialistRole
from app.body_analysis.models import UserSpecialistRole
from app.nutrition.clinical_service import is_physician
from app.nutrition.models import NutritionPlanPhysicianReview, NutritionWeeklyPlan
from app.workout_reviews.dependencies import AuthenticatedUser, DatabaseSession
from app.workout_reviews.models import WorkoutPlanReview
from app.workouts.models import WorkoutPlan

from .models import ProgramMessage, ProgramMessageRead

Kind = Literal["workout", "nutrition"]
router = APIRouter(prefix="/api/v1/program-conversations", tags=["program-conversations"])


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=2000)
    request_id: UUID

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        value = value.strip()
        if not value or "\x00" in value:
            raise ValueError("Message must not be blank")
        return value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    body: str
    created_at: datetime
    sender_id: UUID


class ConversationResponse(BaseModel):
    review_id: UUID | None
    available: bool
    viewer_id: UUID
    messages: list[MessageResponse]
    unread_count: int
    older_cursor: UUID | None = None


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID


def _reference(kind: Kind, review_id: UUID) -> ColumnElement[bool]:
    return (
        ProgramMessage.workout_review_id
        if kind == "workout"
        else ProgramMessage.nutrition_review_id
    ) == review_id


def _participants(
    db: DatabaseSession, user: AuthenticatedUser, kind: Kind, review_id: UUID
) -> tuple[UUID, UUID | None]:
    review: WorkoutPlanReview | NutritionPlanPhysicianReview | None
    if kind == "workout":
        review = db.scalar(
            select(WorkoutPlanReview).where(WorkoutPlanReview.id == review_id).with_for_update()
        )
    else:
        review = db.scalar(
            select(NutritionPlanPhysicianReview)
            .where(NutritionPlanPhysicianReview.id == review_id)
            .with_for_update()
        )
    if review is None:
        raise HTTPException(404, detail={"code": "CONVERSATION_NOT_FOUND"})
    if isinstance(review, WorkoutPlanReview):
        member_id = review.user_id
        specialist_id = review.claimed_by_user_id
    else:
        plan = db.get(NutritionWeeklyPlan, review.plan_id)
        if plan is None:
            raise HTTPException(404, detail={"code": "CONVERSATION_NOT_FOUND"})
        member_id = plan.user_id
        specialist_id = review.physician_user_id
    role_exists = specialist_id is not None and (
        is_physician(db, specialist_id)
        if kind == "nutrition"
        else db.scalar(
            select(UserSpecialistRole.user_id).where(
                UserSpecialistRole.user_id == specialist_id,
                UserSpecialistRole.role == SpecialistRole.COACH,
            )
        )
        is not None
    )
    if user.id != member_id and (user.id != specialist_id or not role_exists):
        raise HTTPException(404, detail={"code": "CONVERSATION_NOT_FOUND"})
    return member_id, specialist_id if role_exists else None


def _read(
    db: DatabaseSession,
    user: AuthenticatedUser,
    kind: Kind,
    review_id: UUID,
    before: UUID | None,
    limit: int,
) -> ConversationResponse:
    _, specialist = _participants(db, user, kind, review_id)
    reference = _reference(kind, review_id)
    query = select(ProgramMessage).where(reference)
    if before is not None:
        cursor = db.scalar(select(ProgramMessage).where(reference, ProgramMessage.id == before))
        if cursor is None:
            raise HTTPException(404, detail={"code": "MESSAGE_NOT_FOUND"})
        query = query.where(
            tuple_(ProgramMessage.created_at, ProgramMessage.id)
            < tuple_(literal(cursor.created_at), literal(cursor.id))
        )
    rows = db.scalars(
        query.order_by(ProgramMessage.created_at.desc(), ProgramMessage.id.desc()).limit(limit + 1)
    ).all()
    unread = (
        db.scalar(
            select(func.count())
            .select_from(ProgramMessage)
            .where(
                reference,
                ProgramMessage.sender_id != user.id,
                ~select(ProgramMessageRead.message_id)
                .where(
                    ProgramMessageRead.message_id == ProgramMessage.id,
                    ProgramMessageRead.user_id == user.id,
                )
                .exists(),
            )
        )
        or 0
    )
    visible = list(rows[:limit])
    return ConversationResponse(
        review_id=review_id,
        available=specialist is not None,
        viewer_id=user.id,
        messages=[MessageResponse.model_validate(row) for row in reversed(visible)],
        unread_count=unread,
        older_cursor=visible[-1].id if len(rows) > limit else None,
    )


@router.get("/{kind}/by-plan/{plan_id}", response_model=ConversationResponse)
def read_by_plan(
    kind: Kind, plan_id: UUID, db: DatabaseSession, user: AuthenticatedUser
) -> ConversationResponse:
    review: WorkoutPlanReview | NutritionPlanPhysicianReview | None
    plan: WorkoutPlan | NutritionWeeklyPlan | None
    if kind == "workout":
        review = db.scalar(
            select(WorkoutPlanReview).where(
                or_(
                    WorkoutPlanReview.source_plan_id == plan_id,
                    WorkoutPlanReview.proposed_plan_id == plan_id,
                    WorkoutPlanReview.approved_plan_id == plan_id,
                )
            )
        )
        plan = db.get(WorkoutPlan, plan_id)
    else:
        review = db.scalar(
            select(NutritionPlanPhysicianReview).where(
                NutritionPlanPhysicianReview.plan_id == plan_id
            )
        )
        plan = db.get(NutritionWeeklyPlan, plan_id)
    if review is not None:
        return _read(db, user, kind, review.id, None, 50)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(404, detail={"code": "CONVERSATION_NOT_FOUND"})
    return ConversationResponse(
        review_id=None, available=False, viewer_id=user.id, messages=[], unread_count=0
    )


@router.get("/{kind}/{review_id}", response_model=ConversationResponse)
def read_conversation(
    kind: Kind,
    review_id: UUID,
    db: DatabaseSession,
    user: AuthenticatedUser,
    before: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ConversationResponse:
    return _read(db, user, kind, review_id, before, limit)


@router.post(
    "/{kind}/{review_id}",
    response_model=MessageResponse,
    status_code=201,
    dependencies=[Depends(require_authenticated_mutation)],
)
def send_message(
    kind: Kind, review_id: UUID, payload: MessageInput, db: DatabaseSession, user: AuthenticatedUser
) -> MessageResponse:
    member, specialist = _participants(db, user, kind, review_id)
    if specialist is None:
        raise HTTPException(409, detail={"code": "SPECIALIST_NOT_ASSIGNED"})
    values = {
        "id": uuid4(),
        "sender_id": user.id,
        "body": payload.body,
        "request_id": payload.request_id,
        "workout_review_id" if kind == "workout" else "nutrition_review_id": review_id,
    }
    inserted = db.scalar(
        insert(ProgramMessage)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_program_message_request")
        .returning(ProgramMessage.id)
    )
    message = db.scalar(
        select(ProgramMessage).where(
            ProgramMessage.sender_id == user.id, ProgramMessage.request_id == payload.request_id
        )
    )
    assert message is not None
    if (
        message.body != payload.body
        or (message.workout_review_id if kind == "workout" else message.nutrition_review_id)
        != review_id
    ):
        raise HTTPException(409, detail={"code": "MESSAGE_REQUEST_CONFLICT"})
    if inserted is not None:
        from app.notifications.inbox import publish_inbox_notification

        recipient = specialist if user.id == member else member
        publish_inbox_notification(
            db,
            recipient,
            "program_message",
            "messages",
            f"message:{message.id}",
            {"kind": kind, "review_id": str(review_id)},
        )
    db.commit()
    return MessageResponse.model_validate(message)


@router.put(
    "/{kind}/{review_id}/read",
    status_code=204,
    dependencies=[Depends(require_authenticated_mutation)],
)
def mark_read(
    kind: Kind, review_id: UUID, payload: ReadInput, db: DatabaseSession, user: AuthenticatedUser
) -> None:
    _participants(db, user, kind, review_id)
    reference = _reference(kind, review_id)
    target = db.scalar(
        select(ProgramMessage).where(reference, ProgramMessage.id == payload.message_id)
    )
    if target is None:
        raise HTTPException(404, detail={"code": "MESSAGE_NOT_FOUND"})
    rows = select(ProgramMessage.id, literal(user.id)).where(
        reference,
        ProgramMessage.sender_id != user.id,
        tuple_(ProgramMessage.created_at, ProgramMessage.id)
        <= tuple_(literal(target.created_at), literal(target.id)),
    )
    db.execute(
        insert(ProgramMessageRead)
        .from_select(["message_id", "user_id"], rows)
        .on_conflict_do_nothing()
    )
    db.commit()
