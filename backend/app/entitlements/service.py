from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import asc, func, or_, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.catalog import (
    QUOTA_POLICIES,
    QuotaPolicy,
    eligible_upgrade_packages,
    package_definition,
    package_rank,
)
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.exceptions import (
    AccessTermTooShortError,
    EntitlementQuotaExceededError,
    EntitlementRequiredError,
)
from app.entitlements.models import EntitlementUsageEvent, UserAccessGrant

VALID_ACCESS_TERM_WEEKS = frozenset({4, 6, 8})


@dataclass(frozen=True, slots=True)
class TrialState:
    active: bool
    ends_at: datetime | None


@dataclass(frozen=True, slots=True)
class AccessSnapshot:
    primary_package: AccessPackageCode
    active_packages: tuple[AccessPackageCode, ...]
    granted_entitlements: frozenset[EntitlementCode]
    grants: tuple[UserAccessGrant, ...]
    trial: TrialState

    def has(self, entitlement: EntitlementCode | str) -> bool:
        return EntitlementCode(entitlement) in self.granted_entitlements


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    entitlement: EntitlementCode
    limit: int
    used: int
    remaining: int
    window_days: int
    reset_at: datetime


def _utc_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _utc_now(value)


def list_active_grants(
    db: Session,
    user_id: UUID,
    *,
    now: datetime | None = None,
) -> list[UserAccessGrant]:
    reference = _utc_now(now)
    statement = (
        select(UserAccessGrant)
        .where(
            UserAccessGrant.user_id == user_id,
            UserAccessGrant.starts_at <= reference,
            UserAccessGrant.revoked_at.is_(None),
            or_(UserAccessGrant.ends_at.is_(None), UserAccessGrant.ends_at > reference),
        )
        .order_by(UserAccessGrant.starts_at.desc(), UserAccessGrant.created_at.desc())
    )
    return list(db.scalars(statement).all())


def resolve_access_snapshot(
    db: Session,
    user_id: UUID,
    *,
    now: datetime | None = None,
) -> AccessSnapshot:
    reference = _utc_now(now)
    grants = list_active_grants(db, user_id, now=reference)
    package_codes = {AccessPackageCode.FREE}
    for grant in grants:
        package_codes.add(AccessPackageCode(grant.package_code))

    ordered_packages = tuple(
        sorted(
            package_codes,
            key=lambda code: (-package_rank(code), code.value),
        )
    )
    granted_entitlements: set[EntitlementCode] = set()
    for code in package_codes:
        granted_entitlements.update(package_definition(code).entitlements)

    active_trial = next(
        (
            grant
            for grant in grants
            if AccessPackageCode(grant.package_code) is AccessPackageCode.LAUNCH_TRIAL
        ),
        None,
    )
    latest_trial = active_trial or db.scalar(
        select(UserAccessGrant)
        .where(
            UserAccessGrant.user_id == user_id,
            UserAccessGrant.package_code == AccessPackageCode.LAUNCH_TRIAL,
        )
        .order_by(UserAccessGrant.starts_at.desc())
        .limit(1)
    )
    trial = TrialState(
        active=active_trial is not None,
        ends_at=latest_trial.ends_at if latest_trial is not None else None,
    )
    return AccessSnapshot(
        primary_package=ordered_packages[0],
        active_packages=ordered_packages,
        granted_entitlements=frozenset(granted_entitlements),
        grants=tuple(grants),
        trial=trial,
    )


def has_entitlement(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    now: datetime | None = None,
) -> bool:
    return resolve_access_snapshot(db, user_id, now=now).has(entitlement)


def require_entitlement(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    now: datetime | None = None,
) -> AccessSnapshot:
    snapshot = resolve_access_snapshot(db, user_id, now=now)
    if not snapshot.has(entitlement):
        raise EntitlementRequiredError(
            entitlement,
            eligible_packages=eligible_upgrade_packages(entitlement),
        )
    return snapshot


def _quota_policy(entitlement: EntitlementCode | str) -> tuple[EntitlementCode, QuotaPolicy | None]:
    code = EntitlementCode(entitlement)
    return code, QUOTA_POLICIES.get(code)


def quota_status(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    now: datetime | None = None,
) -> QuotaStatus | None:
    reference = _utc_now(now)
    code, policy = _quota_policy(entitlement)
    if policy is None:
        return None

    window_start = reference - timedelta(days=policy.window_days)
    base_filter = (
        EntitlementUsageEvent.user_id == user_id,
        EntitlementUsageEvent.entitlement_key == code.value,
        EntitlementUsageEvent.occurred_at >= window_start,
        EntitlementUsageEvent.occurred_at <= reference,
    )
    used = (
        db.scalar(select(func.count()).select_from(EntitlementUsageEvent).where(*base_filter)) or 0
    )
    first_event = db.scalar(
        select(EntitlementUsageEvent.occurred_at)
        .where(*base_filter)
        .order_by(asc(EntitlementUsageEvent.occurred_at))
        .limit(1)
    )
    reset_at = (
        _utc_now(first_event) + timedelta(days=policy.window_days)
        if first_event is not None
        else reference + timedelta(days=policy.window_days)
    )
    return QuotaStatus(
        entitlement=code,
        limit=policy.limit,
        used=int(used),
        remaining=max(0, policy.limit - int(used)),
        window_days=policy.window_days,
        reset_at=reset_at,
    )


def require_quota_available(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    now: datetime | None = None,
) -> QuotaStatus | None:
    reference = _utc_now(now)
    require_entitlement(db, user_id, entitlement, now=reference)
    status = quota_status(db, user_id, entitlement, now=reference)
    if status is not None and status.remaining <= 0:
        raise EntitlementQuotaExceededError(
            status.entitlement,
            status.reset_at,
            now=reference,
        )
    return status


def consume_quota(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    resource_key: str,
    *,
    occurred_at: datetime | None = None,
    now: datetime | None = None,
) -> bool:
    reference = _utc_now(now or occurred_at)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ValueError(f"User not found: {user_id}")

    code, policy = _quota_policy(entitlement)
    if policy is None:
        return False

    existing = db.scalar(
        select(EntitlementUsageEvent).where(
            EntitlementUsageEvent.user_id == user_id,
            EntitlementUsageEvent.entitlement_key == code.value,
            EntitlementUsageEvent.resource_key == resource_key,
        )
    )
    if existing is not None:
        return False

    require_entitlement(db, user_id, code, now=reference)
    status = quota_status(db, user_id, code, now=reference)
    assert status is not None
    if status.remaining <= 0:
        raise EntitlementQuotaExceededError(status.entitlement, status.reset_at, now=reference)

    db.add(
        EntitlementUsageEvent(
            user_id=user_id,
            entitlement_key=code.value,
            resource_key=resource_key,
            occurred_at=reference,
        )
    )
    db.flush()
    return True


def grant_package(
    db: Session,
    user_id: UUID,
    package_code: AccessPackageCode | str,
    *,
    source: GrantSource | str = GrantSource.MANUAL,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    revoked_at: datetime | None = None,
    idempotency_key: str | None = None,
    term_weeks: int | None = None,
) -> UserAccessGrant:
    code = AccessPackageCode(package_code)
    grant_source = GrantSource(source)
    package_definition(code)
    if code is AccessPackageCode.LAUNCH_TRIAL and term_weeks is None:
        term_weeks = 4
    if term_weeks is not None and term_weeks not in VALID_ACCESS_TERM_WEEKS:
        raise ValueError("term_weeks must be one of 4, 6, or 8")
    reference = _utc_now(starts_at)
    lock = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if lock is None:
        raise ValueError(f"User not found: {user_id}")

    if idempotency_key is not None:
        existing = db.scalar(
            select(UserAccessGrant).where(
                UserAccessGrant.user_id == user_id,
                UserAccessGrant.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing

    grant = UserAccessGrant(
        user_id=user_id,
        package_code=code,
        source=grant_source,
        term_weeks=term_weeks,
        starts_at=reference,
        ends_at=_optional_utc(ends_at),
        revoked_at=_optional_utc(revoked_at),
        idempotency_key=idempotency_key,
    )
    db.add(grant)
    db.flush()
    return grant


def max_active_term_weeks_for_entitlement(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    now: datetime | None = None,
) -> int | None:
    code = EntitlementCode(entitlement)
    snapshot = resolve_access_snapshot(db, user_id, now=now)
    terms = [
        grant.term_weeks
        for grant in snapshot.grants
        if grant.term_weeks in VALID_ACCESS_TERM_WEEKS
        and code in package_definition(AccessPackageCode(grant.package_code)).entitlements
    ]
    return max(terms) if terms else None


def ensure_requested_term_weeks(
    db: Session,
    user_id: UUID,
    entitlement: EntitlementCode | str,
    *,
    requested_weeks: int,
    now: datetime | None = None,
) -> None:
    if requested_weeks not in VALID_ACCESS_TERM_WEEKS:
        raise ValueError("requested_weeks must be one of 4, 6, or 8")
    require_entitlement(db, user_id, entitlement, now=now)
    maximum_weeks = max_active_term_weeks_for_entitlement(
        db,
        user_id,
        entitlement,
        now=now,
    )
    if maximum_weeks is not None and requested_weeks > maximum_weeks:
        raise AccessTermTooShortError(requested_weeks, maximum_weeks)
