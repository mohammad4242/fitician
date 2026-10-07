"""Business visibility projections: no clinical payloads or private media."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.access_management.schemas import AdminMemberSummaryResponse


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class MemberSummary(AdminMemberSummaryResponse):
    last_activity_at: datetime | None
    usage_status: Literal["no_recorded_activity", "active", "inactive"]


class SignupPoint(BaseModel):
    date: date
    count: int


class AccessOverview(BaseModel):
    timezone: str = "Asia/Tehran"
    generated_at: datetime
    today_start: datetime
    week_start: datetime
    month_start: datetime
    total_users: int
    registrations_today: int
    registrations_week: int
    registrations_month: int
    active_users_24h: int
    active_users_7d: int
    active_users_30d: int
    active_paid_users: int
    purchases_today: int
    purchases_week: int
    purchases_month: int
    workout_plans: int
    nutrition_plans: int
    body_analyses_completed: int
    daily_signups: list[SignupPoint]
    recent_users: list[MemberSummary]


class UserInsights(BaseModel):
    last_activity_at: datetime | None
    login_count: int
    legacy_login_evidence_count: int
    workout_plans: int
    nutrition_plans: int
    completed_workout_sessions: int
    skipped_workout_sessions: int
    weekly_checkins: int
    body_analyses: int
    body_analyses_completed: int
    latest_weight_kg: float | None


class ActivityItem(BaseModel):
    id: str
    event_type: str
    resource_type: str | None
    resource_id: str | None
    metadata: dict[str, str | int | float | bool | None]
    occurred_at: datetime
    source: Literal["explicit", "historical"]


class LoginItem(BaseModel):
    id: str
    occurred_at: datetime
    platform: str | None
    auth_method: str | None
    app_version: str | None
    device_name: str | None
    evidence: Literal["explicit_login", "legacy_web_session", "legacy_mobile_token_issued"]


class WorkoutHistoryItem(BaseModel):
    id: UUID
    created_at: datetime
    activated_at: datetime | None
    status: str
    primary_goal: str
    secondary_goal: str | None
    duration_weeks: int
    training_days: int
    review_status: str


class SafeExercise(BaseModel):
    name_en: str
    name_fa: str
    sets: int
    reps_min: int | None
    reps_max: int | None
    duration_min_seconds: int | None
    duration_max_seconds: int | None
    rest_seconds: int


class SafeWorkoutDay(BaseModel):
    day_number: int
    title_en: str
    title_fa: str
    estimated_duration_minutes: int
    exercises: list[SafeExercise]


class WorkoutDetail(WorkoutHistoryItem):
    days: list[SafeWorkoutDay]


class NutritionHistoryItem(BaseModel):
    id: UUID
    revision: int
    lifecycle_status: str
    review_status: str
    created_at: datetime
    start_date: date
    started_at: datetime | None
    budget_status: str
    selected: bool
    is_user_visible: bool
    plan_role: str


class SafeFood(BaseModel):
    name_fa: str
    name_en: str
    grams: float


class SafeMeal(BaseModel):
    slot: str
    foods: list[SafeFood]


class SafeNutritionDay(BaseModel):
    day_index: int
    plan_date: date
    meals: list[SafeMeal]


class NutritionDetail(NutritionHistoryItem):
    days: list[SafeNutritionDay]


class ProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    measured_at: datetime
    weight_kg: float | None
    waist_circumference_cm: float | None
    hip_circumference_cm: float | None
    shoulder_circumference_cm: float | None
    shoulder_width_cm: float | None
    observed_fields: list[str] | None


class AnalysisItem(BaseModel):
    id: UUID
    created_at: datetime
    completed_at: datetime | None
    status: str
    revision: int
