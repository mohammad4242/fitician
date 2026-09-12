import { afterEach, expect, it, vi } from "vitest";

import { getEntitlementSnapshot, getProducts } from "./api";

afterEach(() => vi.restoreAllMocks());

it("reads the catalog and member entitlement snapshot endpoints", async () => {
  const products = [{
    code: "training" as const,
    kind: "subscription" as const,
    is_purchasable: true,
    entitlements: ["training.plan.generate" as const],
    quota_policies: [],
  }];
  const snapshot = {
    primary_package: "training" as const,
    active_packages: ["training" as const],
    trial: { active: false, ends_at: null },
    entitlements: { granted: ["training.plan.generate" as const], quotas: [] },
    grants: [],
  };
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json(products))
    .mockResolvedValueOnce(Response.json(snapshot));

  await expect(getProducts()).resolves.toEqual(products);
  await expect(getEntitlementSnapshot()).resolves.toEqual(snapshot);

  expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
    "/api/v1/products",
    "/api/v1/entitlements/me",
  ]);
});
