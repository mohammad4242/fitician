import type {
  AccessPackageCode,
  EntitlementCode,
  ProductQuotaPolicy,
} from "./entitlements.js";

export const billingOfferCodes = [
  "training_4w",
  "training_6w",
  "training_8w",
  "training_coach_4w",
  "training_coach_6w",
  "training_coach_8w",
  "nutrition_4w",
  "nutrition_6w",
  "nutrition_8w",
  "nutrition_physician_4w",
  "nutrition_physician_6w",
  "nutrition_physician_8w",
  "complete_4w",
  "complete_6w",
  "complete_8w",
  "complete_care_4w",
  "complete_care_6w",
  "complete_care_8w",
] as const;
export type BillingOfferCode = (typeof billingOfferCodes)[number];

export const billingOrderStatuses = [
  "created",
  "pending",
  "paid",
  "failed",
  "cancelled",
  "expired",
  "refunded",
] as const;
export type BillingOrderStatus = (typeof billingOrderStatuses)[number];

export const billingTransactionStatuses = [
  "created",
  "pending",
  "verified",
  "failed",
  "cancelled",
  "refunded",
] as const;
export type BillingTransactionStatus = (typeof billingTransactionStatuses)[number];

export const paymentProviderCodes = ["fake"] as const;
export type PaymentProviderCode = (typeof paymentProviderCodes)[number];

export type BillingOffer = {
  readonly offer_code: BillingOfferCode;
  readonly package_code: AccessPackageCode;
  readonly duration_weeks: 4 | 6 | 8;
  readonly price_irr: number | null;
  readonly currency: string | null;
  readonly is_available: boolean;
  readonly entitlements: readonly EntitlementCode[];
  readonly quota_policies: readonly ProductQuotaPolicy[];
};

export type BillingOrder = {
  readonly id: string;
  readonly offer_code: BillingOfferCode;
  readonly package_code_snapshot: AccessPackageCode;
  readonly duration_weeks_snapshot: 4 | 6 | 8;
  readonly amount_irr_snapshot: number;
  readonly currency_snapshot: string;
  readonly provider: PaymentProviderCode;
  readonly status: BillingOrderStatus;
  readonly created_at: string;
  readonly updated_at: string;
  readonly expires_at: string | null;
  readonly paid_at: string | null;
  readonly refunded_at: string | null;
};

export type BillingCheckout = {
  readonly order_id: string;
  readonly transaction_id: string;
  readonly provider: PaymentProviderCode;
  readonly checkout_kind: "redirect" | "native";
  readonly checkout_url: string | null;
  readonly provider_product_id: string | null;
  readonly provider_reference: string | null;
};

export type BillingPaymentResult = {
  readonly order_id: string;
  readonly transaction_id: string;
  readonly transaction_status: BillingTransactionStatus;
  readonly order_status: BillingOrderStatus;
  readonly verified: boolean;
  readonly access_grant_id: string | null;
};
