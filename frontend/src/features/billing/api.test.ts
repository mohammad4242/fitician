import { afterEach, expect, it, vi } from "vitest";

import {
  createCheckout,
  createOrder,
  getOffers,
  getOrder,
  getOrders,
  verifyPayment,
} from "./api";

afterEach(() => vi.restoreAllMocks());

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
}

it("loads commercial offers through the shared web transport", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResponse([]));

  await getOffers();

  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/billing/offers",
    expect.objectContaining({ credentials: "include" }),
  );
});

it("creates orders without accepting a client price", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResponse({ id: "order-1" }));

  await createOrder({
    offer_code: "training_4w",
    provider: "fake",
    client_idempotency_key: "attempt-1",
  });

  const [, init] = vi.mocked(fetch).mock.calls[0] ?? [];
  expect(JSON.parse(String(init?.body))).toEqual({
    offer_code: "training_4w",
    provider: "fake",
    client_idempotency_key: "attempt-1",
  });
  expect(String(init?.body)).not.toContain("amount_irr");
});

it("uses the shared API for checkout, verification, and history", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(jsonResponse({ id: "order-1" }))
    .mockResolvedValueOnce(jsonResponse({ order_id: "order-1" }))
    .mockResolvedValueOnce(jsonResponse({ order_id: "order-1", verified: true }))
    .mockResolvedValueOnce(jsonResponse([]))
    .mockResolvedValueOnce(jsonResponse({ id: "order-1" }));

  await createCheckout("order-1", "fake");
  await verifyPayment("fake", { transaction_id: "tx-1", provider_reference: "ref-1" });
  await getOrders();
  await getOrder("order-1");

  expect(fetch).toHaveBeenNthCalledWith(
    1,
    "/api/v1/billing/orders/order-1/checkout",
    expect.objectContaining({ method: "POST" }),
  );
  expect(fetch).toHaveBeenNthCalledWith(
    2,
    "/api/v1/billing/providers/fake/verify",
    expect.objectContaining({ method: "POST" }),
  );
  expect(fetch).toHaveBeenNthCalledWith(3, "/api/v1/billing/orders", expect.anything());
  expect(fetch).toHaveBeenNthCalledWith(4, "/api/v1/billing/orders/order-1", expect.anything());
});
