import type { ReactNode } from "react";

import type { EntitlementCode } from "@fitician/core/entitlements";

import { useEntitlements } from "./EntitlementContext";

type EntitlementGateProps = {
  entitlement: EntitlementCode;
  children: ReactNode;
  fallback?: ReactNode;
  loadingFallback?: ReactNode;
};

export function EntitlementGate({
  entitlement,
  children,
  fallback = null,
  loadingFallback = null,
}: EntitlementGateProps) {
  const { loading, hasEntitlement } = useEntitlements();
  if (loading) return <>{loadingFallback}</>;
  return hasEntitlement(entitlement) ? <>{children}</> : <>{fallback}</>;
}
