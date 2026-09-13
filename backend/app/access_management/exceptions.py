class AccessManagementError(Exception):
    code = "ACCESS_MANAGEMENT_ERROR"
    status_code = 422

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.code
        super().__init__(self.message)


class CampaignNotFoundError(AccessManagementError):
    code = "ACCESS_CAMPAIGN_NOT_FOUND"
    status_code = 404


class UserNotFoundError(AccessManagementError):
    code = "ACCESS_USER_NOT_FOUND"
    status_code = 404


class GrantNotFoundError(AccessManagementError):
    code = "ACCESS_GRANT_NOT_FOUND"
    status_code = 404


class CampaignConflictError(AccessManagementError):
    code = "ACCESS_CAMPAIGN_CONFLICT"
    status_code = 409


class CampaignValidationError(AccessManagementError):
    code = "ACCESS_CAMPAIGN_INVALID"
    status_code = 422


class CampaignOverlapError(CampaignConflictError):
    code = "ACCESS_CAMPAIGN_WINDOW_OVERLAPS"


class CampaignImmutableError(CampaignConflictError):
    code = "ACCESS_CAMPAIGN_SEMANTICS_IMMUTABLE"


class CampaignRedemptionUnavailableError(CampaignConflictError):
    code = "ACCESS_CAMPAIGN_NOT_REDEEMABLE"


class CampaignKindError(AccessManagementError):
    code = "ACCESS_CAMPAIGN_KIND_INVALID"


class GrantIdempotencyConflictError(CampaignConflictError):
    code = "ACCESS_GRANT_IDEMPOTENCY_CONFLICT"
