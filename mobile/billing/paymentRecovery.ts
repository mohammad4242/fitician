import type { BillingOfferCode, PaymentProviderCode } from "@fitician/core/billing";
import type { BillingApi } from "./billingApi";

export function externalBillingAllowed(platform: string, enabled: boolean, distribution: string): boolean {
  return platform === "android" && enabled && distribution === "direct";
}

export interface PurchaseKeyStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

export function createPaymentRecovery(api: BillingApi, store: PurchaseKeyStore, userId: string) {
  return {
    async begin(offer: BillingOfferCode, provider: PaymentProviderCode) {
      const key = `billing-${userId}-${offer}`;
      let attempt = await store.get(key);
      if (!attempt) {
        attempt = `mobile-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        // Save BEFORE creating the order so process death never loses its identity.
        await store.set(key, attempt);
      }
      const order = await api.createOrder({ offer_code: offer, provider, client_idempotency_key: attempt });
      if (["paid", "refunded", "cancelled", "expired", "failed"].includes(order.status)) {
        await store.set(key, "");
        // A new purchase requires another explicit tap after seeing current state.
        throw new Error("حالت خرید قبلی ثبت شده؛ وضعیت اشتراک را بررسی و دوباره تلاش کنید");
      }
      return api.createCheckout(order.id, { provider: order.provider });
    },
    async recover() {
      const pending = await api.getPendingCheckouts();
      const results = [];
      for (const checkout of pending.slice(0, 3)) {
        if (checkout.provider_reference === null) continue;
        results.push(await api.verifyPayment(checkout.provider, { transaction_id: checkout.transaction_id }));
      }
      return results;
    },
  };
}
