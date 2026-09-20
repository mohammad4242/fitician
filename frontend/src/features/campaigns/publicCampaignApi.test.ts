import { afterEach, describe, expect, it, vi } from "vitest";

import { getActiveSignupCampaign } from "./publicCampaignApi";

afterEach(() => vi.restoreAllMocks());

describe("public campaign api", () => {
  it("requests the active campaign for each public surface", async () => {
    const campaign = {
      code: "autumn-welcome",
      package_code: "complete",
      duration_days: 42,
      term_weeks: 6,
      available_until: null,
      public_badge_fa: "هدیه ثبت‌نام",
      public_badge_en: "Signup Gift",
      public_title_fa: "برنامه کامل مهمان فیتیشن",
      public_title_en: "Your complete program is on us",
      public_message_fa: "ثبت‌نام کن و شروع کن.",
      public_message_en: "Create your account and start.",
      public_cta_fa: "هدیه‌ام رو بگیر",
      public_cta_en: "Claim my gift",
      show_on_landing: true,
      show_on_register: true,
    };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(campaign))
      .mockResolvedValueOnce(Response.json(null));

    await expect(getActiveSignupCampaign("landing")).resolves.toEqual(campaign);
    await expect(getActiveSignupCampaign("register")).resolves.toBeNull();

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/campaigns/signup/active?surface=landing",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/campaigns/signup/active?surface=register",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
