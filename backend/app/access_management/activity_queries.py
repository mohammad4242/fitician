"""Bounded SQL history. Persisted domain records remain the historical source of truth."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String, case, cast, exists, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement, Select, Subquery

from app.auth.models import AuthSession, MobileAuthEvent, MobileTokenFamily, User
from app.billing.models import BillingOrder
from app.body_analysis.models import BodyAnalysis
from app.body_photos.models import BodyPhotoSession
from app.nutrition.models import NutritionDailyCheckIn, NutritionWeeklyPlan
from app.profile.models import BodyMeasurement
from app.support.models import SupportTicket
from app.user_activity.models import UserActivityEvent as Event
from app.workout_cycles.models import WorkoutCycle, WorkoutCycleSession, WorkoutCycleWeeklyCheckIn
from app.workouts.models import WorkoutPlan


def history_query(user_id: UUID | None = None) -> Subquery:
    """SQL UNION with ownership predicates pushed into every source and resource deduplication."""
    statements: list[Select[Any]] = []
    explicit = select(
        cast(Event.id, String).label("id"),
        Event.user_id.label("user_id"),
        Event.event_type.label("event_type"),
        Event.resource_type.label("resource_type"),
        Event.resource_id.label("resource_id"),
        Event.safe_metadata.label("metadata"),
        Event.occurred_at.label("occurred_at"),
        literal("explicit").label("source"),
    )
    if user_id is not None:
        explicit = explicit.where(Event.user_id == user_id)
    statements.append(explicit)

    def source(
        owner: ColumnElement[Any] | InstrumentedAttribute[Any],
        key: ColumnElement[Any] | InstrumentedAttribute[Any],
        time: ColumnElement[Any] | InstrumentedAttribute[Any],
        event_type: str,
        resource_type: str,
        *,
        metadata: ColumnElement[Any] | None = None,
        conditions: tuple[ColumnElement[bool], ...] = (),
    ) -> Select[Any]:
        resource_id = cast(key, String)
        statement = select(
            (literal(resource_type + ":" + event_type + ":") + resource_id).label("id"),
            owner.label("user_id"),
            literal(event_type).label("event_type"),
            literal(resource_type).label("resource_type"),
            resource_id.label("resource_id"),
            (metadata if metadata is not None else cast(literal("{}"), JSON)).label("metadata"),
            time.label("occurred_at"),
            literal("historical").label("source"),
        ).where(
            time.is_not(None),
            *conditions,
            ~exists(
                select(Event.id).where(
                    Event.user_id == owner,
                    Event.event_type == event_type,
                    Event.resource_type == resource_type,
                    Event.resource_id == resource_id,
                )
            ),
        )
        if user_id is not None:
            statement = statement.where(owner == user_id)
        return statement

    registration = source(User.id, User.id, User.created_at, "auth.registered", "user").where(
        ~exists(
            select(Event.id).where(Event.user_id == User.id, Event.event_type == "auth.registered")
        )
    )
    statements.extend(
        [
            registration,
            source(
                WorkoutPlan.user_id,
                WorkoutPlan.id,
                WorkoutPlan.created_at,
                "workout.plan_generated",
                "workout_plan",
                metadata=func.json_build_object("primary_goal", WorkoutPlan.primary_goal),
                conditions=(
                    WorkoutPlan.deleted_at.is_(None),
                    WorkoutPlan.status.in_(["active", "pending_review", "superseded"]),
                ),
            ),
            source(
                WorkoutCycle.user_id,
                WorkoutCycle.id,
                WorkoutCycle.started_at,
                "workout.plan_started",
                "workout_cycle",
            ),
            source(
                WorkoutCycle.user_id,
                WorkoutCycleSession.id,
                WorkoutCycleSession.completed_at,
                "workout.session_completed",
                "workout_session",
                metadata=func.json_build_object(
                    "week_number",
                    WorkoutCycleSession.week_number,
                    "session_number",
                    WorkoutCycleSession.session_number,
                ),
            ).join(WorkoutCycle, WorkoutCycle.id == WorkoutCycleSession.cycle_id),
            source(
                WorkoutCycle.user_id,
                WorkoutCycleSession.id,
                WorkoutCycleSession.skipped_at,
                "workout.session_skipped",
                "workout_session",
                metadata=func.json_build_object(
                    "week_number",
                    WorkoutCycleSession.week_number,
                    "session_number",
                    WorkoutCycleSession.session_number,
                ),
            ).join(WorkoutCycle, WorkoutCycle.id == WorkoutCycleSession.cycle_id),
            source(
                WorkoutCycleWeeklyCheckIn.user_id,
                WorkoutCycleWeeklyCheckIn.id,
                WorkoutCycleWeeklyCheckIn.created_at,
                "workout.weekly_checkin",
                "workout_weekly_checkin",
                metadata=func.json_build_object(
                    "week_number", WorkoutCycleWeeklyCheckIn.week_number
                ),
            ),
            source(
                NutritionWeeklyPlan.user_id,
                NutritionWeeklyPlan.id,
                NutritionWeeklyPlan.created_at,
                "nutrition.plan_generated",
                "nutrition_plan",
                metadata=func.json_build_object("revision", NutritionWeeklyPlan.revision),
            ),
            source(
                NutritionWeeklyPlan.user_id,
                NutritionWeeklyPlan.id,
                NutritionWeeklyPlan.started_at,
                "nutrition.plan_started",
                "nutrition_plan",
            ),
            source(
                NutritionDailyCheckIn.user_id,
                NutritionDailyCheckIn.id,
                NutritionDailyCheckIn.updated_at,
                "nutrition.daily_checkin",
                "nutrition_checkin",
            ),
            source(
                BodyMeasurement.user_id,
                BodyMeasurement.id,
                BodyMeasurement.measured_at,
                "body.measurement_recorded",
                "body_measurement",
                metadata=func.json_build_object(
                    "weight_kg",
                    case(
                        (
                            or_(
                                BodyMeasurement.observed_fields.is_(None),
                                cast(BodyMeasurement.observed_fields, JSONB).contains(
                                    ["weight_kg"]
                                ),
                            ),
                            BodyMeasurement.weight_kg,
                        ),
                        else_=None,
                    ),
                ),
            ),
            source(
                BodyPhotoSession.user_id,
                BodyAnalysis.id,
                BodyAnalysis.completed_at,
                "body_analysis.completed",
                "body_analysis",
                conditions=(BodyAnalysis.status.in_(["completed", "review_pending"]),),
            ).join(BodyPhotoSession, BodyPhotoSession.id == BodyAnalysis.session_id),
            source(
                BillingOrder.user_id,
                BillingOrder.id,
                BillingOrder.paid_at,
                "billing.order_paid",
                "billing_order",
            ),
            source(
                SupportTicket.user_id,
                SupportTicket.id,
                SupportTicket.created_at,
                "support.ticket_created",
                "support_ticket",
            ),
        ]
    )
    web_known = exists(
        select(Event.id).where(
            Event.user_id == AuthSession.user_id,
            Event.event_type.in_(["auth.registered", "auth.login_succeeded"]),
            Event.resource_type == "auth_session",
            Event.resource_id == cast(AuthSession.id, String),
        )
    )
    mobile_known = exists(
        select(Event.id).where(
            Event.user_id == MobileAuthEvent.user_id,
            Event.event_type.in_(["auth.registered", "auth.login_succeeded"]),
            Event.resource_type == "mobile_token_family",
            Event.resource_id == cast(MobileAuthEvent.family_id, String),
        )
    )
    statements.extend(
        [
            source(
                AuthSession.user_id,
                AuthSession.id,
                AuthSession.created_at,
                "auth.legacy_session_created",
                "auth_session",
                metadata=func.json_build_object("platform", "web"),
                conditions=(~web_known,),
            ),
            source(
                MobileAuthEvent.user_id,
                MobileAuthEvent.id,
                MobileAuthEvent.created_at,
                "auth.legacy_token_issued",
                "mobile_auth_event",
                metadata=func.json_build_object("platform", MobileTokenFamily.platform),
                conditions=(
                    MobileAuthEvent.event_type == "token_issued",
                    ~mobile_known,
                ),
            ).outerjoin(MobileTokenFamily, MobileTokenFamily.id == MobileAuthEvent.family_id),
        ]
    )
    return union_all(*statements).subquery("user_history")


def login_query(user_id: UUID) -> Subquery:
    explicit = select(
        cast(Event.id, String).label("id"),
        Event.occurred_at.label("occurred_at"),
        Event.safe_metadata["platform"].as_string().label("platform"),
        Event.safe_metadata["auth_method"].as_string().label("auth_method"),
        Event.safe_metadata["app_version"].as_string().label("app_version"),
        Event.safe_metadata["device_name"].as_string().label("device_name"),
        literal("explicit_login").label("evidence"),
    ).where(Event.user_id == user_id, Event.event_type == "auth.login_succeeded")
    web = select(
        (literal("web:") + cast(AuthSession.id, String)).label("id"),
        AuthSession.created_at.label("occurred_at"),
        literal("web").label("platform"),
        cast(literal(None), String).label("auth_method"),
        cast(literal(None), String).label("app_version"),
        cast(literal(None), String).label("device_name"),
        literal("legacy_web_session").label("evidence"),
    ).where(
        AuthSession.user_id == user_id,
        ~exists(
            select(Event.id).where(
                Event.user_id == user_id,
                Event.event_type.in_(["auth.registered", "auth.login_succeeded"]),
                Event.resource_type == "auth_session",
                Event.resource_id == cast(AuthSession.id, String),
            )
        ),
    )
    mobile = (
        select(
            (literal("mobile:") + cast(MobileAuthEvent.id, String)).label("id"),
            MobileAuthEvent.created_at.label("occurred_at"),
            MobileTokenFamily.platform.label("platform"),
            cast(literal(None), String).label("auth_method"),
            MobileTokenFamily.app_version.label("app_version"),
            MobileTokenFamily.device_name.label("device_name"),
            literal("legacy_mobile_token_issued").label("evidence"),
        )
        .outerjoin(MobileTokenFamily, MobileTokenFamily.id == MobileAuthEvent.family_id)
        .where(
            MobileAuthEvent.user_id == user_id,
            MobileAuthEvent.event_type == "token_issued",
            ~exists(
                select(Event.id).where(
                    Event.user_id == user_id,
                    Event.event_type.in_(["auth.registered", "auth.login_succeeded"]),
                    Event.resource_type == "mobile_token_family",
                    Event.resource_id == cast(MobileAuthEvent.family_id, String),
                )
            ),
        )
    )
    return union_all(explicit, web, mobile).subquery("login_history")
