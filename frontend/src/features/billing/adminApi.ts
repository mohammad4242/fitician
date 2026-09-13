import type {
  BillingOffer,
  BillingOrder,
  BillingOrderStatus,
  BillingTransactionStatus,
  PaymentProviderCode,
} from "@fitician/core/billing";

import { request } from "../../shared/apiClient";

const adminBillingPath = "/api/v1/admin/billing";

export type AdminBillingOffer = BillingOffer & {
  readonly is_active: boolean;
  readonly available_from: string | null;
  readonly available_until: string | null;
};

export type UpdateAdminBillingOfferInput = {
  price_irr?: number;
  currency?: string;
  is_active?: boolean;
  available_from?: string | null;
  available_until?: string | null;
};

export type AdminBillingTransaction = {
  readonly id: string;
  readonly order_id: string;
  readonly provider: PaymentProviderCode;
  readonly provider_reference: string | null;
  readonly amount_irr: number;
  readonly currency: string;
  readonly status: BillingTransactionStatus;
  readonly created_at: string;
  readonly verified_at: string | null;
  readonly failed_at: string | null;
  readonly refunded_at: string | null;
};

export type AdminBillingOrder = BillingOrder & {
  readonly user_id: string | null;
  readonly access_grant_id: string | null;
  readonly transactions: readonly AdminBillingTransaction[];
};

export function getAdminBillingOffers(): Promise<AdminBillingOffer[]> {
  return request<AdminBillingOffer[]>(`${adminBillingPath}/offers`);
}

export function updateAdminBillingOffer(
  offerCode: BillingOffer["offer_code"],
  input: UpdateAdminBillingOfferInput,
): Promise<AdminBillingOffer> {
  return request<AdminBillingOffer>(`${adminBillingPath}/offers/${offerCode}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function getAdminBillingOrders(params: {
  status?: BillingOrderStatus;
  provider?: PaymentProviderCode;
  user_id?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<AdminBillingOrder[]> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return request<AdminBillingOrder[]>(
    `${adminBillingPath}/orders${query === "" ? "" : `?${query}`}`,
  );
}

export function getAdminBillingOrder(orderId: string): Promise<AdminBillingOrder> {
  return request<AdminBillingOrder>(`${adminBillingPath}/orders/${orderId}`);
}
