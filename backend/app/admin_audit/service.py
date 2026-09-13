from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.models import AdminAuditEvent

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
