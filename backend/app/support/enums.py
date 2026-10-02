from enum import StrEnum


class SupportCategory(StrEnum):
    TECHNICAL = "technical"
    ACCOUNT = "account"
    BILLING = "billing"
    WORKOUT = "workout"
    NUTRITION = "nutrition"
    BODY_ANALYSIS = "body_analysis"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class SupportStatus(StrEnum):
    OPEN = "open"
    AWAITING_USER = "awaiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"
