import { expect, it } from "vitest";

import i18n from "../../i18n";
import { ApiError } from "../../shared/apiClient";
import { authErrorMessage } from "./authError";

it("maps an unauthorized API error to a localized message", () => {
  expect(
    authErrorMessage(new ApiError(401, "Invalid email or password"), i18n.t),
  ).toBe("ایمیل یا رمز عبور درست نیست.");
});

it("keeps legacy generic status codes specific to the authentication flow", () => {
  expect(
    authErrorMessage(new ApiError(401, "Invalid OTP", null, "UNAUTHORIZED"), i18n.t, "fa", "otp"),
  ).toBe("کد ورود معتبر نیست یا منقضی شده است.");
  expect(
    authErrorMessage(new ApiError(401, "Google failed", null, "UNAUTHORIZED"), i18n.t, "fa", "google"),
  ).toBe("ورود با گوگل انجام نشد. دوباره تلاش کنید.");
});
