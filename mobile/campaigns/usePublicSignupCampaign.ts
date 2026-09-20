import { useEffect, useState } from "react";

import type { CampaignSurface, PublicSignupCampaign } from "@fitician/core/campaigns";

import { createPublicCampaignApi, type PublicCampaignRequest } from "./publicCampaignApi";

export function usePublicSignupCampaign(
  surface: CampaignSurface,
  request: PublicCampaignRequest,
): PublicSignupCampaign | null {
  const [campaign, setCampaign] = useState<PublicSignupCampaign | null>(null);

  useEffect(() => {
    let active = true;
    const api = createPublicCampaignApi(request);
    void api.getActiveSignupCampaign(surface)
      .then((result) => {
        if (active) setCampaign(result);
      })
      .catch(() => {
        if (active) setCampaign(null);
      });
    return () => {
      active = false;
    };
  }, [request, surface]);

  return campaign;
}
