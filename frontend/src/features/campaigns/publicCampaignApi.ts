import type { CampaignSurface, PublicSignupCampaign } from "@fitician/core/campaigns";

import { request } from "../../shared/apiClient";

const publicCampaignPath = "/api/v1/campaigns/signup/active";

export function getActiveSignupCampaign(
  surface: CampaignSurface,
): Promise<PublicSignupCampaign | null> {
  return request<PublicSignupCampaign | null>(
    `${publicCampaignPath}?surface=${encodeURIComponent(surface)}`,
  );
}
