import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../../shared/apiClient", () => api);

import {
  adminAccessPackageCodes,
  campaignGrantPackageCodes,
  createCampaign,
  getCampaigns,
  updateCampaign,
} from "./adminAccessApi";

beforeEach(() => api.request.mockReset());

it("exposes only normal campaign grant packages", () => {
  expect(campaignGrantPackageCodes).toEqual([
    "training",
    "training_coach",
    "nutrition",
    "nutrition_physician",
    "complete",
    "complete_care",
  ]);
  expect(adminAccessPackageCodes).not.toContain("free");
  expect(adminAccessPackageCodes).not.toContain("launch_trial");
});

it("uses signup_bonus and sends public campaign fields", async () => {
  api.request.mockResolvedValue({ code: "autumn-welcome-1405" });
  const input = {
    code: "autumn-welcome-1405",
    name: "هدیه شروع پاییز",
    kind: "signup_bonus" as const,
    package_code: "complete" as const,
    duration_days: 42,
    term_weeks: 6 as const,
    public_title_fa: "عنوان فارسی",
    public_title_en: "English title",
    public_message_fa: "پیام فارسی",
    public_message_en: "English message",
    public_cta_fa: "شروع",
    public_cta_en: "Start",
    show_on_landing: true,
    show_on_register: true,
  };

  await createCampaign(input);

  expect(api.request).toHaveBeenCalledWith("/api/v1/admin/access/campaigns", {
    method: "POST",
    body: JSON.stringify(input),
  });
});

it("keeps admin campaign reads and edits on the existing access routes", async () => {
  api.request.mockResolvedValue({});

  await getCampaigns();
  await updateCampaign("campaign-1", {
    public_title_fa: "عنوان جدید",
    show_on_landing: false,
  });

  expect(api.request).toHaveBeenNthCalledWith(1, "/api/v1/admin/access/campaigns");
  expect(api.request).toHaveBeenNthCalledWith(2, "/api/v1/admin/access/campaigns/campaign-1", {
    method: "PATCH",
    body: JSON.stringify({ public_title_fa: "عنوان جدید", show_on_landing: false }),
  });
});
