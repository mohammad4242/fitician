import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { EntitlementCode } from "@fitician/core/entitlements";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
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
  const { i18n, t } = useTranslation();
  const { error, loading, retry, hasEntitlement } = useEntitlements();
  if (loading) return <>{loadingFallback}</>;
  if (error !== null && error !== undefined) {
    return (
      <AppErrorNotice
        audience="member"
        context="access"
        error={error}
        locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        onRetry={retry}
      />
    );
  }
  if (hasEntitlement(entitlement)) return <>{children}</>;
  const missingFallback = fallback === undefined
    ? <Link to={`/plans?required=${encodeURIComponent(entitlement)}`}>{t("billing.viewPlans")}</Link>
    : fallback;
  return <>{missingFallback}</>;
}
