import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

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
  fallback,
  loadingFallback = null,
}: EntitlementGateProps) {
  const { t } = useTranslation();
  const { loading, hasEntitlement } = useEntitlements();
  if (loading) return <>{loadingFallback}</>;
  if (hasEntitlement(entitlement)) return <>{children}</>;
  const missingFallback = fallback === undefined
    ? <Link to={`/plans?required=${encodeURIComponent(entitlement)}`}>{t("billing.viewPlans")}</Link>
    : fallback;
  return <>{missingFallback}</>;
}
