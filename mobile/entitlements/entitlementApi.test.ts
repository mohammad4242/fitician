import { expect, it } from "vitest";

import type { TransportRequest } from "@fitician/core";

import { createEntitlementApi } from "./entitlementApi";

it("uses the shared product and member entitlement endpoints", async () => {
  const requests: TransportRequest[] = [];
  const api = createEntitlementApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return {} as TResponse;
  });

  await api.getProducts();
  await api.getSnapshot();

  expect(requests).toEqual([
    { method: "GET", path: "/api/v1/products" },
    { method: "GET", path: "/api/v1/entitlements/me" },
  ]);
});
