import type {
  EntitlementSnapshot,
  ProductCatalogItem,
} from "@fitician/core/entitlements";

import { request } from "../../shared/apiClient";

export function getProducts(): Promise<ProductCatalogItem[]> {
  return request<ProductCatalogItem[]>("/api/v1/products");
}

export function getEntitlementSnapshot(): Promise<EntitlementSnapshot> {
  return request<EntitlementSnapshot>("/api/v1/entitlements/me");
}
