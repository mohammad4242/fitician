import { expect, it, vi } from "vitest";

import { createPurchaseService, type PurchaseBillingApi } from "./purchaseService";

it("completes the deterministic fake checkout through server verification", async () => {
  const verifyPayment = vi.fn().mockResolvedValue({
    access_grant_id: "grant-1",
    order_id: "order-1",
    order_status: "paid",
    transaction_id: "transaction-1",
    transaction_status: "verified",
    verified: true,
  });
  const service = createPurchaseService({ verifyPayment } as PurchaseBillingApi);

  const result = await service.completeCheckout({
    checkout_kind: "redirect",
    checkout_url: "/billing/checkout-result?transaction_id=transaction-1",
    order_id: "order-1",
    provider: "fake",
    provider_product_id: null,
    provider_reference: "fake-payment:transaction-1",
    transaction_id: "transaction-1",
  });

  expect(result?.verified).toBe(true);
  expect(verifyPayment).toHaveBeenCalledWith("fake", {
    provider_reference: "fake-payment:transaction-1",
    transaction_id: "transaction-1",
  });
});

it("opens external redirect checkouts without claiming payment locally", async () => {
  const openExternal = vi.fn().mockResolvedValue(undefined);
  const verifyPayment = vi.fn();
  const service = createPurchaseService({ verifyPayment } as PurchaseBillingApi, openExternal);

  const result = await service.completeCheckout({
    checkout_kind: "redirect",
    checkout_url: "https://payments.example/checkout/1",
    order_id: "order-1",
    provider: "fake",
    provider_product_id: null,
    provider_reference: "external-reference",
    transaction_id: "transaction-1",
  });

  expect(result).toBeNull();
  expect(openExternal).toHaveBeenCalledWith("https://payments.example/checkout/1");
  expect(verifyPayment).not.toHaveBeenCalled();
});

it("does not unlock after a failed provider verification", async () => {
  const verifyPayment = vi.fn().mockResolvedValue({
    access_grant_id: null,
    order_id: "order-1",
    order_status: "failed",
    transaction_id: "transaction-1",
    transaction_status: "failed",
    verified: false,
  });
  const service = createPurchaseService({ verifyPayment } as PurchaseBillingApi);

  await expect(service.completeCheckout({
    checkout_kind: "redirect",
    checkout_url: "/billing/checkout-result",
    order_id: "order-1",
    provider: "fake",
    provider_product_id: null,
    provider_reference: "fake-payment:transaction-1",
    transaction_id: "transaction-1",
  })).resolves.toMatchObject({ verified: false });
});
