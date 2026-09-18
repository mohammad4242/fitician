from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.nutrition.enums import (
    CookingSkill,
    DietaryPattern,
    FoodItemKind,
    MealPreparationPreference,
    NutritionOnboardingStatus,
    NutritionPlanStyle,
    PhysicianReviewMode,
    PhysicianReviewStatus,
    PreferredVariety,
    SafetyOutcome,
    main_meal_effective_slots,
    snack_effective_slots,
)
from app.nutrition.exceptions import (
    DietaryPatternNotSupportedV1Error,
    NutritionCatalogueTargetError,
    NutritionOnboardingBlockedError,
    NutritionProfileNotFoundError,
    SafetyDecisionNotFoundError,
    SafetyScreenRequiredError,
    SharedProfileRequiredError,
)
from app.nutrition.food_catalogue import normalize_food_alias
from app.nutrition.models import (
    NutritionCatalogueFood,
    NutritionCatalogueMeal,
    NutritionCookingEquipment,
    NutritionFoodItem,
    NutritionMedicalCondition,
    NutritionMedicalProfile,
    NutritionMedication,
    NutritionPhysicianReview,
    NutritionProfile,
    NutritionSafetyDecision,
    NutritionSafetyReason,
)
from app.nutrition.safety import SafetyAnswers, evaluate_safety
from app.nutrition.schemas import (
    FoodConstraintInput,
    NutritionCatalogueConstraintInput,
    NutritionCatalogueConstraintResponse,
    NutritionCatalogueTargetInput,
    NutritionCatalogueTargetResponse,
    NutritionProfileInput,
    NutritionProfileResponse,
    PhysicianReviewRequirementResponse,
    SafetyDecisionResponse,
    SafetyEvaluationResponse,
    SafetyProfileInput,
)
from app.profile.enums import ProductMode
from app.profile.models import UserProfile


@dataclass(frozen=True)
class NutritionSnapshot:
    profile: NutritionProfile
    equipment: tuple[NutritionCookingEquipment, ...]
    foods: tuple[NutritionFoodItem, ...]
    safety: NutritionSafetyDecision
    catalogue_foods: dict[UUID, NutritionCatalogueFood]
    catalogue_meals: dict[UUID, NutritionCatalogueMeal]


@dataclass(frozen=True)
class _PreferenceTarget:
    target_type: str
    target_id: UUID
    details: str | None = None


_SAFETY_MESSAGES = {
    SafetyOutcome.STANDARD_AUTOMATIC: "عالی، می‌توانیم اطلاعات تغذیه‌ات را کامل کنیم.",
    SafetyOutcome.AUTOMATIC_DRAFT_REQUIRES_PHYSICIAN_REVIEW: (
        "برنامه اولیه آماده می‌شود اما برای فعال‌شدن به بررسی پزشک فیتیشن نیاز دارد."
    ),
    SafetyOutcome.PHYSICIAN_MANUAL_PLAN_REQUIRED: (
        "برای حفظ ایمنی، برنامه غذایی باید توسط پزشک فیتیشن تنظیم شود."
    ),
    SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED: (
        "در حال حاضر امکان ارائه برنامه خودکار ایمن برای این شرایط وجود ندارد."
    ),
}


def evaluate_safety_profile(payload: SafetyProfileInput) -> SafetyEvaluationResponse:
    evaluation = evaluate_safety(_safety_answers(payload))
    can_continue = evaluation.outcome in {
        SafetyOutcome.STANDARD_AUTOMATIC,
        SafetyOutcome.AUTOMATIC_DRAFT_REQUIRES_PHYSICIAN_REVIEW,
    }
    return SafetyEvaluationResponse(
        outcome=evaluation.outcome,
        policy_version=evaluation.policy_version,
        reason_codes=list(evaluation.reason_codes),
        requires_physician_review=evaluation.outcome is not SafetyOutcome.STANDARD_AUTOMATIC,
        can_continue_onboarding=can_continue,
        message=_SAFETY_MESSAGES[evaluation.outcome],
    )


def _safety_answers(payload: SafetyProfileInput) -> SafetyAnswers:
    return SafetyAnswers(
        conditions=tuple(item.code for item in payload.conditions),
        dangerous_food_reaction_history=payload.dangerous_food_reaction_history,
        pregnant=payload.pregnant,
        breastfeeding=payload.breastfeeding,
        eating_disorder_diagnosed=payload.eating_disorder_diagnosed,
        eating_disorder_active_symptoms=payload.eating_disorder_active_symptoms,
        emergency_or_danger_symptoms=payload.emergency_or_danger_symptoms,
        physician_dietary_restrictions=payload.physician_dietary_restrictions is not None,
        other_relevant_condition=payload.other_relevant_condition is not None,
        complex_medication_food_interaction=payload.complex_medication_food_interaction,
    )


def _require_shared_profile(db: Session, user_id: UUID, *, lock: bool = False) -> UserProfile:
    statement = select(UserProfile).where(UserProfile.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    profile = db.scalar(statement)
    if (
        profile is None
        or profile.product_mode not in {ProductMode.NUTRITION, ProductMode.BOTH}
        or profile.display_name is None
        or profile.birth_date is None
        or profile.sex is None
        or profile.height_cm is None
        or profile.fitness_goal is None
    ):
        raise SharedProfileRequiredError
    return profile


def save_safety_profile(
    db: Session,
    user_id: UUID,
    payload: SafetyProfileInput,
) -> NutritionSafetyDecision:
    _require_shared_profile(db, user_id, lock=True)
    medical = db.scalar(
        select(NutritionMedicalProfile)
        .where(NutritionMedicalProfile.user_id == user_id)
        .with_for_update()
    )
    values = {
        "dangerous_food_reaction_history": payload.dangerous_food_reaction_history,
        "pregnant": payload.pregnant,
        "breastfeeding": payload.breastfeeding,
        "eating_disorder_diagnosed": payload.eating_disorder_diagnosed,
        "eating_disorder_active_symptoms": payload.eating_disorder_active_symptoms,
        "emergency_or_danger_symptoms": payload.emergency_or_danger_symptoms,
        "complex_medication_food_interaction": payload.complex_medication_food_interaction,
        "physician_dietary_restrictions": payload.physician_dietary_restrictions,
        "other_relevant_condition": payload.other_relevant_condition,
    }
    if medical is None:
        medical = NutritionMedicalProfile(user_id=user_id, **values)
        db.add(medical)
    else:
        for field_name, value in values.items():
            setattr(medical, field_name, value)

    evaluation = evaluate_safety(_safety_answers(payload))
    try:
        db.flush()
        db.execute(
            delete(NutritionMedicalCondition).where(NutritionMedicalCondition.user_id == user_id)
        )
        db.execute(delete(NutritionMedication).where(NutritionMedication.user_id == user_id))
        db.add_all(
            [
                NutritionMedicalCondition(
                    user_id=user_id,
                    code=item.code,
                    details=item.details,
                )
                for item in payload.conditions
            ]
        )
        db.add_all(
            [
                NutritionMedication(
                    user_id=user_id,
                    name=item.name,
                    dosage=item.dosage,
                    notes=item.notes,
                )
                for item in payload.medications
            ]
        )
        latest_revision = db.scalar(
            select(NutritionSafetyDecision.revision)
            .where(NutritionSafetyDecision.user_id == user_id)
            .order_by(NutritionSafetyDecision.revision.desc())
            .limit(1)
        )
        decision = NutritionSafetyDecision(
            user_id=user_id,
            medical_condition_policy_version=evaluation.policy_version,
            revision=(latest_revision or 0) + 1,
            outcome=evaluation.outcome,
            reasons=[NutritionSafetyReason(code=code) for code in evaluation.reason_codes],
        )
        db.add(decision)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return current_safety_decision(db, user_id)


def current_safety_decision(db: Session, user_id: UUID) -> NutritionSafetyDecision:
    decision = db.scalar(
        select(NutritionSafetyDecision)
        .where(NutritionSafetyDecision.user_id == user_id)
        .options(selectinload(NutritionSafetyDecision.reasons))
        .order_by(NutritionSafetyDecision.revision.desc())
        .limit(1)
    )
    if decision is None:
        raise SafetyDecisionNotFoundError
    return decision


def safety_response(decision: NutritionSafetyDecision) -> SafetyDecisionResponse:
    can_continue = decision.outcome in {
        SafetyOutcome.STANDARD_AUTOMATIC,
        SafetyOutcome.AUTOMATIC_DRAFT_REQUIRES_PHYSICIAN_REVIEW,
    }
    return SafetyDecisionResponse(
        id=decision.id,
        outcome=decision.outcome,
        policy_version=decision.medical_condition_policy_version,
        reason_codes=[item.code for item in decision.reasons],
        requires_physician_review=decision.outcome is not SafetyOutcome.STANDARD_AUTOMATIC,
        can_continue_onboarding=can_continue,
        message=_SAFETY_MESSAGES[decision.outcome],
        created_at=decision.created_at,
    )


def physician_review_requirement(
    db: Session,
    user_id: UUID,
) -> PhysicianReviewRequirementResponse:
    decision = current_safety_decision(db, user_id)
    modes = {
        SafetyOutcome.STANDARD_AUTOMATIC: PhysicianReviewMode.NONE,
        SafetyOutcome.AUTOMATIC_DRAFT_REQUIRES_PHYSICIAN_REVIEW: (
            PhysicianReviewMode.AUTOMATIC_DRAFT_REVIEW
        ),
        SafetyOutcome.PHYSICIAN_MANUAL_PLAN_REQUIRED: PhysicianReviewMode.MANUAL_PLAN,
        SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED: PhysicianReviewMode.BLOCKED,
    }
    review = db.scalar(
        select(NutritionPhysicianReview)
        .where(
            NutritionPhysicianReview.user_id == user_id,
            NutritionPhysicianReview.safety_decision_id == decision.id,
        )
        .order_by(NutritionPhysicianReview.created_at.desc())
        .limit(1)
    )
    return PhysicianReviewRequirementResponse(
        required=decision.outcome is not SafetyOutcome.STANDARD_AUTOMATIC,
        mode=modes[decision.outcome],
        status=review.status if review is not None else PhysicianReviewStatus.NOT_REQUESTED,
        safety_decision_id=decision.id,
    )


def save_nutrition_profile(
    db: Session,
    user_id: UUID,
    payload: NutritionProfileInput,
) -> NutritionSnapshot:
    shared_profile = _require_shared_profile(db, user_id)
    try:
        decision = current_safety_decision(db, user_id)
    except SafetyDecisionNotFoundError as error:
        raise SafetyScreenRequiredError from error
    if decision.outcome in {
        SafetyOutcome.PHYSICIAN_MANUAL_PLAN_REQUIRED,
        SafetyOutcome.UNSUPPORTED_OR_HARD_BLOCKED,
    }:
        raise NutritionOnboardingBlockedError

    if payload.dietary_pattern in {DietaryPattern.VEGETARIAN, DietaryPattern.VEGAN}:
        raise DietaryPatternNotSupportedV1Error(
            "Vegetarian and vegan dietary patterns are not supported in V1."
        )

    # Resolve and validate every target before mutating the profile or deleting its rows.
    resolved_food_items = _food_items(db, user_id, payload)

    profile = db.get(NutritionProfile, user_id)
    scalar_values = payload.model_dump(
        exclude={
            "cooking_equipment",
            "plan_style",
            "cooking_skill",
            "maximum_cooking_time_minutes",
            "cooking_frequency_per_week",
            "meal_preparation_preference",
            "refrigerator_access",
            "freezer_access",
            "supplied_meals_per_week",
            "supplied_meal_source",
            "foods_available_at_home",
            "favourite_foods",
            "disliked_foods",
            "never_suggest_foods",
            "refused_foods",
            "allergies",
            "intolerances",
            "favourite_catalogue_items",
            "disliked_catalogue_items",
            "allergy_catalogue_items",
            "intolerance_catalogue_items",
            "religious_cultural_exclusions",
            "preferred_variety",
            "maximum_meal_repetition_per_week",
            "accepts_leftovers",
            "accepts_batch_cooking",
        }
    )
    scalar_values["meals_per_day"] = payload.meals_per_day
    scalar_values["snacks_per_day"] = payload.snacks_per_day
    scalar_values["main_meal_count_bucket"] = payload.main_meal_count_bucket
    scalar_values["snack_count_bucket"] = payload.snack_count_bucket
    assert payload.main_meal_count_bucket is not None
    assert payload.snack_count_bucket is not None
    scalar_values["effective_main_meal_slots"] = main_meal_effective_slots(
        payload.main_meal_count_bucket
    )
    scalar_values["effective_snack_slots"] = snack_effective_slots(payload.snack_count_bucket)
    if (
        shared_profile.fitness_goal is not None
        and shared_profile.fitness_goal.value == "body_recomposition"
    ):
        scalar_values["target_weight_change_kg_per_week"] = None
    if profile is None:
        # These columns predate Task 2A. Keep safe defaults for old non-null columns,
        # but never expose or ask them as Nutrition inputs.
        scalar_values.update(
            plan_style=NutritionPlanStyle.BALANCED,
            cooking_skill=CookingSkill.NONE,
            maximum_cooking_time_minutes=0,
            cooking_frequency_per_week=0,
            meal_preparation_preference=MealPreparationPreference.NO_COOKING,
            refrigerator_access=True,
            freezer_access=True,
            supplied_meals_per_week=0,
            supplied_meal_source=None,
            preferred_variety=PreferredVariety.MEDIUM,
            maximum_meal_repetition_per_week=3,
            accepts_leftovers=True,
            accepts_batch_cooking=False,
        )
    scalar_values["onboarding_status"] = NutritionOnboardingStatus.COMPLETED
    if profile is None:
        profile = NutritionProfile(user_id=user_id, **scalar_values)
        db.add(profile)
    else:
        for field_name, value in scalar_values.items():
            setattr(profile, field_name, value)

    try:
        db.flush()
        # Cooking/preparation data is legacy-only and is deliberately not rewritten.
        db.execute(delete(NutritionFoodItem).where(NutritionFoodItem.user_id == user_id))
        db.add_all(resolved_food_items)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return get_nutrition_profile(db, user_id)


def _food_items(
    db: Session,
    user_id: UUID,
    payload: NutritionProfileInput,
) -> list[NutritionFoodItem]:
    items: list[NutritionFoodItem] = []
    explicit_inputs = (
        *payload.favourite_catalogue_items,
        *payload.disliked_catalogue_items,
        *payload.allergy_catalogue_items,
        *payload.intolerance_catalogue_items,
    )
    food_rows = {
        row.id: row
        for row in db.scalars(
            select(NutritionCatalogueFood).where(NutritionCatalogueFood.id.in_(
                [item.target_id for item in explicit_inputs if item.target_type == "food"]
            ))
        ).all()
    }
    meal_rows = {
        row.id: row
        for row in db.scalars(
            select(NutritionCatalogueMeal).where(NutritionCatalogueMeal.id.in_(
                [item.target_id for item in explicit_inputs if item.target_type == "meal"]
            ))
        ).all()
    }
    all_legacy_values = [
        *payload.favourite_foods,
        *payload.disliked_foods,
        *(item.name for item in payload.allergies),
        *(item.name for item in payload.intolerances),
    ]
    legacy_matches = _legacy_catalogue_matches(db) if all_legacy_values else {}

    def resolve(
        explicit: list[NutritionCatalogueTargetInput] | list[NutritionCatalogueConstraintInput],
        legacy_values: list[str],
        *,
        details: list[str | None] | None = None,
    ) -> list[_PreferenceTarget]:
        resolved: list[_PreferenceTarget] = []
        for item in explicit:
            resolved.append(
                _validate_explicit_target(
                    item.target_type,
                    item.target_id,
                    food_rows,
                    meal_rows,
                    db,
                    item.details if isinstance(item, NutritionCatalogueConstraintInput) else None,
                )
            )
        for index, name in enumerate(legacy_values):
            matches = legacy_matches.get(normalize_food_alias(name), frozenset())
            if len(matches) == 0:
                raise NutritionCatalogueTargetError(
                    "NUTRITION_CATALOGUE_TARGET_NOT_FOUND",
                    "The nutrition preference is not a verified catalogue target.",
                )
            if len(matches) > 1:
                raise NutritionCatalogueTargetError(
                    "NUTRITION_CATALOGUE_TARGET_AMBIGUOUS",
                    "The nutrition preference matches more than one catalogue target.",
                )
            target_type, target_id = next(iter(matches))
            resolved.append(
                _PreferenceTarget(
                    target_type=target_type,
                    target_id=target_id,
                    details=details[index] if details is not None else None,
                )
            )
        return resolved

    string_collections = {
        FoodItemKind.FAVOURITE: payload.favourite_foods,
        FoodItemKind.DISLIKED: payload.disliked_foods,
        FoodItemKind.RELIGIOUS_CULTURAL_EXCLUSION: payload.religious_cultural_exclusions,
    }
    favourite = resolve(payload.favourite_catalogue_items, payload.favourite_foods)
    disliked = resolve(payload.disliked_catalogue_items, payload.disliked_foods)
    allergy = resolve(
        payload.allergy_catalogue_items,
        [item.name for item in payload.allergies],
        details=[item.details for item in payload.allergies],
    )
    intolerance = resolve(
        payload.intolerance_catalogue_items,
        [item.name for item in payload.intolerances],
        details=[item.details for item in payload.intolerances],
    )
    _reject_preference_conflicts((*favourite, *disliked, *allergy, *intolerance),
        (len(favourite), len(disliked), len(allergy), len(intolerance)))
    for kind, targets in (
        (FoodItemKind.FAVOURITE, favourite),
        (FoodItemKind.DISLIKED, disliked),
        (FoodItemKind.ALLERGY, allergy),
        (FoodItemKind.INTOLERANCE, intolerance),
    ):
        for target in targets:
            record = (
                food_rows.get(target.target_id)
                if target.target_type == "food"
                else meal_rows.get(target.target_id)
            )
            if record is None:
                record = cast(
                    NutritionCatalogueFood | NutritionCatalogueMeal | None,
                    db.get(
                        NutritionCatalogueFood
                        if target.target_type == "food"
                        else NutritionCatalogueMeal,
                        target.target_id,
                    ),
                )
            assert record is not None
            name = record.name_fa
            items.append(
                NutritionFoodItem(
                    user_id=user_id,
                    kind=kind,
                    name=name,
                    normalized_name=normalize_food_alias(name),
                    details=target.details,
                    catalogue_food_id=target.target_id if target.target_type == "food" else None,
                    catalogue_meal_id=target.target_id if target.target_type == "meal" else None,
                )
            )
    for kind, names in string_collections.items():
        if kind is FoodItemKind.RELIGIOUS_CULTURAL_EXCLUSION:
            items.extend(_named_items(user_id, kind, names))
    return items


def _legacy_catalogue_matches(
    db: Session,
) -> dict[str, frozenset[tuple[str, UUID]]]:
    matches: dict[str, set[tuple[str, UUID]]] = {}
    foods = db.scalars(
        select(NutritionCatalogueFood)
        .where(NutritionCatalogueFood.verification_status == "verified")
        .options(selectinload(NutritionCatalogueFood.aliases))
    ).all()
    meals = db.scalars(
        select(NutritionCatalogueMeal).where(
            NutritionCatalogueMeal.verification_status == "verified"
        )
    ).all()
    for food in foods:
        values = (food.name_fa, food.name_en, food.slug, *(alias.alias for alias in food.aliases))
        for value in values:
            matches.setdefault(normalize_food_alias(value), set()).add(("food", food.id))
    for meal in meals:
        for value in (meal.name_fa, meal.name_en, meal.code):
            matches.setdefault(normalize_food_alias(value), set()).add(("meal", meal.id))
    return {key: frozenset(value) for key, value in matches.items()}


def _validate_explicit_target(
    target_type: str,
    target_id: UUID,
    food_rows: dict[UUID, NutritionCatalogueFood],
    meal_rows: dict[UUID, NutritionCatalogueMeal],
    db: Session,
    details: str | None,
) -> _PreferenceTarget:
    rows = food_rows if target_type == "food" else meal_rows
    row = rows.get(target_id)
    if row is None:
        other_model = NutritionCatalogueMeal if target_type == "food" else NutritionCatalogueFood
        if db.scalar(select(other_model.id).where(other_model.id == target_id)) is not None:
            raise NutritionCatalogueTargetError(
                "NUTRITION_CATALOGUE_TARGET_TYPE_MISMATCH",
                "The nutrition catalogue target type does not match the database target.",
            )
        raise NutritionCatalogueTargetError(
            "NUTRITION_CATALOGUE_TARGET_NOT_FOUND",
            "The nutrition preference is not a verified catalogue target.",
        )
    if row.verification_status.value != "verified":
        raise NutritionCatalogueTargetError(
            "NUTRITION_CATALOGUE_TARGET_NOT_VERIFIED",
            "The nutrition catalogue target is not verified.",
        )
    return _PreferenceTarget(target_type=target_type, target_id=target_id, details=details)


def _reject_preference_conflicts(
    entries: tuple[_PreferenceTarget, ...],
    collection_sizes: tuple[int, int, int, int],
) -> None:
    if len({(entry.target_type, entry.target_id) for entry in entries}) != len(entries):
        raise NutritionCatalogueTargetError(
            "NUTRITION_PREFERENCE_CONFLICT",
            "A nutrition catalogue target cannot be repeated across preference categories.",
        )


def _named_items(
    user_id: UUID,
    kind: FoodItemKind,
    names: list[str],
) -> list[NutritionFoodItem]:
    return [
        NutritionFoodItem(
            user_id=user_id,
            kind=kind,
            name=name,
            normalized_name=normalize_food_alias(name),
        )
        for name in names
    ]


def _constraint_items(
    user_id: UUID,
    kind: FoodItemKind,
    values: list[FoodConstraintInput],
) -> list[NutritionFoodItem]:
    return [
        NutritionFoodItem(
            user_id=user_id,
            kind=kind,
            name=item.name,
            normalized_name=item.name.casefold(),
            details=item.details,
        )
        for item in values
    ]


def get_nutrition_profile(db: Session, user_id: UUID) -> NutritionSnapshot:
    profile = db.get(NutritionProfile, user_id)
    if profile is None:
        raise NutritionProfileNotFoundError
    equipment = tuple(
        db.scalars(
            select(NutritionCookingEquipment)
            .where(NutritionCookingEquipment.user_id == user_id)
            .order_by(NutritionCookingEquipment.equipment)
        ).all()
    )
    foods = tuple(
        db.scalars(
            select(NutritionFoodItem)
            .where(NutritionFoodItem.user_id == user_id)
            .order_by(NutritionFoodItem.kind, NutritionFoodItem.normalized_name)
        ).all()
    )
    food_ids = {item.catalogue_food_id for item in foods if item.catalogue_food_id is not None}
    meal_ids = {item.catalogue_meal_id for item in foods if item.catalogue_meal_id is not None}
    return NutritionSnapshot(
        profile=profile,
        equipment=equipment,
        foods=foods,
        safety=current_safety_decision(db, user_id),
        catalogue_foods={
            item.id: item
            for item in db.scalars(
                select(NutritionCatalogueFood).where(NutritionCatalogueFood.id.in_(food_ids))
            ).all()
        },
        catalogue_meals={
            item.id: item
            for item in db.scalars(
                select(NutritionCatalogueMeal).where(NutritionCatalogueMeal.id.in_(meal_ids))
            ).all()
        },
    )


def nutrition_profile_response(snapshot: NutritionSnapshot) -> NutritionProfileResponse:
    grouped: dict[FoodItemKind, list[NutritionFoodItem]] = {kind: [] for kind in FoodItemKind}
    for item in snapshot.foods:
        grouped[item.kind].append(item)

    def names(kind: FoodItemKind) -> list[str]:
        return [item.name for item in grouped[kind]]

    def constraints(kind: FoodItemKind) -> list[FoodConstraintInput]:
        return [FoodConstraintInput(name=item.name, details=item.details) for item in grouped[kind]]

    def target(item: NutritionFoodItem) -> NutritionCatalogueTargetResponse | None:
        catalogue: NutritionCatalogueFood | NutritionCatalogueMeal | None
        if item.catalogue_food_id is not None:
            catalogue = snapshot.catalogue_foods.get(item.catalogue_food_id)
            target_type = "food"
        elif item.catalogue_meal_id is not None:
            catalogue = snapshot.catalogue_meals.get(item.catalogue_meal_id)
            target_type = "meal"
        else:
            return None
        if catalogue is None:
            return None
        if target_type == "food":
            category = catalogue.category
        else:
            assert isinstance(catalogue, NutritionCatalogueMeal)
            category = catalogue.category.value
        return NutritionCatalogueTargetResponse(
            target_type=target_type,
            target_id=catalogue.id,
            name_fa=catalogue.name_fa,
            name_en=catalogue.name_en,
            category=category,
            image_url=catalogue.image_path,
        )

    def constraint_target(item: NutritionFoodItem) -> NutritionCatalogueConstraintResponse | None:
        base = target(item)
        if base is None:
            return None
        return NutritionCatalogueConstraintResponse(**base.model_dump(), details=item.details)

    profile = snapshot.profile
    return NutritionProfileResponse(
        user_id=profile.user_id,
        onboarding_status=profile.onboarding_status,
        daily_activity_level=profile.daily_activity_level,
        metabolic_basis=profile.metabolic_basis,
        individual_monthly_food_budget_irr=profile.individual_monthly_food_budget_irr,
        currency="IRR",
        weekly_budget_irr=profile.individual_monthly_food_budget_irr * 12 // 52,
        budget_style=profile.budget_style,
        meals_per_day=profile.meals_per_day,
        snacks_per_day=profile.snacks_per_day,
        main_meal_count_bucket=profile.main_meal_count_bucket,
        snack_count_bucket=profile.snack_count_bucket,
        preferred_plan_start_day=profile.preferred_plan_start_day,
        plan_style=profile.plan_style,
        cooking_skill=profile.cooking_skill,
        maximum_cooking_time_minutes=profile.maximum_cooking_time_minutes,
        cooking_frequency_per_week=profile.cooking_frequency_per_week,
        meal_preparation_preference=profile.meal_preparation_preference,
        refrigerator_access=profile.refrigerator_access,
        freezer_access=profile.freezer_access,
        cooking_equipment=[item.equipment for item in snapshot.equipment],
        supplied_meals_per_week=profile.supplied_meals_per_week,
        supplied_meal_source=profile.supplied_meal_source,
        foods_available_at_home=names(FoodItemKind.AVAILABLE_AT_HOME),
        favourite_foods=names(FoodItemKind.FAVOURITE),
        disliked_foods=names(FoodItemKind.DISLIKED),
        never_suggest_foods=names(FoodItemKind.NEVER_SUGGEST),
        refused_foods=names(FoodItemKind.REFUSED),
        allergies=constraints(FoodItemKind.ALLERGY),
        intolerances=constraints(FoodItemKind.INTOLERANCE),
        favourite_catalogue_items=[
            resolved
            for item in grouped[FoodItemKind.FAVOURITE]
            if (resolved := target(item)) is not None
        ],
        disliked_catalogue_items=[
            resolved
            for item in grouped[FoodItemKind.DISLIKED]
            if (resolved := target(item)) is not None
        ],
        allergy_catalogue_items=[
            resolved
            for item in grouped[FoodItemKind.ALLERGY]
            if (resolved := constraint_target(item)) is not None
        ],
        intolerance_catalogue_items=[
            resolved
            for item in grouped[FoodItemKind.INTOLERANCE]
            if (resolved := constraint_target(item)) is not None
        ],
        dietary_pattern=profile.dietary_pattern,
        religious_cultural_exclusions=names(FoodItemKind.RELIGIOUS_CULTURAL_EXCLUSION),
        preferred_variety=profile.preferred_variety,
        maximum_meal_repetition_per_week=profile.maximum_meal_repetition_per_week,
        accepts_leftovers=profile.accepts_leftovers,
        accepts_batch_cooking=profile.accepts_batch_cooking,
        work_shift_context=profile.work_shift_context,
        physician_review_required=(snapshot.safety.outcome is not SafetyOutcome.STANDARD_AUTOMATIC),
        daily_check_in_enabled=profile.daily_check_in_enabled,
        preferred_check_in_time=profile.preferred_check_in_time,
        target_weight_change_kg_per_week=profile.target_weight_change_kg_per_week,
        weight_rate_mode=profile.weight_rate_mode,
        effective_main_meal_slots=profile.effective_main_meal_slots,
        effective_snack_slots=profile.effective_snack_slots,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
