from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.models import AdminAuditEvent
from app.admin_audit.schemas import AdminAuditActorSummary, AdminAuditEventResponse
from app.auth.models import User
from app.profile.models import UserProfile

_FORBIDDEN_STATE_KEYS = frozenset(
    {
        "password",
        "passwordhash",
        "sessiontoken",
        "refreshtoken",
        "accesstoken",
        "token",
        "providersecret",
        "callbackpayload",
        "cardnumber",
        "cvv",
        "cvc",
        "secret",
        "apikey",
        "googlesub",
        "applesub",
    }
)


def _normalized_key(key: str) -> str:
    return "".join(character for character in key.casefold() if character.isalnum())


def _assert_safe_state(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("Audit business state keys must be strings")
            if _normalized_key(key) in _FORBIDDEN_STATE_KEYS:
                raise ValueError(f"Audit business state contains sensitive field: {key}")
            _assert_safe_state(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _assert_safe_state(child)


def _safe_state(state: Mapping[str, object] | None) -> dict[str, object] | None:
    if state is None:
        return None
    _assert_safe_state(state)
    return dict(state)


def record_admin_audit_event(
    db: Session,
    *,
    action: AdminAuditAction | str,
    resource_type: str,
    resource_key: str,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    reason: str | None = None,
    before_state: Mapping[str, object] | None = None,
    after_state: Mapping[str, object] | None = None,
    created_at: datetime | None = None,
) -> AdminAuditEvent:
    event = AdminAuditEvent(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=AdminAuditAction(action),
        resource_type=resource_type,
        resource_key=resource_key,
        reason=reason,
        before_state=_safe_state(before_state),
        after_state=_safe_state(after_state),
        created_at=(created_at.astimezone(UTC) if created_at and created_at.tzinfo else created_at),
    )
    db.add(event)
    db.flush()
    return event


def _actor_summary(user: User | None, profile: UserProfile | None) -> AdminAuditActorSummary | None:
    if user is None:
        return None
    return AdminAuditActorSummary(
        user_id=user.id,
        display_name=profile.display_name if profile is not None else None,
        email=user.email,
        phone_number=user.phone_number,
    )


def list_admin_audit_events(
    db: Session,
    *,
    action: AdminAuditAction | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    resource_type: str | None = None,
    from_datetime: datetime | None = None,
    to_datetime: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AdminAuditEventResponse]:
    actor = aliased(User)
    actor_profile = aliased(UserProfile)
    target = aliased(User)
    target_profile = aliased(UserProfile)
    statement = (
        select(
            AdminAuditEvent,
            actor,
            actor_profile,
            target,
            target_profile,
        )
        .outerjoin(actor, actor.id == AdminAuditEvent.actor_user_id)
        .outerjoin(actor_profile, actor_profile.user_id == actor.id)
        .outerjoin(target, target.id == AdminAuditEvent.target_user_id)
        .outerjoin(target_profile, target_profile.user_id == target.id)
        .order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if action is not None:
        statement = statement.where(AdminAuditEvent.action == action)
    if actor_user_id is not None:
        statement = statement.where(AdminAuditEvent.actor_user_id == actor_user_id)
    if target_user_id is not None:
        statement = statement.where(AdminAuditEvent.target_user_id == target_user_id)
    if resource_type is not None:
        statement = statement.where(AdminAuditEvent.resource_type == resource_type)
    if from_datetime is not None:
        statement = statement.where(AdminAuditEvent.created_at >= from_datetime)
    if to_datetime is not None:
        statement = statement.where(AdminAuditEvent.created_at <= to_datetime)

    rows = db.execute(statement).all()
    return [
        AdminAuditEventResponse(
            id=event.id,
            action=event.action,
            actor=_actor_summary(actor_user, actor_profile_row),
            target=_actor_summary(target_user, target_profile_row),
            resource_type=event.resource_type,
            resource_key=event.resource_key,
            reason=event.reason,
            before_state=event.before_state,
            after_state=event.after_state,
            created_at=event.created_at,
        )
        for event, actor_user, actor_profile_row, target_user, target_profile_row in rows
    ]
