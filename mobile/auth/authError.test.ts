import { expect, it } from "vitest";

import { ApiError } from "@fitician/core";

import { AppleSignInFlowError } from "./appleCredential";
import { authErrorMessage } from "./authError";

it("maps expected authentication failures to Persian user-safe messages", () => {
  expect(authErrorMessage(new ApiError(401, "server detail", null, "AUTH_INVALID_CREDENTIALS"))).toBe(
    "ایمیل یا رمز عبور درست نیست.",
  );
  expect(authErrorMessage(new ApiError(409, "server detail", null, "AUTH_EMAIL_ALREADY_REGISTERED"))).toBe(
    "این ایمیل قبلاً ثبت شده است.",
  );
  expect(authErrorMessage(new ApiError(429, "server detail", null, "AUTH_RATE_LIMITED"))).toBe(
    "درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.",
  );
  expect(authErrorMessage(new ApiError(401, "server detail", null, "AUTH_OTP_INVALID_OR_EXPIRED"), "otp")).toBe(
    "کد ورود معتبر نیست یا منقضی شده است.",
  );
  expect(authErrorMessage(new ApiError(409, "server detail", null, "AUTH_APPLE_ACCOUNT_CONFLICT"), "apple")).toBe(
    "این حساب اپل به حساب دیگری متصل است.",
  );
});

it("preserves safe native Apple flow messages", () => {
  expect(authErrorMessage(new AppleSignInFlowError("ورود با اپل لغو شد."), "apple")).toBe(
    "ورود با اپل لغو شد.",
  );
});

it("does not expose raw server or network errors", () => {
  expect(authErrorMessage(new Error("database password leaked"))).toBe(
    "انجام این عملیات با خطای غیرمنتظره روبه‌رو شد. دوباره تلاش کنید.",
  );
  expect(authErrorMessage(new ApiError(500, "internal details", null, "INTERNAL_SERVER_ERROR"))).toBe(
    "انجام این عملیات با خطای غیرمنتظره روبه‌رو شد. دوباره تلاش کنید.",
  );
});

it("uses context only when a legacy API error has no domain code", () => {
  expect(authErrorMessage(new ApiError(401, "legacy detail"), "otp")).toBe(
    "کد ورود معتبر نیست یا منقضی شده است.",
  );
  expect(authErrorMessage(new ApiError(401, "legacy detail"), "google")).toBe(
    "ورود با گوگل انجام نشد. دوباره تلاش کنید.",
  );
});
