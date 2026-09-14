import { expect, it } from "vitest";

import { ApiError } from "@fitician/core";

import {
  accountDeletionError,
  accountDeletionStatusLabel,
  isExactDeletionConfirmation,
} from "./accountDeletionModel";

it("requires the exact destructive confirmation phrase", () => {
  expect(isExactDeletionConfirmation("DELETE")).toBe(true);
  expect(isExactDeletionConfirmation(" delete ")).toBe(false);
  expect(isExactDeletionConfirmation("CANCEL")).toBe(false);
});

it("maps deletion states and reauthentication without exposing server details", () => {
  expect(accountDeletionStatusLabel("pending")).toBe("درخواست حذف در انتظار اجراست");
  expect(accountDeletionError(new ApiError(403, "RECENT_AUTHENTICATION_REQUIRED"))).toEqual({
    message: "برای ادامه، دوباره وارد حساب شوید.",
    requiresReauthentication: true,
  });
  expect(accountDeletionError(new ApiError(500, "internal stack trace"))).toEqual({
    message: "انجام این عملیات با خطای غیرمنتظره روبه‌رو شد. دوباره تلاش کنید.",
    requiresReauthentication: false,
  });
  expect(accountDeletionError(new ApiError(409, "private detail", null, "NO_PENDING_DELETION"))).toEqual({
    message: "درخواست حذف حسابی در انتظار نیست.",
    requiresReauthentication: false,
  });
});
