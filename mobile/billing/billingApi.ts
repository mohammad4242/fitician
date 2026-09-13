import type { TransportRequest } from "@fitician/core";
import type {
  BillingCheckout,
  BillingOffer,
  BillingOrder,
  BillingPaymentResult,
  PaymentProviderCode,
} from "@fitician/core/billing";

export type AuthenticatedBillingRequest = <TResponse>(request: TransportRequest) => Promise<TResponse>;

export type CreateBillingOrderInput = {
  readonly offer_code: BillingOffer["offer_code"];
  readonly provider: PaymentProviderCode;
  readonly client_idempotency_key: string;
};

export type CreateBillingCheckoutInput = {
  readonly provider: PaymentProviderCode;
};

export type VerifyBillingPaymentInput = {
  readonly transaction_id: string;
  readonly provider_reference?: string | null;
};

export interface BillingApi {
  createCheckout(orderId: string, input: CreateBillingCheckoutInput): Promise<BillingCheckout>;
  createOrder(input: CreateBillingOrderInput): Promise<BillingOrder>;
  getOffers(): Promise<BillingOffer[]>;
  getOrder(orderId: string): Promise<BillingOrder>;
  getOrders(): Promise<BillingOrder[]>;
  verifyPayment(provider: PaymentProviderCode, input: VerifyBillingPaymentInput): Promise<BillingPaymentResult>;
}

const billingPath = "/api/v1/billing";

function jsonBody(value: object): TransportRequest["body"] {
  return value as TransportRequest["body"];
}

export function createBillingApi(request: AuthenticatedBillingRequest): BillingApi {
  return {
    createCheckout: (orderId, input) => request<BillingCheckout>({
      body: jsonBody(input),
      method: "POST",
      path: `${billingPath}/orders/${orderId}/checkout`,
    }),
    createOrder: (input) => request<BillingOrder>({
      body: jsonBody(input),
      method: "POST",
      path: `${billingPath}/orders`,
    }),
    getOffers: () => request<BillingOffer[]>({
      method: "GET",
      path: `${billingPath}/offers`,
    }),
    getOrder: (orderId) => request<BillingOrder>({
      method: "GET",
      path: `${billingPath}/orders/${orderId}`,
    }),
    getOrders: () => request<BillingOrder[]>({
      method: "GET",
      path: `${billingPath}/orders`,
    }),
    verifyPayment: (provider, input) => request<BillingPaymentResult>({
      body: jsonBody(input),
      method: "POST",
      path: `${billingPath}/providers/${provider}/verify`,
    }),
  };
}
