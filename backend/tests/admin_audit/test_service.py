import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.schemas import AccessCampaignCreateRequest
from app.access_management.service import create_campaign
from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.models import AdminAuditEvent
from app.admin_audit.service import record_admin_audit_event


def test_audit_action_codes_are_stable() -> None:
    assert AdminAuditAction.BILLING_OFFER_UPDATED.value == "billing.offer.updated"
    assert AdminAuditAction.ACCESS_GRANT_REVOKED.value == "access.grant.revoked"


def test_record_admin_audit_event_adds_safe_business_state_without_committing(
    db: Session,
) -> None:
    event = record_admin_audit_event(
        db,
        actor_user_id=None,
        target_user_id=None,
        action=AdminAuditAction.ACCESS_GRANT_CREATED,
        resource_type="access_grant",
        resource_key="grant-1",
        reason="support compensation",
        before_state=None,
        after_state={"package_code": "training", "ends_at": "2026-10-01T00:00:00Z"},
    )

    assert event.id is not None
    assert db.get(AdminAuditEvent, event.id) is event
    assert db.scalar(select(AdminAuditEvent).where(AdminAuditEvent.id == event.id)) is event
    assert event.after_state == {
        "package_code": "training",
        "ends_at": "2026-10-01T00:00:00Z",
    }


@pytest.mark.parametrize(
    "key",
    ["password_hash", "session_token", "provider_secret", "card_number"],
)
def test_audit_rejects_sensitive_business_state(db: Session, key: str) -> None:
    with pytest.raises(ValueError, match="sensitive"):
        record_admin_audit_event(
            db,
            action=AdminAuditAction.ACCESS_GRANT_CREATED,
            resource_type="access_grant",
            resource_key="grant-1",
            after_state={key: "redacted"},
        )


def test_campaign_mutation_can_roll_back_with_audit_failure(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_audit(*args: object, **kwargs: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.access_management.service.record_admin_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        create_campaign(
            db,
            AccessCampaignCreateRequest(
                code="audit-rollback",
                name="Audit rollback",
                kind=AccessCampaignKind.MANUAL_PROMOTION,
                package_code="complete",
                duration_days=56,
                term_weeks=8,
            ),
            actor_user_id=None,
        )

    db.rollback()
    from app.access_management.repository import get_campaign_by_code

    assert get_campaign_by_code(db, "audit-rollback") is None
