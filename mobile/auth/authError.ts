import { ApiError, resolveAppError } from "@fitician/core";

import { AppleSignInFlowError } from "./appleCredential";
import { GoogleSignInFlowError } from "./googleCredential";

export type AuthErrorContext = "apple" | "credentials" | "google" | "otp" | "recovery";

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
    if (context === "apple") return "AUTH_APPLE_FAILED";
    if (context === "recovery") return "AUTH_SESSION_EXPIRED";
    return "AUTH_INVALID_CREDENTIALS";
  }
  if (error.status === 409) {
    if (context === "apple") return "AUTH_APPLE_ACCOUNT_CONFLICT";
    if (context === "google") return "AUTH_GOOGLE_ACCOUNT_CONFLICT";
    return "AUTH_EMAIL_ALREADY_REGISTERED";
  }
  if (error.status === 429) return "AUTH_RATE_LIMITED";
  return null;
}

export function authErrorMessage(
  error: unknown,
  context: AuthErrorContext = "credentials",
): string {
  if (error instanceof GoogleSignInFlowError) return error.message;
  if (error instanceof AppleSignInFlowError) return error.message;
  if (error instanceof ApiError) {
    const code = legacyAuthCode(error, context);
    const resolvedError = code === null
      ? error
      : new ApiError(error.status, error.message, error.validationDetails, code, {
          meta: error.meta,
          requestId: error.requestId,
          retryable: error.retryable,
        });
    return resolveAppError(resolvedError, {
      audience: "member",
      context: "auth",
      locale: "fa",
    }).message;
  }
  return resolveAppError(error, {
    audience: "member",
    context: "auth",
    locale: "fa",
  }).message;
}
