from enum import StrEnum


class AccessPackageCode(StrEnum):
    FREE = "free"
    TRAINING = "training"
    TRAINING_COACH = "training_coach"
    NUTRITION = "nutrition"
    NUTRITION_PHYSICIAN = "nutrition_physician"
    COMPLETE = "complete"
    COMPLETE_CARE = "complete_care"
    LAUNCH_TRIAL = "launch_trial"


class AccessPackageKind(StrEnum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    TRIAL = "trial"


class GrantSource(StrEnum):
    LAUNCH_TRIAL = "launch_trial"
    MANUAL = "manual"
    PROMOTION = "promotion"
    SUBSCRIPTION = "subscription"
    ADMIN = "admin"


class EntitlementCode(StrEnum):
    TRAINING_PLAN_GENERATE = "training.plan.generate"
    TRAINING_CYCLE_MANAGE = "training.cycle.manage"
    TRAINING_COACH_REVIEW = "training.coach_review"

    NUTRITION_PLAN_GENERATE = "nutrition.plan.generate"
    NUTRITION_PLAN_MANAGE = "nutrition.plan.manage"
    NUTRITION_FOOD_PHOTO_ANALYZE = "nutrition.food_photo.analyze"
    NUTRITION_PHYSICIAN_REVIEW = "nutrition.physician_review"
    NUTRITION_LABS_MANAGE = "nutrition.labs.manage"
    NUTRITION_SUPPLEMENTS_MANAGE = "nutrition.supplements.manage"

    BODY_ANALYSIS_RUN = "body_analysis.run"
