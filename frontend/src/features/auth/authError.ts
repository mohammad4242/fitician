import type { TFunction } from "i18next";

import type { ErrorLocale } from "@fitician/core";

import { ApiError } from "../../shared/apiClient";
import { webErrorMessage } from "../../shared/appError";

export type AuthErrorContext = "credentials" | "google" | "otp" | "recovery" | "verification";

const GENERIC_API_CODES = new Set([
  "BAD_REQUEST",
  "CONFLICT",
  "RATE_LIMITED",
  "UNAUTHORIZED",
  "VALIDATION_ERROR",
]);

function legacyAuthCode(error: ApiError, context: AuthErrorContext): string | null {
  if (error.code !== null && !GENERIC_API_CODES.has(error.code)) return null;
  if (error.status === 401) {
    if (context === "otp") return "AUTH_OTP_INVALID_OR_EXPIRED";
    if (context === "google") return "AUTH_GOOGLE_FAILED";
    if (context === "verification") return "AUTH_EMAIL_VERIFICATION_INVALID";
    if (context === "recovery") return "AUTH_SESSION_EXPIRED";
    return "AUTH_INVALID_CREDENTIALS";
  }
  if (error.status === 400 && context === "verification") return "AUTH_EMAIL_VERIFICATION_INVALID";
  if (error.status === 409) {
    if (context === "google") return "AUTH_GOOGLE_ACCOUNT_CONFLICT";
    return "AUTH_EMAIL_ALREADY_REGISTERED";
  }
  if (error.status === 429) return "AUTH_RATE_LIMITED";
  return null;
}

export function normalizeAuthError(error: unknown, context: AuthErrorContext): unknown {
  if (!(error instanceof ApiError)) return error;
  const code = legacyAuthCode(error, context);
  if (code === null) return error;
  return new ApiError(error.status, error.message, error.validationDetails, code, {
    meta: error.meta,
    requestId: error.requestId,
    retryable: error.retryable,
  });
}

export function authErrorMessage(
  error: unknown,
  t: TFunction,
  locale: ErrorLocale = "fa",
  context: AuthErrorContext = "credentials",
): string {
  if (error instanceof ApiError) {
    return webErrorMessage(normalizeAuthError(error, context), t("errors.generic"), {
      audience: "member",
      context: "auth",
      locale,
    });
  }
  return webErrorMessage(error, t("errors.generic"), {
    audience: "member",
    context: "auth",
    locale,
  });
}
