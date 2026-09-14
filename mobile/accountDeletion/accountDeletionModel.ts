import { ApiError, formatTehranDateTime, resolveAppError } from "@fitician/core";

import type { AccountDeletionStatus } from "./accountDeletionApi";

export interface AccountDeletionErrorMessage {
  readonly message: string;
  readonly requiresReauthentication: boolean;
}

export function isExactDeletionConfirmation(value: string): boolean {
  return value === "DELETE";
}

export function accountDeletionStatusLabel(status: AccountDeletionStatus): string {
  if (status === "none") return "درخواستی برای حذف ثبت نشده است";
  if (status === "pending") return "درخواست حذف در انتظار اجراست";
  if (status === "cancelled") return "درخواست حذف لغو شده است";
  return "حذف حساب تکمیل شده است";
}

export function accountDeletionError(error: unknown): AccountDeletionErrorMessage {
  const code = error instanceof ApiError ? error.code : null;
  const message = error instanceof Error ? error.message : "";
  const legacyCode = code === null && (
    message === "RECENT_AUTHENTICATION_REQUIRED"
    || message === "INVALID_REAUTHENTICATION"
    || message === "GRACE_PERIOD_EXPIRED"
  ) ? message : null;
  const resolvedError = error instanceof ApiError && legacyCode !== null
    ? new ApiError(error.status, error.message, error.validationDetails, legacyCode, {
        meta: error.meta,
        requestId: error.requestId,
        retryable: error.retryable,
      })
    : error;
  return {
    message: resolveAppError(resolvedError, {
      audience: "member",
      context: "access",
      locale: "fa",
    }).message,
    requiresReauthentication: (code ?? legacyCode) === "RECENT_AUTHENTICATION_REQUIRED",
  };
}

export function formatDeletionDate(value: string | null): string {
  if (value === null) return "زمان نامشخص";
  try {
    return formatTehranDateTime(value);
  } catch {
    return "زمان نامشخص";
  }
}
