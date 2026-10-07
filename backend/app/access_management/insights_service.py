"""Admin business analytics over canonical domain records. No clinical read authorization."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.access_management.activity_queries import history_query, login_query
from app.access_management.insights_schemas import (
    AccessOverview,
    ActivityItem,
    AnalysisItem,
    LoginItem,
    MemberSummary,
    Page,
    ProgressItem,
    SignupPoint,
    UserInsights,
)
from app.access_management.repository import search_users_statement
from app.access_management.service import user_or_raise
from app.auth.models import User
from app.billing.models import BillingOrder
from app.body_analysis.models import BodyAnalysis
from app.body_photos.models import BodyPhotoSession
from app.entitlements.enums import AccessPackageCode, GrantSource
from app.entitlements.models import UserAccessGrant
from app.entitlements.service import access_snapshot_from_grants
from app.nutrition.models import NutritionWeeklyPlan
from app.profile.models import BodyMeasurement, UserProfile
from app.user_activity.models import UserActivityEvent
from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession, WorkoutCycleWeeklyCheckIn
from app.workouts.models import WorkoutPlan

TEHRAN = ZoneInfo("Asia/Tehran")
SignupPeriod = Literal["all", "today", "week", "month", "custom"]
UserSort = Literal["newest", "oldest", "last_activity"]


def local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, TEHRAN).astimezone(UTC)


def period_boundaries(now: datetime) -> tuple[datetime, datetime, datetime]:
    today = now.astimezone(TEHRAN).date()
    return (
        local_midnight(today),
        local_midnight(today - timedelta(days=(today.weekday() + 2) % 7)),
        local_midnight(today.replace(day=1)),
    )


def member_summaries(db: Session, users: list[User], now: datetime) -> list[MemberSummary]:
    """Four batched queries, independent of page size. Reuse canonical entitlement policy."""
    if not users:
        return []
    ids = [user.id for user in users]
    names = dict(
        db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(
                UserProfile.user_id.in_(ids)
            )
        )
        .tuples()
        .all()
    )
    grants: dict[UUID, list[UserAccessGrant]] = defaultdict(list)
    latest_trials = {
        grant.user_id: grant
        for grant in db.scalars(
            select(UserAccessGrant)
            .where(
                UserAccessGrant.user_id.in_(ids),
                UserAccessGrant.package_code == AccessPackageCode.LAUNCH_TRIAL,
            )
            .distinct(UserAccessGrant.user_id)
            .order_by(
                UserAccessGrant.user_id, UserAccessGrant.starts_at.desc(), UserAccessGrant.id.desc()
            )
        )
    }
    for grant in db.scalars(
        select(UserAccessGrant)
        .where(
            UserAccessGrant.user_id.in_(ids),
            UserAccessGrant.starts_at <= now,
            UserAccessGrant.revoked_at.is_(None),
            or_(UserAccessGrant.ends_at.is_(None), UserAccessGrant.ends_at > now),
        )
        .order_by(UserAccessGrant.starts_at.desc(), UserAccessGrant.created_at.desc())
    ):
        grants[grant.user_id].append(grant)
    # Push the page ownership predicate into every history source.
    history = history_query()
    last_activity = dict(
        db.execute(
            select(history.c.user_id, func.max(history.c.occurred_at))
            .where(history.c.user_id.in_(ids))
            .group_by(history.c.user_id)
        )
        .tuples()
        .all()
    )
    result = []
    for user in users:
        active = grants[user.id]
        snapshot = access_snapshot_from_grants(active, latest_trial=latest_trials.get(user.id))
        latest = last_activity.get(user.id)
        result.append(
            MemberSummary(
                user_id=user.id,
                display_name=names.get(user.id),
                email=user.email,
                phone_number=user.phone_number,
                created_at=user.created_at,
                primary_package=snapshot.primary_package,
                active_packages=list(snapshot.active_packages),
                trial_active=snapshot.trial.active,
                trial_ends_at=snapshot.trial.ends_at,
                paid_access_end=max(
                    (
                        grant.ends_at
                        for grant in active
                        if grant.source == GrantSource.SUBSCRIPTION and grant.ends_at is not None
                    ),
                    default=None,
                ),
                last_activity_at=latest,
                usage_status=(
                    "no_recorded_activity"
                    if latest is None
                    else "active"
                    if latest >= now - timedelta(days=7)
                    else "inactive"
                ),
            )
        )
    return result


def users_page(
    db: Session,
    *,
    q: str | None,
    limit: int,
    offset: int,
    signup_period: SignupPeriod,
    from_date: date | None,
    to_date: date | None,
    sort: UserSort,
    now: datetime | None = None,
) -> Page[MemberSummary]:
    reference = now or datetime.now(UTC)
    statement = search_users_statement(q)
    if signup_period == "custom":
        if from_date is None or to_date is None or from_date > to_date:
            raise HTTPException(422, detail={"code": "INVALID_SIGNUP_RANGE"})
        statement = statement.where(
            User.created_at >= local_midnight(from_date),
            User.created_at < local_midnight(to_date + timedelta(days=1)),
        )
    elif signup_period != "all":
        today, week, month = period_boundaries(reference)
        start = {"today": today, "week": week, "month": month}[signup_period]
        statement = statement.where(User.created_at >= start, User.created_at <= reference)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    if sort == "last_activity":
        history = history_query()
        last = (
            select(history.c.user_id, func.max(history.c.occurred_at).label("last_activity"))
            .group_by(history.c.user_id)
            .subquery()
        )
        statement = statement.outerjoin(last, last.c.user_id == User.id).order_by(
            last.c.last_activity.desc().nulls_last(), User.id.desc()
        )
    elif sort == "oldest":
        statement = statement.order_by(User.created_at.asc(), User.id.asc())
    else:
        statement = statement.order_by(User.created_at.desc(), User.id.desc())
    users = list(db.scalars(statement.limit(limit).offset(offset)))
    return Page(
        items=member_summaries(db, users, reference), total=total, limit=limit, offset=offset
    )


def overview(db: Session, *, now: datetime | None = None) -> AccessOverview:
    reference = now or datetime.now(UTC)
    today, week, month = period_boundaries(reference)
    counts = db.execute(
        select(
            func.count(User.id),
            *[
                func.count(User.id).filter(User.created_at >= start, User.created_at <= reference)
                for start in (today, week, month)
            ],
        )
    ).one()
    history = history_query()
    activity = db.execute(
        select(
            *[
                func.count(func.distinct(history.c.user_id)).filter(
                    history.c.occurred_at >= reference - timedelta(days=days),
                    history.c.occurred_at <= reference,
                )
                for days in (1, 7, 30)
            ]
        ).where(
            history.c.occurred_at >= reference - timedelta(days=30),
            history.c.occurred_at <= reference,
        )
    ).one()
    paid = int(
        db.scalar(
            select(func.count(func.distinct(UserAccessGrant.user_id))).where(
                UserAccessGrant.source == GrantSource.SUBSCRIPTION,
                UserAccessGrant.revoked_at.is_(None),
                UserAccessGrant.starts_at <= reference,
                or_(UserAccessGrant.ends_at.is_(None), UserAccessGrant.ends_at > reference),
            )
        )
        or 0
    )
    purchases = db.execute(
        select(
            *[
                func.count(BillingOrder.id).filter(
                    BillingOrder.paid_at >= start, BillingOrder.paid_at <= reference
                )
                for start in (today, week, month)
            ]
        )
    ).one()
    date_expr = func.date(func.timezone("Asia/Tehran", User.created_at))
    local_today = reference.astimezone(TEHRAN).date()
    dates = [local_today - timedelta(days=29 - day) for day in range(30)]
    daily = dict(
        db.execute(
            select(date_expr, func.count())
            .where(
                User.created_at >= local_midnight(dates[0]),
                User.created_at <= reference,
            )
            .group_by(date_expr)
        )
        .tuples()
        .all()
    )
    recent = list(
        db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(10))
    )
    return AccessOverview(
        generated_at=reference,
        today_start=today,
        week_start=week,
        month_start=month,
        total_users=counts[0],
        registrations_today=counts[1],
        registrations_week=counts[2],
        registrations_month=counts[3],
        active_users_24h=activity[0],
        active_users_7d=activity[1],
        active_users_30d=activity[2],
        active_paid_users=paid,
        purchases_today=purchases[0],
        purchases_week=purchases[1],
        purchases_month=purchases[2],
        workout_plans=int(
            db.scalar(
                select(func.count())
                .select_from(WorkoutPlan)
                .where(
                    WorkoutPlan.deleted_at.is_(None),
                    WorkoutPlan.status.in_(["active", "pending_review", "superseded"]),
                )
            )
            or 0
        ),
        nutrition_plans=int(db.scalar(select(func.count()).select_from(NutritionWeeklyPlan)) or 0),
        body_analyses_completed=int(
            db.scalar(
                select(func.count())
                .select_from(BodyAnalysis)
                .where(
                    BodyAnalysis.completed_at.is_not(None),
                    BodyAnalysis.status.in_(["completed", "review_pending"]),
                )
            )
            or 0
        ),
        daily_signups=[SignupPoint(date=day, count=daily.get(day, 0)) for day in dates],
        recent_users=member_summaries(db, recent, reference),
    )


def insights(db: Session, user_id: UUID) -> UserInsights:
    user_or_raise(db, user_id)
    history = history_query(user_id)
    logins = login_query(user_id)
    latest_weight = db.scalar(
        select(BodyMeasurement.weight_kg)
        .where(
            BodyMeasurement.user_id == user_id,
            or_(
                BodyMeasurement.observed_fields.is_(None),
                cast(BodyMeasurement.observed_fields, JSONB).contains(["weight_kg"]),
            ),
        )
        .order_by(BodyMeasurement.measured_at.desc(), BodyMeasurement.id.desc())
        .limit(1)
    )
    analysis_counts = db.execute(
        select(
            func.count(BodyAnalysis.id),
            func.count(BodyAnalysis.id).filter(
                BodyAnalysis.completed_at.is_not(None),
                BodyAnalysis.status.in_(["completed", "review_pending"]),
            ),
        )
        .join(BodyPhotoSession)
        .where(BodyPhotoSession.user_id == user_id)
    ).one()
    sessions = db.execute(
        select(
            func.count(WorkoutCycleSession.id).filter(WorkoutCycleSession.status == "completed"),
            func.count(WorkoutCycleSession.id).filter(WorkoutCycleSession.status == "skipped"),
        )
        .join(WorkoutCycle)
        .where(WorkoutCycle.user_id == user_id)
    ).one()
    return UserInsights(
        last_activity_at=db.scalar(select(func.max(history.c.occurred_at))),
        login_count=int(
            db.scalar(
                select(func.count())
                .select_from(UserActivityEvent)
                .where(
                    UserActivityEvent.user_id == user_id,
                    UserActivityEvent.event_type == "auth.login_succeeded",
                )
            )
            or 0
        ),
        legacy_login_evidence_count=int(
            db.scalar(
                select(func.count())
                .select_from(logins)
                .where(logins.c.evidence != "explicit_login")
            )
            or 0
        ),
        workout_plans=int(
            db.scalar(
                select(func.count())
                .select_from(WorkoutPlan)
                .where(
                    WorkoutPlan.user_id == user_id,
                    WorkoutPlan.deleted_at.is_(None),
                    WorkoutPlan.status.in_(["active", "pending_review", "superseded"]),
                )
            )
            or 0
        ),
        nutrition_plans=int(
            db.scalar(
                select(func.count())
                .select_from(NutritionWeeklyPlan)
                .where(NutritionWeeklyPlan.user_id == user_id)
            )
            or 0
        ),
        completed_workout_sessions=sessions[0],
        skipped_workout_sessions=sessions[1],
        weekly_checkins=int(
            db.scalar(
                select(func.count())
                .select_from(WorkoutCycleWeeklyCheckIn)
                .where(WorkoutCycleWeeklyCheckIn.user_id == user_id)
            )
            or 0
        ),
        body_analyses=analysis_counts[0],
        body_analyses_completed=analysis_counts[1],
        latest_weight_kg=float(latest_weight) if latest_weight is not None else None,
    )


def activity_page(
    db: Session, user_id: UUID, *, limit: int, offset: int, event_type: str | None = None
) -> Page[ActivityItem]:
    user_or_raise(db, user_id)
    history = history_query(user_id)
    statement = select(history)
    if event_type:
        statement = statement.where(history.c.event_type == event_type)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(
        statement.order_by(history.c.occurred_at.desc(), history.c.id.desc())
        .limit(limit)
        .offset(offset)
    ).mappings()
    return Page(
        items=[ActivityItem.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def logins_page(db: Session, user_id: UUID, *, limit: int, offset: int) -> Page[LoginItem]:
    user_or_raise(db, user_id)
    history = login_query(user_id)
    total = int(db.scalar(select(func.count()).select_from(history)) or 0)
    rows = db.execute(
        select(history)
        .order_by(history.c.occurred_at.desc(), history.c.id.desc())
        .limit(limit)
        .offset(offset)
    ).mappings()
    return Page(
        items=[LoginItem.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def progress_page(db: Session, user_id: UUID, *, limit: int, offset: int) -> Page[ProgressItem]:
    user_or_raise(db, user_id)
    statement = select(BodyMeasurement).where(BodyMeasurement.user_id == user_id)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(
        statement.order_by(BodyMeasurement.measured_at.desc(), BodyMeasurement.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    measurement_fields = (
        "weight_kg",
        "waist_circumference_cm",
        "hip_circumference_cm",
        "shoulder_circumference_cm",
        "shoulder_width_cm",
    )
    for row in rows:
        item = ProgressItem.model_validate(row)
        if row.observed_fields is not None:
            # Snapshot carry-forward values are not new observations.
            for field in measurement_fields:
                if field not in row.observed_fields:
                    setattr(item, field, None)
            item.observed_fields = [
                field for field in row.observed_fields if field in measurement_fields
            ]
        items.append(item)
    return Page(items=items, total=total, limit=limit, offset=offset)


def analyses_page(db: Session, user_id: UUID, *, limit: int, offset: int) -> Page[AnalysisItem]:
    user_or_raise(db, user_id)
    statement = (
        select(
            BodyAnalysis.id,
            BodyAnalysis.created_at,
            BodyAnalysis.completed_at,
            BodyAnalysis.status,
            BodyAnalysis.revision,
        )
        .join(BodyPhotoSession)
        .where(BodyPhotoSession.user_id == user_id)
    )
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.execute(
        statement.order_by(BodyAnalysis.created_at.desc(), BodyAnalysis.id.desc())
        .limit(limit)
        .offset(offset)
    ).mappings()
    return Page(
        items=[AnalysisItem.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
