from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.models import AdminAuditEvent
from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant
from app.entitlements.service import grant_package


def test_member_deletion_cascades_redemption_and_nulls_audit_target_while_history_remains(
    db: Session,
) -> None:
    actor = User(email=f"audit-actor-{uuid4()}@example.com", password_hash="hash")
    member = User(email=f"audit-member-{uuid4()}@example.com", password_hash="hash")
    db.add_all([actor, member])
    db.flush()
    campaign = AccessCampaign(
        code=f"deletion-{uuid4()}",
        name="Deletion campaign",
        kind=AccessCampaignKind.MANUAL_PROMOTION,
        package_code=AccessPackageCode.COMPLETE,
        duration_days=56,
        term_weeks=8,
        is_active=True,
        created_by_user_id=actor.id,
    )
    db.add(campaign)
    db.flush()
    grant = grant_package(
        db,
        member.id,
        AccessPackageCode.COMPLETE,
        source=GrantSource.ADMIN,
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(days=56),
        term_weeks=8,
        idempotency_key=f"deletion-{uuid4()}",
    )
    redemption = AccessCampaignRedemption(
        campaign_id=campaign.id,
        user_id=member.id,
        access_grant_id=grant.id,
        package_code_snapshot=AccessPackageCode.COMPLETE,
        duration_days_snapshot=56,
        term_weeks_snapshot=8,
    )
    audit = AdminAuditEvent(
        actor_user_id=actor.id,
        target_user_id=member.id,
        action=AdminAuditAction.ACCESS_GRANT_CREATED,
        resource_type="access_grant",
        resource_key=str(grant.id),
        reason="deletion test",
    )
    db.add_all([redemption, audit])
    db.flush()
    grant_id = grant.id
    redemption_id = redemption.id
    audit_id = audit.id
    campaign_id = campaign.id

    db.execute(delete(User).where(User.id == member.id))
    db.flush()
    db.expire_all()

    assert db.get(AccessCampaignRedemption, redemption_id) is None
    assert db.get(UserAccessGrant, grant_id) is None
    retained_audit = db.get(AdminAuditEvent, audit_id)
    assert retained_audit is not None
    assert retained_audit.actor_user_id == actor.id
    assert retained_audit.target_user_id is None

    db.execute(delete(User).where(User.id == actor.id))
    db.flush()
    db.expire_all()

    retained_campaign = db.get(AccessCampaign, campaign_id)
    retained_audit = db.scalar(select(AdminAuditEvent).where(AdminAuditEvent.id == audit_id))
    assert retained_campaign is not None
    assert retained_campaign.created_by_user_id is None
    assert retained_audit is not None
    assert retained_audit.actor_user_id is None
