from enum import StrEnum


class AdminAuditAction(StrEnum):
    BILLING_OFFER_UPDATED = "billing.offer.updated"
    ACCESS_CAMPAIGN_CREATED = "access.campaign.created"
    ACCESS_CAMPAIGN_UPDATED = "access.campaign.updated"
    ACCESS_CAMPAIGN_ACTIVATED = "access.campaign.activated"
    ACCESS_CAMPAIGN_DEACTIVATED = "access.campaign.deactivated"
    ACCESS_GRANT_CREATED = "access.grant.created"
    ACCESS_GRANT_REVOKED = "access.grant.revoked"
    ACCESS_CAMPAIGN_MANUALLY_REDEEMED = "access.campaign.manually_redeemed"
