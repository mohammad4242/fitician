import type { AccessPackageCode } from "./entitlements";

export const accessCampaignKinds = [
  "signup_bonus",
  "manual_promotion",
] as const;

export type AccessCampaignKind = (typeof accessCampaignKinds)[number];

export const campaignSurfaces = ["landing", "register"] as const;

export type CampaignSurface = (typeof campaignSurfaces)[number];

export type PublicSignupCampaign = {
  readonly code: string;
  readonly package_code: AccessPackageCode;
  readonly duration_days: number;
  readonly term_weeks: 4 | 6 | 8 | null;
  readonly available_until: string | null;
  readonly public_badge_fa: string | null;
  readonly public_badge_en: string | null;
  readonly public_title_fa: string | null;
  readonly public_title_en: string | null;
  readonly public_message_fa: string | null;
  readonly public_message_en: string | null;
  readonly public_cta_fa: string | null;
  readonly public_cta_en: string | null;
  readonly show_on_landing: boolean;
  readonly show_on_register: boolean;
};
