from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.workout_cycles.enums import WorkoutCycleSessionStatus


class WorkoutTimelineState(StrEnum):
    NO_PLAN = "no_plan"
    READY_TO_START = "ready_to_start"
    SCHEDULED_START = "scheduled_start"
    WORKOUT_TODAY = "workout_today"
    REST_DAY = "rest_day"
    OVERDUE = "overdue"
    COMPLETED_TODAY = "completed_today"
    LEGACY_CYCLE = "legacy_cycle"
    CYCLE_COMPLETED = "cycle_completed"


class NutritionTimelineState(StrEnum):
    NO_PLAN = "no_plan"
    PENDING_REVIEW = "pending_review"
    READY_TO_START = "ready_to_start"
    SCHEDULED_START = "scheduled_start"
    ACTIVE = "active"


class TimelineWorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workout_day_id: UUID
    week_number: int
    session_number: int
    scheduled_date: date
    status: WorkoutCycleSessionStatus
    day_number: int
    title_fa: str
    title_en: str
    estimated_duration_minutes: int


class TimelineWorkoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: WorkoutTimelineState
    workout_plan_id: UUID | None = None
    cycle_id: UUID | None = None
    start_date: date | None = None
    current_week: int | None = None
    duration_weeks: int | None = None
    completed_sessions: int = 0
    total_sessions: int = 0
    today_session: TimelineWorkoutSessionResponse | None = None
    overdue_session: TimelineWorkoutSessionResponse | None = None
    next_session: TimelineWorkoutSessionResponse | None = None


class TimelineNutritionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: NutritionTimelineState
    plan_id: UUID | None = None
    start_date: date | None = None
    absolute_day_number: int | None = None
    pattern_day_index: int | None = None
    day_id: UUID | None = None
    nutrient_totals: dict[str, float] = Field(default_factory=dict)
    effective_today: "TimelineNutritionEffectiveDayResponse | None" = None


class TimelineNutritionEffectiveDayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    start_date: date
    absolute_day_number: int
    pattern_day_index: int
    day_id: UUID | None = None
    nutrient_totals: dict[str, float] = Field(default_factory=dict)


class ProgramTimelineTodayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    timezone: str
    workout: TimelineWorkoutResponse
    nutrition: TimelineNutritionResponse
