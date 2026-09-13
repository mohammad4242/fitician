import { expect, it } from "vitest";

import {
  billingOfferCodes,
  billingOrderStatuses,
  billingTransactionStatuses,
  paymentProviderCodes,
  type BillingCheckout,
  type BillingOffer,
  type BillingOrder,
  type BillingPaymentResult,
} from "./billing.js";

it("keeps the provider-neutral billing contract stable", () => {
  expect(billingOfferCodes).toHaveLength(18);
  expect(billingOfferCodes).toContain("complete_care_8w");
  expect(billingOrderStatuses).toEqual([
    "created",
    "pending",
    "paid",
    "failed",
    "cancelled",
    "expired",
    "refunded",
  ]);
  expect(billingTransactionStatuses).toContain("verified");
  expect(paymentProviderCodes).toEqual(["fake"]);

  const offer = {
    offer_code: "training_4w",
    package_code: "training",
    duration_weeks: 4,
    price_irr: null,
    currency: null,
    is_available: false,
    entitlements: ["training.plan.generate"],
    quota_policies: [],
  } satisfies BillingOffer;
  const order = {
    id: "order-1",
    offer_code: "training_4w",
    package_code_snapshot: "training",
    duration_weeks_snapshot: 4,
    amount_irr_snapshot: 1_000_000,
    currency_snapshot: "IRR",
    provider: "fake",
    status: "created",
    created_at: "2026-09-13T00:00:00Z",
    updated_at: "2026-09-13T00:00:00Z",
    expires_at: null,
    paid_at: null,
    refunded_at: null,
  } satisfies BillingOrder;
  const checkout = {
    order_id: order.id,
    transaction_id: "transaction-1",
    provider: "fake",
    checkout_kind: "redirect",
    checkout_url: null,
    provider_product_id: null,
    provider_reference: null,
  } satisfies BillingCheckout;
  const result = {
    order_id: order.id,
    transaction_id: checkout.transaction_id,
    transaction_status: "verified",
    order_status: "paid",
    verified: true,
    access_grant_id: "grant-1",
  } satisfies BillingPaymentResult;

  expect(offer.duration_weeks).toBe(4);
  expect(result.verified).toBe(true);
});
