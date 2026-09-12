import type { TransportRequest } from "@fitician/core";
import type {
  EntitlementSnapshot,
  ProductCatalogItem,
} from "@fitician/core/entitlements";

export type AuthenticatedEntitlementRequest = <TResponse>(
  request: TransportRequest,
) => Promise<TResponse>;

export interface EntitlementApi {
  getProducts(): Promise<ProductCatalogItem[]>;
  getSnapshot(): Promise<EntitlementSnapshot>;
}

export function createEntitlementApi(request: AuthenticatedEntitlementRequest): EntitlementApi {
  return {
    getProducts: () => request<ProductCatalogItem[]>({
      method: "GET",
      path: "/api/v1/products",
    }),
    getSnapshot: () => request<EntitlementSnapshot>({
      method: "GET",
      path: "/api/v1/entitlements/me",
    }),
  };
}
