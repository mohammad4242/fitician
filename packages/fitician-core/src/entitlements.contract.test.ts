import { expect, it } from "vitest";

import {
  accessPackageCodes,
  entitlementCodes,
  type EntitlementSnapshot,
  type ProductCatalogItem,
} from "./entitlements.js";
import en from "./i18n/en.js";
import fa from "./i18n/fa.js";

it("keeps the entitlement contract stable for Web and Mobile", () => {
  expect(accessPackageCodes).toEqual([
    "free",
    "training",
    "training_coach",
    "nutrition",
    "nutrition_physician",
    "complete",
    "complete_care",
    "launch_trial",
  ]);
  expect(entitlementCodes).toContain("body_analysis.run");
  expect(fa.translation.entitlements.packageLabels.launch_trial).toBe("دوره آزمایشی شروع");
  expect(en.translation.entitlements.packageLabels.launch_trial).toBe("Launch Trial");

  const catalogItem = {
    code: "training",
    kind: "subscription",
    is_purchasable: true,
    entitlements: ["training.plan.generate"],
    quota_policies: [],
  } satisfies ProductCatalogItem;
  const snapshot = {
    primary_package: "free",
    active_packages: ["free"],
    trial: { active: false, ends_at: null },
    entitlements: { granted: [], quotas: [] },
    grants: [
      {
        id: "grant-1",
        package_code: "training",
        source: "subscription",
        term_weeks: 6,
        starts_at: "2026-09-13T00:00:00Z",
        ends_at: "2026-10-25T00:00:00Z",
        revoked_at: null,
      },
    ],
  } satisfies EntitlementSnapshot;

  expect(catalogItem.entitlements).toContain("training.plan.generate");
  expect(snapshot.primary_package).toBe("free");
});
