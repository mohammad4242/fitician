from datetime import date, time
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.nutrition.enums import (
    BudgetStyle,
    CookingEquipment,
    CookingSkill,
    DailyActivityLevel,
    DietaryPattern,
    FoodItemKind,
    MainMealCountBucket,
    MealPreparationPreference,
    NutritionOnboardingStatus,
    NutritionPlanStyle,
    PreferredVariety,
    SnackCountBucket,
    Weekday,
    WeightRateMode,
)
from app.nutrition.models import (
    NutritionCookingEquipment,
    NutritionFoodItem,
    NutritionMedicalCondition,
    NutritionMedicalProfile,
    NutritionMedication,
    NutritionProfile,
    NutritionStructuredExercise,
)
from app.profile.enums import (
    ExperienceLevel,
    FitnessGoal,
    ProductMode,
    Sex,
    TrainingCaution,
    TrainingIntensity,
    TrainingLocation,
    WorkoutGenerationMethod,
)
from app.profile.models import BodyMeasurement, UserProfile, UserProfileTrainingCaution
from app.profile.review_summary import build_review_profile_summary

ORIGIN = {"Origin": "http://localhost:5173"}


def _register(client: TestClient) -> UUID:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "review-summary@example.com", "password": "long password"},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _seed_profile(db: Session, user_id: UUID) -> None:
    db.add(
        UserProfile(
            user_id=user_id,
            product_mode=ProductMode.BOTH,
            timezone="Asia/Tehran",
            display_name="سارا",
            birth_date=date(1995, 4, 12),
            sex=Sex.FEMALE,
            height_cm=165,
            fitness_goal=FitnessGoal.BODY_RECOMPOSITION,
            experience_level=ExperienceLevel.INTERMEDIATE,
            training_age_months=24,
            preferred_weekdays=[0, 2, 4],
            priority_muscles=["glutes", "back"],
            training_days_per_week=3,
            training_location=TrainingLocation.GYM,
            available_equipment=None,
            session_duration_minutes=60,
            training_intensity=TrainingIntensity.MODERATE,
            physical_limitations="زانو باید کنترل شود",
            plan_duration_weeks=8,
            workout_generation_method=WorkoutGenerationMethod.FITICIAN_COACH,
            training_caution_items=[UserProfileTrainingCaution(caution=TrainingCaution.KNEE)],
        )
    )
    db.add(
        BodyMeasurement(
            user_id=user_id,
            weight_kg=Decimal("62.50"),
            shoulder_circumference_cm=Decimal("96"),
            waist_circumference_cm=Decimal("72"),
            hip_circumference_cm=Decimal("101"),
        )
    )
    db.flush()
    db.add(
        NutritionProfile(
            user_id=user_id,
            onboarding_status=NutritionOnboardingStatus.COMPLETED,
            daily_activity_level=DailyActivityLevel.MODERATE,
            metabolic_basis=None,
            individual_monthly_food_budget_irr=13_000_000,
            budget_style=BudgetStyle.STRICT,
            meals_per_day=3,
            snacks_per_day=1,
            main_meal_count_bucket=MainMealCountBucket.THREE,
            snack_count_bucket=SnackCountBucket.ONE,
            effective_main_meal_slots=3,
            effective_snack_slots=1,
            preferred_plan_start_day=Weekday.SATURDAY,
            plan_style=NutritionPlanStyle.BALANCED,
            cooking_skill=CookingSkill.BASIC,
            maximum_cooking_time_minutes=45,
            cooking_frequency_per_week=4,
            meal_preparation_preference=MealPreparationPreference.MIXED,
            refrigerator_access=True,
            freezer_access=True,
            supplied_meals_per_week=2,
            supplied_meal_source="محل کار",
            dietary_pattern=DietaryPattern.OMNIVORE,
            preferred_variety=PreferredVariety.MEDIUM,
            maximum_meal_repetition_per_week=3,
            accepts_leftovers=True,
            accepts_batch_cooking=False,
            work_shift_context="شیفت صبح",
            daily_check_in_enabled=True,
            preferred_check_in_time=time(9, 30),
            target_weight_change_kg_per_week=Decimal("0.5"),
            weight_rate_mode=WeightRateMode.SAFE,
        )
    )
    db.flush()
    db.add(NutritionCookingEquipment(user_id=user_id, equipment=CookingEquipment.STOVE))
    db.add(
        NutritionFoodItem(
            user_id=user_id,
            kind=FoodItemKind.FAVOURITE,
            name="مرغ",
            normalized_name="مرغ",
            details="پروتئین اصلی",
        )
    )
    db.add(
        NutritionStructuredExercise(
            user_id=user_id,
            trains=True,
            exercise_type="resistance",
            days_per_week=3,
            minutes_per_session=60,
            intensity=TrainingIntensity.MODERATE,
            source="training_profile",
        )
    )
    db.add(
        NutritionMedicalProfile(
            user_id=user_id,
            dangerous_food_reaction_history=False,
            pregnant=False,
            breastfeeding=False,
            eating_disorder_diagnosed=False,
            eating_disorder_active_symptoms=False,
            emergency_or_danger_symptoms=False,
            complex_medication_food_interaction=True,
            physician_dietary_restrictions="نمک محدود",
            other_relevant_condition="پیگیری فشار خون",
        )
    )
    db.flush()
    db.add(
        NutritionMedicalCondition(
            user_id=user_id,
            code="controlled_hypertension",
            details="تحت کنترل",
        )
    )
    db.add(
        NutritionMedication(
            user_id=user_id,
            name="داروی فشار خون",
            dosage="روزانه",
            notes="صبح مصرف شود",
        )
    )
    db.flush()


def test_build_review_profile_summary_contains_current_training_nutrition_and_medical_data(
    client: TestClient,
    db: Session,
) -> None:
    user_id = _register(client)
    _seed_profile(db, user_id)

    summary = build_review_profile_summary(db, user_id)

    assert summary is not None
    assert summary.display_name == "سارا"
    assert summary.height_cm == 165
    assert summary.weight_kg == Decimal("62.50")
    assert summary.training_cautions == ["knee"]
    assert summary.physical_limitations == "زانو باید کنترل شود"
    assert summary.nutrition is not None
    assert summary.nutrition.individual_monthly_food_budget_irr == 13_000_000
    assert summary.nutrition.cooking_equipment == ["stove"]
    assert summary.nutrition.food_items[0].kind == "favourite"
    assert summary.nutrition.structured_exercise is not None
    assert summary.nutrition.structured_exercise.days_per_week == 3
    assert summary.medical is not None
    assert summary.medical.flags["complex_medication_food_interaction"] is True
    assert summary.medical.conditions[0].code == "controlled_hypertension"
    assert summary.medical.medications[0].name == "داروی فشار خون"


def test_build_review_profile_summary_returns_none_without_profile(
    db: Session,
) -> None:
    assert build_review_profile_summary(db, UUID("00000000-0000-0000-0000-000000000001")) is None
