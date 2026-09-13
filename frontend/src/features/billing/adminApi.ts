import type { BillingOffer } from "@fitician/core/billing";

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
