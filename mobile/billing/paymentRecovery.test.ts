import { expect, it, vi } from "vitest";
import { externalBillingAllowed, createPaymentRecovery } from "./paymentRecovery";

it("keeps store builds and iOS closed", () => {
  expect(externalBillingAllowed("android", true, "direct")).toBe(true);
  for (const args of [["ios", true, "direct"], ["android", true, "store"], ["android", false, "direct"]] as const) {
    expect(externalBillingAllowed(args[0], args[1], args[2])).toBe(false);
  }
});

it("reuses a persisted purchase key after app termination", async () => {
  const saved = new Map<string, string>();
  const store = { get: async (key: string) => saved.get(key) ?? null, set: async (key: string, value: string) => { saved.set(key, value); } };
  const api = {
    createOrder: vi.fn().mockResolvedValue({ id: "order-1", provider: "tetrapay" }),
    createCheckout: vi.fn().mockResolvedValue({ order_id: "order-1" }),
    getPendingCheckouts: vi.fn().mockResolvedValue([{provider: "tetrapay", transaction_id: "tx-1", provider_reference: "token"}]),
    verifyPayment: vi.fn().mockResolvedValue({verified: true}),
  };
  await createPaymentRecovery(api as never, store, "user-1").begin("training_4w", "tetrapay");
  await createPaymentRecovery(api as never, store, "user-1").begin("training_4w", "tetrapay");
  expect(api.createOrder.mock.calls[0][0].client_idempotency_key).toBe(api.createOrder.mock.calls[1][0].client_idempotency_key);
  const recovered = await createPaymentRecovery(api as never, store, "user-1").recover();
  expect(recovered[0]?.verified).toBe(true);
  expect(api.verifyPayment).toHaveBeenCalledWith("tetrapay", { transaction_id: "tx-1" });
});
