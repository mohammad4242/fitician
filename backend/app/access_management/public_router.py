from datetime import UTC, datetime

from fastapi import APIRouter

from app.access_management.enums import CampaignSurface
from app.access_management.repository import get_active_signup_bonus_for_surface
from app.access_management.schemas import PublicSignupCampaignResponse
from app.access_management.service import public_campaign_response
from app.auth.dependencies import DatabaseSession

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.get(
    "/signup/active",
    response_model=PublicSignupCampaignResponse | None,
)
def read_active_signup_campaign(
    db: DatabaseSession,
    surface: CampaignSurface = CampaignSurface.LANDING,
) -> PublicSignupCampaignResponse | None:
    campaign = get_active_signup_bonus_for_surface(
        db,
        surface,
        now=datetime.now(UTC),
    )
    return None if campaign is None else public_campaign_response(campaign)
