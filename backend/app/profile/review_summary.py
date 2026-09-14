from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.nutrition.models import (
    NutritionCookingEquipment,
    NutritionFoodItem,
    NutritionMedicalCondition,
    NutritionMedicalProfile,
    NutritionMedication,
    NutritionProfile,
    NutritionSafetyDecision,
    NutritionStructuredExercise,
)
from app.profile.exceptions import ProfileInvariantError, ProfileNotFoundError
from app.profile.schemas import calculate_age
from app.profile.service import get_profile


class ReviewProfileFoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    name: str
    details: str | None


class ReviewProfileMedicalCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    details: str | None


class ReviewProfileMedication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    dosage: str | None
    notes: str | None


class ReviewProfileStructuredExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trains: bool
    exercise_type: str | None
    days_per_week: int | None
    minutes_per_session: int | None
    intensity: str | None
    source: str
    confirmed_at: datetime
    updated_at: datetime


class ReviewProfileNutrition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    onboarding_status: str
    daily_activity_level: str
    metabolic_basis: str | None
    individual_monthly_food_budget_irr: int
    budget_style: str
    meals_per_day: int
    snacks_per_day: int
    main_meal_count_bucket: str
    snack_count_bucket: str
    effective_main_meal_slots: int
    effective_snack_slots: int
    preferred_plan_start_day: str
    plan_style: str
    cooking_skill: str
    maximum_cooking_time_minutes: int
    cooking_frequency_per_week: int
    meal_preparation_preference: str
    refrigerator_access: bool
    freezer_access: bool
    supplied_meals_per_week: int
    supplied_meal_source: str | None
    dietary_pattern: str
    preferred_variety: str
    maximum_meal_repetition_per_week: int
    accepts_leftovers: bool
    accepts_batch_cooking: bool
    work_shift_context: str | None
    daily_check_in_enabled: bool
    preferred_check_in_time: time | None
    target_weight_change_kg_per_week: Decimal | None
    weight_rate_mode: str
    cooking_equipment: list[str]
    food_items: list[ReviewProfileFoodItem]
    structured_exercise: ReviewProfileStructuredExercise | None
    created_at: datetime
    updated_at: datetime


class ReviewProfileMedical(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flags: dict[str, bool]
    physician_dietary_restrictions: str | None
    other_relevant_condition: str | None
    conditions: list[ReviewProfileMedicalCondition]
    medications: list[ReviewProfileMedication]
    safety_outcome: str | None
    safety_reason_codes: list[str]
    medical_condition_policy_version: str | None
    safety_decision_created_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReviewProfileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    display_name: str | None
    birth_date: date | None
    age: int | None
    sex: str | None
    product_mode: str
    timezone: str
    height_cm: int | None
    weight_kg: Decimal | None
    weight_measured_at: datetime | None
    shoulder_circumference_cm: Decimal | None
    waist_circumference_cm: Decimal | None
    hip_circumference_cm: Decimal | None
    measurements_measured_at: datetime | None
    fitness_goal: str | None
    experience_level: str | None
    training_age_months: int | None
    preferred_weekdays: list[int] | None
    priority_muscles: list[str] | None
    training_days_per_week: int | None
    training_location: str | None
    home_training_setup: str | None
    available_equipment: list[str] | None
    session_duration_minutes: int | None
    training_intensity: str | None
    physical_limitations: str | None
    plan_duration_weeks: int | None
    workout_generation_method: str | None
    training_cautions: list[str]
    profile_created_at: datetime
    profile_updated_at: datetime
    nutrition: ReviewProfileNutrition | None
    medical: ReviewProfileMedical | None


def build_review_profile_summary(
    db: Session,
    user_id: UUID,
) -> ReviewProfileSummary | None:
    try:
        snapshot = get_profile(db, user_id)
    except (ProfileNotFoundError, ProfileInvariantError):
        return None

    profile = snapshot.profile
    measurement = snapshot.measurement
    nutrition_profile = db.get(NutritionProfile, user_id)
    nutrition = _nutrition_summary(db, nutrition_profile)
    medical = _medical_summary(db, user_id)

    return ReviewProfileSummary(
        user_id=user_id,
        display_name=profile.display_name,
        birth_date=profile.birth_date,
        age=(calculate_age(profile.birth_date, date.today()) if profile.birth_date else None),
        sex=_enum_value(profile.sex),
        product_mode=_enum_value(profile.product_mode),
        timezone=profile.timezone,
        height_cm=profile.height_cm,
        weight_kg=measurement.weight_kg,
        weight_measured_at=measurement.measured_at,
        shoulder_circumference_cm=measurement.shoulder_circumference_cm,
        waist_circumference_cm=measurement.waist_circumference_cm,
        hip_circumference_cm=measurement.hip_circumference_cm,
        measurements_measured_at=measurement.measured_at,
        fitness_goal=_enum_value(profile.fitness_goal),
        experience_level=_enum_value(profile.experience_level),
        training_age_months=profile.training_age_months,
        preferred_weekdays=profile.preferred_weekdays,
        priority_muscles=profile.priority_muscles,
        training_days_per_week=profile.training_days_per_week,
        training_location=_enum_value(profile.training_location),
        home_training_setup=_enum_value(profile.home_training_setup),
        available_equipment=profile.available_equipment,
        session_duration_minutes=profile.session_duration_minutes,
        training_intensity=_enum_value(profile.training_intensity),
        physical_limitations=profile.physical_limitations,
        plan_duration_weeks=profile.plan_duration_weeks,
        workout_generation_method=_enum_value(profile.workout_generation_method),
        training_cautions=sorted(
            (_enum_value(item.caution) for item in profile.training_caution_items),
            key=str,
        ),
        profile_created_at=profile.created_at,
        profile_updated_at=profile.updated_at,
        nutrition=nutrition,
        medical=medical,
    )


def _nutrition_summary(
    db: Session,
    profile: NutritionProfile | None,
) -> ReviewProfileNutrition | None:
    if profile is None:
        return None
    equipment = db.scalars(
        select(NutritionCookingEquipment)
        .where(NutritionCookingEquipment.user_id == profile.user_id)
        .order_by(NutritionCookingEquipment.equipment)
    ).all()
    food_items = db.scalars(
        select(NutritionFoodItem)
        .where(NutritionFoodItem.user_id == profile.user_id)
        .order_by(NutritionFoodItem.kind, NutritionFoodItem.normalized_name)
    ).all()
    exercise = db.get(NutritionStructuredExercise, profile.user_id)
    return ReviewProfileNutrition(
        onboarding_status=_enum_value(profile.onboarding_status),
        daily_activity_level=_enum_value(profile.daily_activity_level),
        metabolic_basis=_enum_value(profile.metabolic_basis),
        individual_monthly_food_budget_irr=profile.individual_monthly_food_budget_irr,
        budget_style=_enum_value(profile.budget_style),
        meals_per_day=profile.meals_per_day,
        snacks_per_day=profile.snacks_per_day,
        main_meal_count_bucket=_enum_value(profile.main_meal_count_bucket),
        snack_count_bucket=_enum_value(profile.snack_count_bucket),
        effective_main_meal_slots=profile.effective_main_meal_slots,
        effective_snack_slots=profile.effective_snack_slots,
        preferred_plan_start_day=_enum_value(profile.preferred_plan_start_day),
        plan_style=_enum_value(profile.plan_style),
        cooking_skill=_enum_value(profile.cooking_skill),
        maximum_cooking_time_minutes=profile.maximum_cooking_time_minutes,
        cooking_frequency_per_week=profile.cooking_frequency_per_week,
        meal_preparation_preference=_enum_value(profile.meal_preparation_preference),
        refrigerator_access=profile.refrigerator_access,
        freezer_access=profile.freezer_access,
        supplied_meals_per_week=profile.supplied_meals_per_week,
        supplied_meal_source=profile.supplied_meal_source,
        dietary_pattern=_enum_value(profile.dietary_pattern),
        preferred_variety=_enum_value(profile.preferred_variety),
        maximum_meal_repetition_per_week=profile.maximum_meal_repetition_per_week,
        accepts_leftovers=profile.accepts_leftovers,
        accepts_batch_cooking=profile.accepts_batch_cooking,
        work_shift_context=profile.work_shift_context,
        daily_check_in_enabled=profile.daily_check_in_enabled,
        preferred_check_in_time=profile.preferred_check_in_time,
        target_weight_change_kg_per_week=profile.target_weight_change_kg_per_week,
        weight_rate_mode=_enum_value(profile.weight_rate_mode),
        cooking_equipment=[_enum_value(item.equipment) for item in equipment],
        food_items=[
            ReviewProfileFoodItem(
                kind=_enum_value(item.kind), name=item.name, details=item.details
            )
            for item in food_items
        ],
        structured_exercise=(
            ReviewProfileStructuredExercise(
                trains=exercise.trains,
                exercise_type=_enum_value(exercise.exercise_type),
                days_per_week=exercise.days_per_week,
                minutes_per_session=exercise.minutes_per_session,
                intensity=_enum_value(exercise.intensity),
                source=_enum_value(exercise.source),
                confirmed_at=exercise.confirmed_at,
                updated_at=exercise.updated_at,
            )
            if exercise is not None
            else None
        ),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _medical_summary(db: Session, user_id: UUID) -> ReviewProfileMedical | None:
    profile = db.get(NutritionMedicalProfile, user_id)
    conditions = db.scalars(
        select(NutritionMedicalCondition)
        .where(NutritionMedicalCondition.user_id == user_id)
        .order_by(NutritionMedicalCondition.code)
    ).all()
    medications = db.scalars(
        select(NutritionMedication)
        .where(NutritionMedication.user_id == user_id)
        .order_by(NutritionMedication.name)
    ).all()
    safety = db.scalar(
        select(NutritionSafetyDecision)
        .where(NutritionSafetyDecision.user_id == user_id)
        .options(selectinload(NutritionSafetyDecision.reasons))
        .order_by(NutritionSafetyDecision.created_at.desc(), NutritionSafetyDecision.id.desc())
    )
    if profile is None:
        return None
    return ReviewProfileMedical(
        flags={
            "dangerous_food_reaction_history": profile.dangerous_food_reaction_history,
            "pregnant": profile.pregnant,
            "breastfeeding": profile.breastfeeding,
            "eating_disorder_diagnosed": profile.eating_disorder_diagnosed,
            "eating_disorder_active_symptoms": profile.eating_disorder_active_symptoms,
            "emergency_or_danger_symptoms": profile.emergency_or_danger_symptoms,
            "complex_medication_food_interaction": profile.complex_medication_food_interaction,
        },
        physician_dietary_restrictions=profile.physician_dietary_restrictions,
        other_relevant_condition=profile.other_relevant_condition,
        conditions=[
            ReviewProfileMedicalCondition(
                code=_enum_value(item.code), details=item.details
            )
            for item in conditions
        ],
        medications=[
            ReviewProfileMedication(name=item.name, dosage=item.dosage, notes=item.notes)
            for item in medications
        ],
        safety_outcome=_enum_value(safety.outcome) if safety else None,
        safety_reason_codes=[reason.code for reason in safety.reasons] if safety else [],
        medical_condition_policy_version=(
            safety.medical_condition_policy_version if safety else None
        ),
        safety_decision_created_at=safety.created_at if safety else None,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    raw_value = getattr(value, "value", value)
    return str(raw_value)
