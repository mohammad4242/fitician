from enum import StrEnum


class AccessCampaignKind(StrEnum):
    SIGNUP_BONUS = "signup_bonus"
    MANUAL_PROMOTION = "manual_promotion"


class CampaignSurface(StrEnum):
    LANDING = "landing"
    REGISTER = "register"
