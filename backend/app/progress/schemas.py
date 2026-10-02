from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Preset = Literal["week", "four_weeks", "current_program"]


class ProgressContext(BaseModel):
    preset: Preset
    timezone: str
    today: date
    start_date: date
    end_date: date
    range_clipped: bool = False
    goal: str | None = None
    product_mode: str | None = None
    training_enabled: bool
    nutrition_enabled: bool
    current_cycle_id: UUID | None = None
    current_program_id: UUID | None = None
    week_number: int | None = None


class TrainingWeek(BaseModel):
    start_date: date
    planned: int
    completed: int


class ProgressTraining(BaseModel):
    planned_sessions: int
    due_sessions: int
    completed_sessions: int
    skipped_sessions: int
    overdue_sessions: int
    rescheduled_sessions: int | None = None
    adherence_percent: float | None
    denominator: Literal["elapsed_scheduled_dates_plus_resolved_today"] = (
        "elapsed_scheduled_dates_plus_resolved_today"
    )
    weeks: list[TrainingWeek]
    self_reported_cycle_progress: str | None = None


class RecoveryPoint(BaseModel):
    recorded_at: datetime
    week_number: int
    recovery: Literal["good", "average", "poor"]
    difficulty: Literal["too_easy", "easy", "appropriate", "hard", "too_hard"]


class BodyPoint(BaseModel):
    recorded_at: datetime
    value: float
    source: Literal["manual", "legacy_changed_value"]


class BodySeries(BaseModel):
    unit: Literal["kg", "cm"]
    points: list[BodyPoint] = Field(default_factory=list)
    start_value: float | None = None
    latest_value: float | None = None
    delta: float | None = None
    legacy_coverage: Literal["changed_values_only"] = "changed_values_only"


class ProgressBodyMeasurements(BaseModel):
    weight: BodySeries = Field(default_factory=lambda: BodySeries(unit="kg"))
    waist: BodySeries = Field(default_factory=lambda: BodySeries(unit="cm"))
    hip: BodySeries = Field(default_factory=lambda: BodySeries(unit="cm"))
    shoulder_width: BodySeries = Field(default_factory=lambda: BodySeries(unit="cm"))


class CaloriePoint(BaseModel):
    date: date
    target_kcal: float | None
    actual_kcal: float | None
    target_plan_id: UUID | None = None
    target_revision: int | None = None
    target_source: Literal["lifecycle_history", "recorded_plan_reference"] | None = None
    logging_state: Literal["missing", "recorded", "invalid"]
    reliable: bool = False
    in_progress: bool
    near_target: bool | None = None


class ProgressNutrition(BaseModel):
    series: list[CaloriePoint]
    days_in_range: int
    elapsed_days: int
    logged_days: int
    reliable_logged_days: int
    comparable_days: int
    adherent_days: int
    adherence_percent: float | None
    average_target_kcal: float | None
    average_actual_kcal: float | None
    average_difference_kcal: float | None
    rule: Literal["confirmed_high_confidence_completed_days_80_to_120_percent"] = (
        "confirmed_high_confidence_completed_days_80_to_120_percent"
    )
    complete_day_intake_verified: Literal[False] = False


class AnalysisSummary(BaseModel):
    latest_session_id: UUID | None = None
    latest_analysis_id: UUID | None = None
    latest_status: str | None = None
    latest_at: datetime | None = None


class ProgressInsight(BaseModel):
    code: str
    values: dict[str, float | int | str]


class ProgressOverview(BaseModel):
    context: ProgressContext
    training: ProgressTraining | None = None
    nutrition: ProgressNutrition | None = None
    body_measurements: ProgressBodyMeasurements = Field(default_factory=ProgressBodyMeasurements)
    body_analysis: AnalysisSummary = Field(default_factory=AnalysisSummary)
    recovery: list[RecoveryPoint] = Field(default_factory=list)
    insights: list[ProgressInsight] = Field(default_factory=list)
