import { expect, it } from "vitest";

import {
  accessCampaignKinds,
  campaignSurfaces,
  type PublicSignupCampaign,
} from "./campaigns";

it("keeps the public campaign kind and surface contracts stable", () => {
  expect(accessCampaignKinds).toEqual(["signup_bonus", "manual_promotion"]);
  expect(campaignSurfaces).toEqual(["landing", "register"]);

  const campaign = {
    code: "autumn_welcome_1405",
    package_code: "complete",
    duration_days: 42,
    term_weeks: 6,
    available_until: null,
    public_badge_fa: null,
    public_badge_en: null,
    public_title_fa: "عنوان",
    public_title_en: "Title",
    public_message_fa: "پیام",
    public_message_en: "Message",
    public_cta_fa: "شروع",
    public_cta_en: "Start",
    show_on_landing: true,
    show_on_register: true,
  } satisfies PublicSignupCampaign;

  expect(campaign.package_code).toBe("complete");
});
