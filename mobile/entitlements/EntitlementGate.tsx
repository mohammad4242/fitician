import type { ReactNode } from "react";
import { Text, View } from "react-native";

import {
  resolveAppError,
  type ErrorAudienceInput,
  type ErrorContext,
  type ErrorLocale,
} from "@fitician/core";
import type { EntitlementCode } from "@fitician/core/entitlements";

import { Notice, Skeleton } from "../ui/components";
import { useMobileEntitlements } from "./EntitlementProvider";

export interface EntitlementGateProps {
  readonly children: ReactNode;
  readonly entitlement: EntitlementCode;
  readonly fallback?: ReactNode;
  readonly loadingFallback?: ReactNode;
  readonly audience?: ErrorAudienceInput;
  readonly context?: ErrorContext;
  readonly locale?: ErrorLocale;
}

export function EntitlementGate({
  children,
  entitlement,
  fallback,
  loadingFallback,
  audience = "member",
  context = "access",
  locale = "fa",
}: EntitlementGateProps) {
  const { error, hasEntitlement, loading, retry, snapshot } = useMobileEntitlements();
  if (loading && snapshot === null) {
    return loadingFallback ?? <Skeleton accessibilityLabel="در حال بررسی دسترسی" height={36} />;
  }
  if (error !== null) {
    const resolved = resolveAppError(error, { audience, context, locale });
    return (
      <Notice
        actionLabel={resolved.action ?? (locale === "fa" ? "تلاش دوباره" : "Try again")}
        message={resolved.message}
        onAction={retry}
        technicalDetails={resolved}
        title={resolved.title}
        variant={resolved.severity === "warning" ? "warning" : "danger"}
      />
    );
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
