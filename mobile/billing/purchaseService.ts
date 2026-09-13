import type {
  BillingCheckout,
  BillingPaymentResult,
} from "@fitician/core/billing";

import type { BillingApi } from "./billingApi";

export type PurchaseBillingApi = Pick<BillingApi, "verifyPayment">;
export type ExternalCheckoutOpener = (url: string) => Promise<unknown>;

export interface PurchaseService {
  completeCheckout(checkout: BillingCheckout): Promise<BillingPaymentResult | null>;
}

export function createPurchaseService(
  api: PurchaseBillingApi,
  openExternal?: ExternalCheckoutOpener,
): PurchaseService {
  return {
    async completeCheckout(checkout) {
      if (checkout.checkout_kind === "native") return null;
      if (checkout.checkout_url?.match(/^https?:\/\//i)) {
        if (openExternal === undefined) throw new Error("An external checkout opener is required");
        await openExternal(checkout.checkout_url);
        return null;
      }
      if (checkout.provider !== "fake" || checkout.provider_reference === null) {
        throw new Error("A local checkout requires a normalized provider reference");
      }
      return api.verifyPayment(checkout.provider, {
        provider_reference: checkout.provider_reference,
        transaction_id: checkout.transaction_id,
      });
    },
  };
}
