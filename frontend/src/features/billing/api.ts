import type {
  BillingCheckout,
  BillingOffer,
  BillingOrder,
  BillingPaymentResult,
  PaymentProviderCode,
} from "@fitician/core/billing";

import { request } from "../../shared/apiClient";

const billingPath = "/api/v1/billing";

export type CreateOrderInput = {
  offer_code: BillingOffer["offer_code"];
  provider: PaymentProviderCode;
  client_idempotency_key: string;
};

export type VerifyPaymentInput = {
  transaction_id: string;
  provider_reference?: string | null;
};

export type CreateCheckoutInput = {
  provider: PaymentProviderCode;
};

export function getOffers(): Promise<BillingOffer[]> {
  return request<BillingOffer[]>(`${billingPath}/offers`);
}

export function createOrder(input: CreateOrderInput): Promise<BillingOrder> {
  return request<BillingOrder>(`${billingPath}/orders`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createCheckout(
  orderId: string,
  input: CreateCheckoutInput,
): Promise<BillingCheckout> {
  return request<BillingCheckout>(`${billingPath}/orders/${orderId}/checkout`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getOrders(): Promise<BillingOrder[]> {
  return request<BillingOrder[]>(`${billingPath}/orders`);
}

export function getOrder(orderId: string): Promise<BillingOrder> {
  return request<BillingOrder>(`${billingPath}/orders/${orderId}`);
}

export function verifyPayment(
  provider: PaymentProviderCode,
  input: VerifyPaymentInput,
): Promise<BillingPaymentResult> {
  return request<BillingPaymentResult>(`${billingPath}/providers/${provider}/verify`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
