import { expect, it } from "vitest";

import type { TransportRequest } from "@fitician/core";

import { createBillingApi } from "./billingApi";

it("uses authenticated transport for offers, orders, checkout, and verification", async () => {
  const requests: TransportRequest[] = [];
  const api = createBillingApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return {} as TResponse;
  });

  await api.getOffers();
  await api.createOrder({
    client_idempotency_key: "mobile-attempt-1",
    offer_code: "training_4w",
    provider: "fake",
  });
  await api.createCheckout("order-1", { provider: "fake" });
  await api.getOrders();
  await api.getOrder("order-1");
  await api.verifyPayment("fake", { provider_reference: "fake-payment:tx-1", transaction_id: "tx-1" });

  expect(requests).toEqual([
    { method: "GET", path: "/api/v1/billing/offers" },
    {
      body: { client_idempotency_key: "mobile-attempt-1", offer_code: "training_4w", provider: "fake" },
      method: "POST",
      path: "/api/v1/billing/orders",
    },
    {
      body: { provider: "fake" },
      method: "POST",
      path: "/api/v1/billing/orders/order-1/checkout",
    },
    { method: "GET", path: "/api/v1/billing/orders" },
    { method: "GET", path: "/api/v1/billing/orders/order-1" },
    {
      body: { provider_reference: "fake-payment:tx-1", transaction_id: "tx-1" },
      method: "POST",
      path: "/api/v1/billing/providers/fake/verify",
    },
  ]);
});
