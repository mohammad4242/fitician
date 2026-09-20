import type { TransportRequest } from "@fitician/core";
import type { CampaignSurface, PublicSignupCampaign } from "@fitician/core/campaigns";

export type PublicCampaignRequest = <TResponse>(request: TransportRequest) => Promise<TResponse>;

export interface PublicCampaignApi {
  getActiveSignupCampaign(surface: CampaignSurface): Promise<PublicSignupCampaign | null>;
}

const publicCampaignPath = "/api/v1/campaigns/signup/active";

export function createPublicCampaignApi(request: PublicCampaignRequest): PublicCampaignApi {
  return {
    getActiveSignupCampaign: (surface) => request<PublicSignupCampaign | null>({
      method: "GET",
      path: `${publicCampaignPath}?surface=${encodeURIComponent(surface)}`,
    }),
  };
}
