import { describe, expect, it } from "vitest";

import type { BillingOffer } from "./billing.js";
import en from "./i18n/en.js";
import fa from "./i18n/fa.js";
import {
  billingPackageOrder,
  categoryForPackage,
  defaultBillingCategory,
  getBodyAnalysisQuotaEstimate,
  groupBillingOffers,
  packagesForBillingCategory,
} from "./billingPresentation.js";

const offer = (
  packageCode: BillingOffer["package_code"],
  durationWeeks: BillingOffer["duration_weeks"],
): BillingOffer => ({
  currency: "IRR",
  duration_weeks: durationWeeks,
  entitlements: ["body_analysis.run"],
  is_available: true,
  offer_code: `${packageCode}_${durationWeeks}w` as BillingOffer["offer_code"],
  package_code: packageCode,
  price_irr: durationWeeks * 100_000,
  quota_policies: [{ entitlement: "body_analysis.run", limit: 1, window_days: 7 }],
});

describe("billing presentation", () => {
  it("defines the six packages in pricing order and category pairs", () => {
    expect(billingPackageOrder).toEqual([
      "training",
      "training_coach",
      "nutrition",
      "nutrition_physician",
      "complete",
      "complete_care",
    ]);
    expect(packagesForBillingCategory.training).toEqual(["training", "training_coach"]);
    expect(packagesForBillingCategory.nutrition).toEqual(["nutrition", "nutrition_physician"]);
    expect(packagesForBillingCategory.complete).toEqual(["complete", "complete_care"]);
  });

  it("groups offers by package and sorts each package by duration", () => {
    const grouped = groupBillingOffers([
      offer("complete_care", 8),
      offer("training", 6),
      offer("training", 4),
    ]);

    expect([...grouped.keys()]).toEqual(["training", "complete_care"]);
    expect(grouped.get("training")?.map((item) => item.duration_weeks)).toEqual([4, 6]);
  });

  it("resolves the default category from the current package with training fallback", () => {
    expect(categoryForPackage("nutrition_physician")).toBe("nutrition");
    expect(defaultBillingCategory("complete_care")).toBe("complete");
    expect(defaultBillingCategory("launch_trial")).toBe("training");
  });

  it("estimates body analysis usage from the selected offer quota policy", () => {
    expect(getBodyAnalysisQuotaEstimate(offer("training", 6))).toEqual({
      estimatedTotal: 6,
      limit: 1,
      windowDays: 7,
    });
    expect(getBodyAnalysisQuotaEstimate({ ...offer("training", 8), quota_policies: [] })).toBeNull();
    expect(getBodyAnalysisQuotaEstimate({
      ...offer("training", 8),
      quota_policies: [{ entitlement: "body_analysis.run", limit: 2, window_days: 14 }],
    })).toEqual({ estimatedTotal: 8, limit: 2, windowDays: 14 });
  });

  it("keeps Persian and English presentation content complete for every package", () => {
    const keys = ["training", "trainingCoach", "nutrition", "nutritionPhysician", "complete", "completeCare"] as const;
    for (const key of keys) {
      expect(fa.translation.billing.packageDetails[key].name).not.toBe("");
      expect(en.translation.billing.packageDetails[key].name).not.toBe("");
      expect(fa.translation.billing.packageDetails[key].features.length).toBeGreaterThanOrEqual(7);
      expect(en.translation.billing.packageDetails[key].features.length).toBe(fa.translation.billing.packageDetails[key].features.length);
    }
  });
});
