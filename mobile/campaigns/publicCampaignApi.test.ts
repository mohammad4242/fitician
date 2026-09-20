import { expect, it } from "vitest";

import type { TransportRequest } from "@fitician/core";

import { createPublicCampaignApi } from "./publicCampaignApi";

it("requests the public campaign for each supported surface through the configured transport", async () => {
  const requests: TransportRequest[] = [];
  const api = createPublicCampaignApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return null as TResponse;
  });

  await api.getActiveSignupCampaign("landing");
  await api.getActiveSignupCampaign("register");

  expect(requests).toEqual([
    { method: "GET", path: "/api/v1/campaigns/signup/active?surface=landing" },
    { method: "GET", path: "/api/v1/campaigns/signup/active?surface=register" },
  ]);
});
