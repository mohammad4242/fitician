import type { BillingOffer } from "./billing.js";
import type { AccessPackageCode } from "./entitlements.js";

export const billingCategories = ["training", "nutrition", "complete"] as const;
export type BillingCategory = (typeof billingCategories)[number];

export const billingPackageOrder = [
  "training",
  "training_coach",
  "nutrition",
  "nutrition_physician",
  "complete",
  "complete_care",
] as const satisfies readonly AccessPackageCode[];
export type BillingPackageCode = (typeof billingPackageOrder)[number];

export const packagesForBillingCategory = {
  training: ["training", "training_coach"],
  nutrition: ["nutrition", "nutrition_physician"],
  complete: ["complete", "complete_care"],
} as const satisfies Record<BillingCategory, readonly BillingPackageCode[]>;

export const featuredBillingPackages = ["complete", "complete_care"] as const;
export const premiumBillingPackage: BillingPackageCode = "complete_care";

const categoryByPackage = new Map<BillingPackageCode, BillingCategory>(
  billingCategories.flatMap((category) => packagesForBillingCategory[category]
    .map((packageCode) => [packageCode, category] as const)),
);

export function isBillingPackageCode(code: AccessPackageCode): code is BillingPackageCode {
  return billingPackageOrder.includes(code as BillingPackageCode);
}

export function categoryForPackage(code: AccessPackageCode): BillingCategory | null {
  return isBillingPackageCode(code) ? categoryByPackage.get(code) ?? null : null;
}

export function defaultBillingCategory(code: AccessPackageCode | null | undefined): BillingCategory {
  return code ? categoryForPackage(code) ?? "training" : "training";
}

export function groupBillingOffers(
  offers: readonly BillingOffer[],
): ReadonlyMap<BillingPackageCode, readonly BillingOffer[]> {
  const groups = new Map<BillingPackageCode, BillingOffer[]>();
  for (const offer of offers) {
    if (!isBillingPackageCode(offer.package_code)) continue;
    const group = groups.get(offer.package_code) ?? [];
    group.push(offer);
    groups.set(offer.package_code, group);
  }
  return new Map(billingPackageOrder.flatMap((packageCode) => {
    const group = groups.get(packageCode);
    return group
      ? [[packageCode, [...group].sort((a, b) => a.duration_weeks - b.duration_weeks)] as const]
      : [];
  }));
}

export type BodyAnalysisQuotaEstimate = {
  readonly estimatedTotal: number;
  readonly limit: number;
  readonly windowDays: number;
};

export function getBodyAnalysisQuotaEstimate(offer: BillingOffer): BodyAnalysisQuotaEstimate | null {
  const policy = offer.quota_policies.find((item) => item.entitlement === "body_analysis.run");
  if (!policy || policy.limit <= 0 || policy.window_days <= 0) return null;
  return {
    estimatedTotal: Math.floor((offer.duration_weeks * 7) / policy.window_days) * policy.limit,
    limit: policy.limit,
    windowDays: policy.window_days,
  };
}
