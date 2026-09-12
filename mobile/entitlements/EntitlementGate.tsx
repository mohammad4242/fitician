import type { ReactNode } from "react";
import { Text, View } from "react-native";

import type { EntitlementCode } from "@fitician/core/entitlements";

import { Notice, Skeleton } from "../ui/components";
import { useMobileEntitlements } from "./EntitlementProvider";

export interface EntitlementGateProps {
  readonly children: ReactNode;
  readonly entitlement: EntitlementCode;
  readonly fallback?: ReactNode;
  readonly loadingFallback?: ReactNode;
}

export function EntitlementGate({
  children,
  entitlement,
  fallback,
  loadingFallback,
}: EntitlementGateProps) {
  const { hasEntitlement, loading, snapshot } = useMobileEntitlements();
  if (loading && snapshot === null) {
    return loadingFallback ?? <Skeleton accessibilityLabel="در حال بررسی دسترسی" height={36} />;
  }
  if (hasEntitlement(entitlement)) return <>{children}</>;
  return fallback ?? (
    <Notice
      message="برای استفاده از این عملیات، دسترسی فعال لازم است."
      title="این عملیات در دسترس نیست"
      variant="warning"
    />
  );
}

export function EntitlementLoadingState() {
  return (
    <View>
      <Text accessibilityRole="text">در حال بررسی دسترسی…</Text>
    </View>
  );
}
