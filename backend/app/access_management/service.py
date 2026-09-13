from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.exceptions import (
    CampaignConflictError,
    CampaignImmutableError,
    CampaignKindError,
    CampaignNotFoundError,
    CampaignOverlapError,
    CampaignRedemptionUnavailableError,
    CampaignValidationError,
    GrantIdempotencyConflictError,
    GrantNotFoundError,
    UserNotFoundError,
)
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.access_management.repository import (
    count_redemptions,
    get_campaign,
    get_campaign_by_code,
    get_redemption,
    list_active_signup_campaigns,
    list_campaigns,
)
from app.access_management.schemas import (
    AccessCampaignCreateRequest,
    AccessCampaignResponse,
    AccessCampaignUpdateRequest,
    AdminCampaignRedemptionResponse,
    AdminEntitlementSnapshotResponse,
    AdminGrantResponse,
    AdminMemberSummaryResponse,
)
from app.admin_audit.enums import AdminAuditAction
from app.admin_audit.service import record_admin_audit_event
from app.auth.models import User
from app.billing.models import BillingOrder
from app.entitlements.catalog import package_definition
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.models import UserAccessGrant
from app.entitlements.service import grant_package, resolve_access_snapshot
from app.profile.models import UserProfile

MAX_CAMPAIGN_DURATION_DAYS = 3650


@dataclass(frozen=True, slots=True)
class CampaignRedemptionResult:
    campaign: AccessCampaign
    redemption: AccessCampaignRedemption
    grant: UserAccessGrant
    created: bool


@dataclass(frozen=True, slots=True)
class AdminGrantMutationResult:
    grant: UserAccessGrant
    created: bool


@dataclass(frozen=True, slots=True)
class GrantRevocationResult:
    grant: UserAccessGrant
    revoked: bool


def utc_now(value: datetime | None = None) -> datetime:
    reference = value or datetime.now(UTC)
    if reference.tzinfo is None:
        return reference.replace(tzinfo=UTC)
    return reference.astimezone(UTC)


def _optional_utc(value: datetime | None) -> datetime | None:
    return None if value is None else utc_now(value)


def _campaign_state(campaign: AccessCampaign, *, redemption_count: int) -> dict[str, object]:
    return {
        "id": str(campaign.id),
        "code": campaign.code,
        "name": campaign.name,
        "description": campaign.description,
        "kind": campaign.kind.value,
        "package_code": campaign.package_code.value,
        "duration_days": campaign.duration_days,
        "term_weeks": campaign.term_weeks,
        "available_from": campaign.available_from.isoformat()
        if campaign.available_from is not None
        else None,
        "available_until": campaign.available_until.isoformat()
        if campaign.available_until is not None
        else None,
        "is_active": campaign.is_active,
        "max_total_redemptions": campaign.max_total_redemptions,
        "redemption_count": redemption_count,
    }


def _validate_campaign_values(
    *,
    kind: AccessCampaignKind,
    package_code: AccessPackageCode,
    duration_days: int,
    term_weeks: int | None,
    available_from: datetime | None,
    available_until: datetime | None,
    max_total_redemptions: int | None,
) -> None:
    if package_code is AccessPackageCode.FREE:
        raise CampaignValidationError("Campaign package cannot be free")
    if duration_days < 1 or duration_days > MAX_CAMPAIGN_DURATION_DAYS:
        raise CampaignValidationError("duration_days must be between 1 and 3650")
    if term_weeks is not None and term_weeks not in {4, 6, 8}:
        raise CampaignValidationError("term_weeks must be one of 4, 6, or 8")
    if (
        EntitlementCode.TRAINING_PLAN_GENERATE in package_definition(package_code).entitlements
        and term_weeks is None
    ):
        raise CampaignValidationError("term_weeks is required for training access")
    if package_code is AccessPackageCode.LAUNCH_TRIAL and term_weeks != 4:
        raise CampaignValidationError("Launch Trial campaigns require term_weeks=4")
    if (
        available_from is not None
        and available_until is not None
        and utc_now(available_until) < utc_now(available_from)
    ):
        raise CampaignValidationError("available_until must be after available_from")
    if max_total_redemptions is not None and max_total_redemptions < 1:
        raise CampaignValidationError("max_total_redemptions must be positive")
    if kind not in {AccessCampaignKind.SIGNUP_TRIAL, AccessCampaignKind.MANUAL_PROMOTION}:
        raise CampaignValidationError("Unsupported campaign kind")


def _intervals_overlap(
    first_from: datetime | None,
    first_until: datetime | None,
    second_from: datetime | None,
    second_until: datetime | None,
) -> bool:
    minimum = datetime.min.replace(tzinfo=UTC)
    maximum = datetime.max.replace(tzinfo=UTC)
    first_start = utc_now(first_from) if first_from is not None else minimum
    first_end = utc_now(first_until) if first_until is not None else maximum
    second_start = utc_now(second_from) if second_from is not None else minimum
    second_end = utc_now(second_until) if second_until is not None else maximum
    return max(first_start, second_start) <= min(first_end, second_end)


def _ensure_no_signup_overlap(
    db: Session,
    *,
    campaign: AccessCampaign | None,
    kind: AccessCampaignKind,
    is_active: bool,
    available_from: datetime | None,
    available_until: datetime | None,
) -> None:
    if not is_active or kind is not AccessCampaignKind.SIGNUP_TRIAL:
        return
    active_campaigns = db.scalars(
        select(AccessCampaign).where(
            AccessCampaign.kind == AccessCampaignKind.SIGNUP_TRIAL,
            AccessCampaign.is_active.is_(True),
        )
    ).all()
    for other in active_campaigns:
        if campaign is not None and other.id == campaign.id:
            continue
        if _intervals_overlap(
            available_from,
            available_until,
            other.available_from,
            other.available_until,
        ):
            raise CampaignOverlapError(
                f"Signup campaign window overlaps active campaign: {other.code}"
            )


def _campaign_or_raise(db: Session, campaign_id: UUID, *, lock: bool = False) -> AccessCampaign:
    campaign = get_campaign(db, campaign_id, lock=lock)
    if campaign is None:
        raise CampaignNotFoundError
    return campaign


def _campaign_response(db: Session, campaign: AccessCampaign) -> AccessCampaignResponse:
    return AccessCampaignResponse(
        id=campaign.id,
        code=campaign.code,
        name=campaign.name,
        description=campaign.description,
        kind=campaign.kind,
        package_code=campaign.package_code,
        duration_days=campaign.duration_days,
        term_weeks=campaign.term_weeks,  # type: ignore[arg-type]
        available_from=campaign.available_from,
        available_until=campaign.available_until,
        is_active=campaign.is_active,
        max_total_redemptions=campaign.max_total_redemptions,
        redemption_count=count_redemptions(db, campaign.id),
        created_by_user_id=campaign.created_by_user_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def list_campaign_responses(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[AccessCampaignResponse]:
    campaigns = list_campaigns(db, limit=limit, offset=offset)
    return [_campaign_response(db, campaign) for campaign in campaigns]


def get_campaign_response(db: Session, campaign_id: UUID) -> AccessCampaignResponse:
    return _campaign_response(db, _campaign_or_raise(db, campaign_id))


def create_campaign(
    db: Session,
    payload: AccessCampaignCreateRequest,
    *,
    actor_user_id: UUID,
) -> AccessCampaign:
    if get_campaign_by_code(db, payload.code) is not None:
        raise CampaignConflictError("Campaign code is already in use")
    available_from = _optional_utc(payload.available_from)
    available_until = _optional_utc(payload.available_until)
    _validate_campaign_values(
        kind=payload.kind,
        package_code=payload.package_code,
        duration_days=payload.duration_days,
        term_weeks=payload.term_weeks,
        available_from=available_from,
        available_until=available_until,
        max_total_redemptions=payload.max_total_redemptions,
    )
    _ensure_no_signup_overlap(
        db,
        campaign=None,
        kind=payload.kind,
        is_active=payload.is_active,
        available_from=available_from,
        available_until=available_until,
    )
    campaign = AccessCampaign(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        kind=payload.kind,
        package_code=payload.package_code,
        duration_days=payload.duration_days,
        term_weeks=payload.term_weeks,
        available_from=available_from,
        available_until=available_until,
        is_active=payload.is_active,
        max_total_redemptions=payload.max_total_redemptions,
        created_by_user_id=actor_user_id,
    )
    db.add(campaign)
    db.flush()
    record_admin_audit_event(
        db,
        action=AdminAuditAction.ACCESS_CAMPAIGN_CREATED,
        actor_user_id=actor_user_id,
        resource_type="access_campaign",
        resource_key=str(campaign.id),
        after_state=_campaign_state(campaign, redemption_count=0),
    )
    return campaign


def update_campaign(
    db: Session,
    campaign_id: UUID,
    payload: AccessCampaignUpdateRequest,
    *,
    actor_user_id: UUID,
) -> AccessCampaign:
    campaign = _campaign_or_raise(db, campaign_id, lock=True)
    fields = payload.model_fields_set
    if not fields:
        raise CampaignConflictError("At least one campaign field is required")
    redemption_count = count_redemptions(db, campaign.id)
    immutable_fields = {"kind", "package_code", "duration_days", "term_weeks"}
    for field in fields & immutable_fields:
        if getattr(payload, field) != getattr(campaign, field):
            if redemption_count > 0:
                raise CampaignImmutableError(
                    "Campaign package, kind, duration, and term are immutable after redemption"
                )

    before = _campaign_state(campaign, redemption_count=redemption_count)
    for field in fields:
        value = getattr(payload, field)
        if field == "name":
            if value is None:
                raise CampaignConflictError("Campaign name cannot be null")
            value = value.strip()
        if field in {"available_from", "available_until"}:
            value = _optional_utc(value)
        if field in {"kind", "package_code"} and value is None:
            raise CampaignConflictError(f"Campaign {field} cannot be null")
        setattr(campaign, field, value)

    _validate_campaign_values(
        kind=campaign.kind,
        package_code=campaign.package_code,
        duration_days=campaign.duration_days,
        term_weeks=campaign.term_weeks,
        available_from=campaign.available_from,
        available_until=campaign.available_until,
        max_total_redemptions=campaign.max_total_redemptions,
    )
    _ensure_no_signup_overlap(
        db,
        campaign=campaign,
        kind=campaign.kind,
        is_active=campaign.is_active,
        available_from=campaign.available_from,
        available_until=campaign.available_until,
    )
    db.flush()
    record_admin_audit_event(
        db,
        action=AdminAuditAction.ACCESS_CAMPAIGN_UPDATED,
        actor_user_id=actor_user_id,
        resource_type="access_campaign",
        resource_key=str(campaign.id),
        before_state=before,
        after_state=_campaign_state(campaign, redemption_count=redemption_count),
    )
    return campaign


def set_campaign_active(
    db: Session,
    campaign_id: UUID,
    is_active: bool,
    *,
    actor_user_id: UUID,
) -> AccessCampaign:
    campaign = _campaign_or_raise(db, campaign_id, lock=True)
    if campaign.is_active is is_active:
        return campaign
    before = _campaign_state(campaign, redemption_count=count_redemptions(db, campaign.id))
    if is_active:
        _ensure_no_signup_overlap(
            db,
            campaign=campaign,
            kind=campaign.kind,
            is_active=True,
            available_from=campaign.available_from,
            available_until=campaign.available_until,
        )
    campaign.is_active = is_active
    db.flush()
    record_admin_audit_event(
        db,
        action=(
            AdminAuditAction.ACCESS_CAMPAIGN_ACTIVATED
            if is_active
            else AdminAuditAction.ACCESS_CAMPAIGN_DEACTIVATED
        ),
        actor_user_id=actor_user_id,
        resource_type="access_campaign",
        resource_key=str(campaign.id),
        before_state=before,
        after_state=_campaign_state(campaign, redemption_count=count_redemptions(db, campaign.id)),
    )
    return campaign


def redeem_campaign(
    db: Session,
    campaign_id: UUID,
    user_id: UUID,
    *,
    now: datetime | None = None,
    actor_user_id: UUID | None = None,
    reason: str | None = None,
    manual: bool = False,
) -> CampaignRedemptionResult:
    reference = utc_now(now)
    campaign = _campaign_or_raise(db, campaign_id, lock=True)
    if manual and campaign.kind is not AccessCampaignKind.MANUAL_PROMOTION:
        raise CampaignKindError("Only manual promotion campaigns can be applied by an Admin")
    if not manual and campaign.kind is not AccessCampaignKind.SIGNUP_TRIAL:
        raise CampaignKindError("Manual promotion campaigns do not auto-apply at signup")
    if manual and (actor_user_id is None or not reason or not reason.strip()):
        raise CampaignConflictError("A reason is required for manual campaign redemption")
    if db.get(User, user_id) is None:
        raise UserNotFoundError

    existing = get_redemption(db, campaign.id, user_id, lock=True)
    idempotency_key = f"campaign:{campaign.code}:v1"
    if existing is not None:
        grant = (
            db.get(UserAccessGrant, existing.access_grant_id)
            if existing.access_grant_id is not None
            else None
        )
        if grant is None:
            grant = grant_package(
                db,
                user_id,
                existing.package_code_snapshot,
                source=(
                    GrantSource.LAUNCH_TRIAL
                    if existing.package_code_snapshot is AccessPackageCode.LAUNCH_TRIAL
                    else GrantSource.PROMOTION
                ),
                starts_at=reference,
                ends_at=reference + timedelta(days=existing.duration_days_snapshot),
                idempotency_key=idempotency_key,
                term_weeks=existing.term_weeks_snapshot,
            )
            existing.access_grant_id = grant.id
            db.flush()
        return CampaignRedemptionResult(campaign, existing, grant, False)

    if not campaign.is_active:
        raise CampaignRedemptionUnavailableError("Campaign is inactive")
    if campaign.available_from is not None and reference < utc_now(campaign.available_from):
        raise CampaignRedemptionUnavailableError("Campaign is not available yet")
    if campaign.available_until is not None and reference > utc_now(campaign.available_until):
        raise CampaignRedemptionUnavailableError("Campaign eligibility has ended")
    if (
        campaign.max_total_redemptions is not None
        and count_redemptions(db, campaign.id) >= campaign.max_total_redemptions
    ):
        raise CampaignRedemptionUnavailableError("Campaign redemption limit has been reached")

    package_code = AccessPackageCode(campaign.package_code)
    grant = grant_package(
        db,
        user_id,
        package_code,
        source=(
            GrantSource.LAUNCH_TRIAL
            if package_code is AccessPackageCode.LAUNCH_TRIAL
            else GrantSource.PROMOTION
        ),
        starts_at=reference,
        ends_at=reference + timedelta(days=campaign.duration_days),
        idempotency_key=idempotency_key,
        term_weeks=campaign.term_weeks,
    )
    redemption = AccessCampaignRedemption(
        campaign_id=campaign.id,
        user_id=user_id,
        access_grant_id=grant.id,
        package_code_snapshot=package_code,
        duration_days_snapshot=campaign.duration_days,
        term_weeks_snapshot=campaign.term_weeks,
        redeemed_at=reference,
    )
    db.add(redemption)
    db.flush()
    if manual:
        record_admin_audit_event(
            db,
            action=AdminAuditAction.ACCESS_CAMPAIGN_MANUALLY_REDEEMED,
            actor_user_id=actor_user_id,
            target_user_id=user_id,
            resource_type="access_campaign_redemption",
            resource_key=str(redemption.id),
            reason=reason.strip() if reason is not None else None,
            after_state={
                "campaign_id": str(campaign.id),
                "campaign_code": campaign.code,
                "grant_id": str(grant.id),
                "package_code": package_code.value,
                "term_weeks": campaign.term_weeks,
                "ends_at": grant.ends_at.isoformat() if grant.ends_at is not None else None,
            },
        )
    return CampaignRedemptionResult(campaign, redemption, grant, True)


def provision_signup_campaigns(
    db: Session,
    user_id: UUID,
    *,
    now: datetime | None = None,
) -> list[CampaignRedemptionResult]:
    if db.get(User, user_id) is None:
        raise UserNotFoundError
    reference = utc_now(now)
    results: list[CampaignRedemptionResult] = []
    for campaign in list_active_signup_campaigns(db):
        try:
            results.append(redeem_campaign(db, campaign.id, user_id, now=reference))
        except CampaignRedemptionUnavailableError:
            continue
    return results


def member_summary(
    db: Session,
    user: User,
    *,
    now: datetime | None = None,
) -> AdminMemberSummaryResponse:
    snapshot = resolve_access_snapshot(db, user.id, now=now)
    grants = list_all_grants(db, user.id)
    reference = utc_now(now)
    paid_access_end = max(
        (
            grant.ends_at
            for grant in grants
            if grant.source is GrantSource.SUBSCRIPTION
            and grant.revoked_at is None
            and grant.starts_at <= reference
            and (grant.ends_at is None or grant.ends_at > reference)
            and grant.ends_at is not None
        ),
        default=None,
    )
    profile = db.get(UserProfile, user.id)
    return AdminMemberSummaryResponse(
        user_id=user.id,
        display_name=profile.display_name if profile is not None else None,
        email=user.email,
        phone_number=user.phone_number,
        created_at=user.created_at,
        primary_package=snapshot.primary_package,
        active_packages=list(snapshot.active_packages),
        trial_active=snapshot.trial.active,
        trial_ends_at=snapshot.trial.ends_at,
        paid_access_end=paid_access_end,
    )


def list_all_grants(db: Session, user_id: UUID) -> list[UserAccessGrant]:
    return list(
        db.scalars(
            select(UserAccessGrant)
            .where(UserAccessGrant.user_id == user_id)
            .order_by(UserAccessGrant.starts_at.desc(), UserAccessGrant.created_at.desc())
        ).all()
    )


def entitlement_snapshot(
    db: Session,
    user_id: UUID,
    *,
    now: datetime | None = None,
) -> AdminEntitlementSnapshotResponse:
    snapshot = resolve_access_snapshot(db, user_id, now=now)
    return AdminEntitlementSnapshotResponse(
        primary_package=snapshot.primary_package,
        active_packages=list(snapshot.active_packages),
        granted_entitlements=sorted(snapshot.granted_entitlements, key=lambda code: code.value),
        trial_active=snapshot.trial.active,
        trial_ends_at=snapshot.trial.ends_at,
    )


def grant_status(grant: UserAccessGrant, *, now: datetime | None = None) -> str:
    reference = utc_now(now)
    if grant.revoked_at is not None:
        return "revoked"
    if grant.starts_at > reference:
        return "future"
    if grant.ends_at is not None and grant.ends_at <= reference:
        return "expired"
    return "active"


def grant_response(
    db: Session,
    grant: UserAccessGrant,
    *,
    now: datetime | None = None,
) -> AdminGrantResponse:
    from app.access_management.models import AccessCampaignRedemption

    redemption_row = db.execute(
        select(AccessCampaignRedemption, AccessCampaign)
        .join(AccessCampaign, AccessCampaign.id == AccessCampaignRedemption.campaign_id)
        .where(AccessCampaignRedemption.access_grant_id == grant.id)
    ).first()
    campaign = None
    if redemption_row is not None:
        _redemption, campaign = redemption_row
    order = db.scalar(select(BillingOrder).where(BillingOrder.access_grant_id == grant.id))
    current = grant_status(grant, now=now)
    return AdminGrantResponse(
        id=grant.id,
        package_code=AccessPackageCode(grant.package_code),
        source=GrantSource(grant.source),
        term_weeks=grant.term_weeks,  # type: ignore[arg-type]
        starts_at=grant.starts_at,
        ends_at=grant.ends_at,
        revoked_at=grant.revoked_at,
        created_at=grant.created_at,
        status=current,  # type: ignore[arg-type]
        is_currently_active=current == "active",
        billing_order_id=order.id if order is not None else None,
        campaign_id=campaign.id if campaign is not None else None,
        campaign_name=campaign.name if campaign is not None else None,
    )


def user_or_raise(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError
    return user


def user_access_response(
    db: Session,
    user_id: UUID,
    *,
    now: datetime | None = None,
) -> tuple[AdminMemberSummaryResponse, AdminEntitlementSnapshotResponse, list[AdminGrantResponse]]:
    user = user_or_raise(db, user_id)
    grants = list_all_grants(db, user_id)
    return (
        member_summary(db, user, now=now),
        entitlement_snapshot(db, user_id, now=now),
        [grant_response(db, grant, now=now) for grant in grants],
    )


def manual_redemption_response(
    db: Session,
    result: CampaignRedemptionResult,
    *,
    now: datetime | None = None,
) -> AdminCampaignRedemptionResponse:
    return AdminCampaignRedemptionResponse(
        campaign=_campaign_response(db, result.campaign),
        grant=grant_response(db, result.grant, now=now),
    )


def grant_or_raise(db: Session, grant_id: UUID, *, lock: bool = False) -> UserAccessGrant:
    statement = select(UserAccessGrant).where(UserAccessGrant.id == grant_id)
    if lock:
        statement = statement.with_for_update()
    grant = db.scalar(statement)
    if grant is None:
        raise GrantNotFoundError
    return grant


def _admin_grant_state(grant: UserAccessGrant) -> dict[str, object]:
    return {
        "id": str(grant.id),
        "user_id": str(grant.user_id),
        "package_code": AccessPackageCode(grant.package_code).value,
        "source": GrantSource(grant.source).value,
        "term_weeks": grant.term_weeks,
        "starts_at": grant.starts_at.isoformat(),
        "ends_at": grant.ends_at.isoformat() if grant.ends_at is not None else None,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at is not None else None,
    }


def create_admin_grant(
    db: Session,
    user_id: UUID,
    *,
    package_code: AccessPackageCode | str,
    term_weeks: int | None,
    starts_at: datetime | None,
    ends_at: datetime,
    reason: str,
    client_idempotency_key: str,
    actor_user_id: UUID,
) -> AdminGrantMutationResult:
    user_or_raise(db, user_id)
    code = AccessPackageCode(package_code)
    start = utc_now(starts_at)
    end = utc_now(ends_at)
    _validate_campaign_values(
        kind=AccessCampaignKind.MANUAL_PROMOTION,
        package_code=code,
        duration_days=1,
        term_weeks=term_weeks,
        available_from=None,
        available_until=None,
        max_total_redemptions=None,
    )
    if end <= start:
        raise CampaignConflictError("ends_at must be after starts_at")
    if not reason.strip():
        raise CampaignConflictError("A reason is required for manual access grant")
    idempotency_key = f"admin:{client_idempotency_key}"
    existing = db.scalar(
        select(UserAccessGrant)
        .where(
            UserAccessGrant.user_id == user_id,
            UserAccessGrant.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    if existing is not None:
        same_request = (
            AccessPackageCode(existing.package_code) is code
            and existing.term_weeks == term_weeks
            and utc_now(existing.starts_at) == start
            and (
                existing.ends_at is not None
                and utc_now(existing.ends_at) == end
            )
        )
        if not same_request:
            raise GrantIdempotencyConflictError(
                "The idempotency key is already used for a different grant"
            )
        return AdminGrantMutationResult(existing, False)

    grant = grant_package(
        db,
        user_id,
        code,
        source=GrantSource.ADMIN,
        starts_at=start,
        ends_at=end,
        idempotency_key=idempotency_key,
        term_weeks=term_weeks,
    )
    db.flush()
    record_admin_audit_event(
        db,
        action=AdminAuditAction.ACCESS_GRANT_CREATED,
        actor_user_id=actor_user_id,
        target_user_id=user_id,
        resource_type="access_grant",
        resource_key=str(grant.id),
        reason=reason.strip(),
        after_state=_admin_grant_state(grant),
    )
    return AdminGrantMutationResult(grant, True)


def revoke_grant(
    db: Session,
    grant_id: UUID,
    *,
    reason: str,
    actor_user_id: UUID,
    now: datetime | None = None,
) -> GrantRevocationResult:
    if not reason.strip():
        raise CampaignConflictError("A reason is required for access revocation")
    grant = grant_or_raise(db, grant_id, lock=True)
    if grant.revoked_at is not None:
        return GrantRevocationResult(grant, False)
    before = _admin_grant_state(grant)
    grant.revoked_at = utc_now(now)
    db.flush()
    record_admin_audit_event(
        db,
        action=AdminAuditAction.ACCESS_GRANT_REVOKED,
        actor_user_id=actor_user_id,
        target_user_id=grant.user_id,
        resource_type="access_grant",
        resource_key=str(grant.id),
        reason=reason.strip(),
        before_state=before,
        after_state=_admin_grant_state(grant),
    )
    return GrantRevocationResult(grant, True)
