from enum import StrEnum


class BillingOfferCode(StrEnum):
    TRAINING_4W = "training_4w"
    TRAINING_6W = "training_6w"
    TRAINING_8W = "training_8w"
    TRAINING_COACH_4W = "training_coach_4w"
    TRAINING_COACH_6W = "training_coach_6w"
    TRAINING_COACH_8W = "training_coach_8w"
    NUTRITION_4W = "nutrition_4w"
    NUTRITION_6W = "nutrition_6w"
    NUTRITION_8W = "nutrition_8w"
    NUTRITION_PHYSICIAN_4W = "nutrition_physician_4w"
    NUTRITION_PHYSICIAN_6W = "nutrition_physician_6w"
    NUTRITION_PHYSICIAN_8W = "nutrition_physician_8w"
    COMPLETE_4W = "complete_4w"
    COMPLETE_6W = "complete_6w"
    COMPLETE_8W = "complete_8w"
    COMPLETE_CARE_4W = "complete_care_4w"
    COMPLETE_CARE_6W = "complete_care_6w"
    COMPLETE_CARE_8W = "complete_care_8w"


class BillingOrderStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class BillingTransactionStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentProviderCode(StrEnum):
    FAKE = "fake"
