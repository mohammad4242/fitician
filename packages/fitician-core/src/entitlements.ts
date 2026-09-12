export const accessPackageCodes = [
  "free",
  "training",
  "training_coach",
  "nutrition",
  "nutrition_physician",
  "complete",
  "complete_care",
  "launch_trial",
] as const;
export type AccessPackageCode = (typeof accessPackageCodes)[number];

export const accessPackageKinds = ["free", "subscription", "trial"] as const;
export type AccessPackageKind = (typeof accessPackageKinds)[number];

export const grantSources = [
  "launch_trial",
  "manual",
  "promotion",
  "subscription",
  "admin",
] as const;
export type GrantSource = (typeof grantSources)[number];

export const entitlementCodes = [
  "training.plan.generate",
  "training.cycle.manage",
  "training.coach_review",
  "nutrition.plan.generate",
  "nutrition.plan.manage",
  "nutrition.food_photo.analyze",
  "nutrition.physician_review",
  "nutrition.labs.manage",
  "nutrition.supplements.manage",
  "body_analysis.run",
] as const;
export type EntitlementCode = (typeof entitlementCodes)[number];

export type ProductQuotaPolicy = {
  readonly entitlement: EntitlementCode;
  readonly limit: number;
  readonly window_days: number;
};

export type ProductCatalogItem = {
  readonly code: AccessPackageCode;
  readonly kind: AccessPackageKind;
  readonly is_purchasable: boolean;
  readonly entitlements: readonly EntitlementCode[];
  readonly quota_policies: readonly ProductQuotaPolicy[];
};

export type QuotaStatus = {
  readonly entitlement: EntitlementCode;
  readonly limit: number;
  readonly used: number;
  readonly remaining: number;
  readonly window_days: number;
  readonly reset_at: string;
};

export type EntitlementState = {
  readonly granted: readonly EntitlementCode[];
  readonly quotas: readonly QuotaStatus[];
};

export type AccessGrantSummary = {
  readonly id: string;
  readonly package_code: AccessPackageCode;
  readonly source: GrantSource;
  readonly starts_at: string;
  readonly ends_at: string | null;
  readonly revoked_at: string | null;
};

export type EntitlementSnapshot = {
  readonly primary_package: AccessPackageCode;
  readonly active_packages: readonly AccessPackageCode[];
  readonly trial: {
    readonly active: boolean;
    readonly ends_at: string | null;
  };
  readonly entitlements: EntitlementState;
  readonly grants: readonly AccessGrantSummary[];
};
