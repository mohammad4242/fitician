from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.access_management.enums import AccessCampaignKind
from app.access_management.models import AccessCampaign, AccessCampaignRedemption
from app.auth.models import User
from app.auth.security import normalize_iranian_phone
from app.profile.models import UserProfile


def get_campaign(
    db: Session,
    campaign_id: UUID,
    *,
    lock: bool = False,
) -> AccessCampaign | None:
    statement = select(AccessCampaign).where(AccessCampaign.id == campaign_id)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)

def get_campaign_by_code(db: Session, code: str) -> AccessCampaign | None:
    return db.scalar(select(AccessCampaign).where(AccessCampaign.code == code))


def list_campaigns(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[AccessCampaign]:
    statement = (
        select(AccessCampaign)
        .order_by(AccessCampaign.created_at.desc(), AccessCampaign.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


def list_active_signup_campaigns(db: Session) -> list[AccessCampaign]:
    statement = (
        select(AccessCampaign)
        .where(
            AccessCampaign.kind == AccessCampaignKind.SIGNUP_TRIAL,
            AccessCampaign.is_active.is_(True),
        )
        .order_by(AccessCampaign.available_from.asc().nulls_first(), AccessCampaign.id)
    )
    return list(db.scalars(statement).all())


def count_redemptions(db: Session, campaign_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AccessCampaignRedemption)
            .where(AccessCampaignRedemption.campaign_id == campaign_id)
        )
        or 0
    )


def get_redemption(
    db: Session,
    campaign_id: UUID,
    user_id: UUID,
    *,
    lock: bool = False,
) -> AccessCampaignRedemption | None:
    statement = select(AccessCampaignRedemption).where(
        AccessCampaignRedemption.campaign_id == campaign_id,
        AccessCampaignRedemption.user_id == user_id,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def search_users(
    db: Session,
    query: str | None,
    *,
    limit: int = 25,
    offset: int = 0,
) -> list[User]:
    statement = (
        select(User)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(limit)
        .offset(offset)
    )
    normalized_query = query.strip() if query is not None else ""
    if normalized_query:
        filters: list[ColumnElement[bool]] = [
            User.email.ilike(f"%{normalized_query}%"),
            User.phone_number.ilike(f"%{normalized_query}%"),
            UserProfile.display_name.ilike(f"%{normalized_query}%"),
        ]
        try:
            filters.append(User.phone_number == normalize_iranian_phone(normalized_query))
        except ValueError:
            pass
        try:
            filters.append(User.id == UUID(normalized_query))
        except ValueError:
            pass
        statement = statement.where(or_(*filters)).distinct()
    return list(db.scalars(statement).all())
