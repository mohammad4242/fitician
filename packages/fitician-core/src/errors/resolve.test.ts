import { describe, expect, it } from "vitest";

import {
  ApiError,
  TransportError,
  parseApiErrorPayload,
} from "../transport";
import { resolveAppError } from "./resolve";

describe("resolveAppError", () => {
  it("uses the domain code before HTTP status for member presentation", () => {
    const result = resolveAppError(
      new ApiError(403, "internal entitlement detail", null, "ENTITLEMENT_REQUIRED", {
        meta: { entitlement: "training_plan_generate" },
      }),
      { audience: "member", context: "workout_generation", locale: "fa" },
    );

    expect(result.message).toContain("دسترسی لازم");
    expect(result.message).not.toContain("internal entitlement detail");
    expect(result.status).toBe(403);
    expect(result.code).toBe("ENTITLEMENT_REQUIRED");
    expect(result.meta).toEqual({ entitlement: "training_plan_generate" });
  });

  it("shows safe diagnostics to admins without exposing raw provider text", () => {
    const result = resolveAppError(
      new ApiError(503, "provider secret and stack trace", null, "BODY_ANALYSIS_PROVIDER_UNAVAILABLE", {
        retryable: true,
        meta: { current_state: "queued" },
        requestId: "corr-admin-1",
      }),
      { audience: "admin", context: "body_analysis", locale: "en" },
    );

    expect(result.message).toContain("provider");
    expect(result.message).not.toContain("provider secret");
    expect(result.code).toBe("BODY_ANALYSIS_PROVIDER_UNAVAILABLE");
    expect(result.status).toBe(503);
    expect(result.requestId).toBe("corr-admin-1");
    expect(result.retryable).toBe(true);
    expect(result.showTechnicalDetails).toBe(true);
  });

  it("normalizes doctor audience to physician workflow language", () => {
    const result = resolveAppError(
      new ApiError(404, "missing safety decision", null, "SAFETY_DECISION_NOT_FOUND"),
      { audience: "doctor", context: "specialist_review", locale: "fa" },
    );

    expect(result.message).toBe(
      "بررسی این برنامه ممکن نیست چون ارزیابی ایمنی کاربر هنوز ثبت نشده است.",
    );
  });

  it("keeps coach and physician workflow causes distinct from generic permission errors", () => {
    const coach = resolveAppError(
      new ApiError(403, "forbidden", null, "COACH_ROLE_REQUIRED"),
      { audience: "coach", context: "specialist_review", locale: "fa" },
    );
    const physician = resolveAppError(
      new ApiError(403, "forbidden", null, "SPECIALIST_RELATIONSHIP_REQUIRED"),
      { audience: "physician", context: "specialist_review", locale: "fa" },
    );

    expect(coach.message).toContain("مربی");
    expect(physician.message).toContain("پرونده");
    expect(physician.message).not.toContain("مربی");
  });

  it("resolves nutrition plan edit codes from the shared catalog", () => {
    const result = resolveAppError(
      new ApiError(409, "raw edit detail", null, "MEAL_LOCKED"),
      { audience: "member", context: "nutrition", locale: "fa" },
    );

    expect(result.message).toContain("این وعده قفل است");
    expect(result.message).not.toContain("raw edit detail");
  });

  it.each([
    ["ACTIVE_PLAN_REQUIRED", "برنامه تأییدشده و فعال"],
    ["STRICT_BUDGET_EXCEEDED", "بودجه غذایی تعیین‌شده"],
    ["PROTEIN_MINIMUM_EXCEEDS_CALORIE_BUDGET", "حداقل پروتئین"],
  ])("resolves nutrition workflow code %s from the shared catalog", (code, expected) => {
    const result = resolveAppError(
      new ApiError(422, "raw nutrition detail", null, code),
      { audience: "member", context: "nutrition", locale: "fa" },
    );

    expect(result.message).toContain(expected);
    expect(result.message).not.toContain("raw nutrition detail");
  });

  it("turns validation details into localized field errors", () => {
    const result = resolveAppError(
      new ApiError(
        422,
        "validation failed",
        [{ loc: ["body", "weight_kg"], type: "missing", msg: "Field required" }],
        "VALIDATION_ERROR",
      ),
      { audience: "member", context: "profile", locale: "fa" },
    );

    expect(result.fieldErrors).toEqual([
      expect.objectContaining({
        field: "weight_kg",
        message: "وزن وارد نشده است.",
      }),
    ]);
    expect(result.message).toContain("وزن");
  });

  it("keeps authentication status fallbacks code-specific", () => {
    expect(resolveAppError(
      new ApiError(401, "raw auth detail"),
      { audience: "member", context: "auth", locale: "fa" },
    )).toMatchObject({ code: "AUTH_INVALID_CREDENTIALS", message: "ایمیل یا رمز عبور درست نیست." });
    expect(resolveAppError(
      new ApiError(409, "raw duplicate detail"),
      { audience: "member", context: "auth", locale: "fa" },
    )).toMatchObject({ code: "AUTH_EMAIL_ALREADY_REGISTERED", message: "این ایمیل قبلاً ثبت شده است." });
  });

  it("redacts raw validation messages for admins too", () => {
    const result = resolveAppError(
      new ApiError(
        422,
        "validation failed",
        [{ field: "email", code: "invalid", message: "private note token=secret" }],
        "VALIDATION_ERROR",
      ),
      { audience: "admin", context: "profile", locale: "fa" },
    );

    expect(result.fieldErrors[0]?.message).toBe("ایمیل معتبر نیست.");
    expect(result.fieldErrors[0]?.message).not.toContain("secret");
  });

  it.each([
    [400, "درخواست معتبر نیست"],
    [401, "نشست"],
    [403, "دسترسی"],
    [404, "پیدا نشد"],
    [409, "وضعیت"],
    [422, "اطلاعات"],
    [429, "درخواست‌های زیادی"],
    [500, "غیرمنتظره"],
    [502, "سرویس"],
    [503, "موقتاً"],
  ])("has a safe fallback for HTTP %s", (status, expected) => {
    const result = resolveAppError(
      new ApiError(status, "raw SQL password=secret stack trace"),
      { audience: "member", context: "generic", locale: "fa" },
    );

    expect(result.message).toContain(expected);
    expect(result.message).not.toContain("secret");
    expect(result.message).not.toContain("stack");
  });

  it("separates offline, timeout, abort, and unknown runtime errors", () => {
    expect(
      resolveAppError(new TransportError("offline"), {
        audience: "member",
        context: "generic",
        locale: "fa",
      }),
    ).toMatchObject({ code: "OFFLINE", severity: "warning", retryable: true });
    expect(
      resolveAppError(new TransportError("timeout"), {
        audience: "member",
        context: "generic",
        locale: "fa",
      }),
    ).toMatchObject({ code: "REQUEST_TIMEOUT", severity: "warning", retryable: true });
    expect(
      resolveAppError(new TransportError("aborted"), {
        audience: "member",
        context: "generic",
        locale: "fa",
      }),
    ).toMatchObject({ code: "REQUEST_ABORTED", severity: "silent", retryable: false });
    expect(
      resolveAppError(new Error("database password leaked"), {
        audience: "member",
        context: "generic",
        locale: "fa",
      }),
    ).toMatchObject({ code: "UNKNOWN_ERROR", severity: "error" });
  });
});

describe("parseApiErrorPayload", () => {
  it("parses structured detail, fields, metadata, retryability, and request ID", () => {
    const error = parseApiErrorPayload(
      429,
      {
        detail: {
          code: "ENTITLEMENT_QUOTA_EXCEEDED",
          message: "Quota reached",
          retryable: true,
          fields: [{ field: "training_days", code: "range", message: "Invalid" }],
          meta: { retry_after_seconds: 30, reset_at: "2026-09-14T12:00:00Z" },
          request_id: "corr-structured-1",
        },
      },
    );

    expect(error).toMatchObject({
      code: "ENTITLEMENT_QUOTA_EXCEEDED",
      message: "Quota reached",
      retryable: true,
      requestId: "corr-structured-1",
      meta: { retry_after_seconds: 30, reset_at: "2026-09-14T12:00:00Z" },
      validationDetails: [{ field: "training_days", code: "range", message: "Invalid" }],
    });
    expect(error.details).toBe(error.validationDetails);
  });

  it("parses legacy string, validation array, and non-json payloads safely", () => {
    expect(parseApiErrorPayload(400, { detail: "Bad request" })).toMatchObject({
      status: 400,
      message: "Bad request",
    });
    expect(parseApiErrorPayload(422, { detail: [{ loc: ["body", "height_cm"], type: "missing" }] })).toMatchObject({
      code: "VALIDATION_ERROR",
      validationDetails: [{ loc: ["body", "height_cm"], type: "missing" }],
    });
    expect(parseApiErrorPayload(500, "<html>database password=secret</html>")).toMatchObject({
      code: "INTERNAL_SERVER_ERROR",
      message: "The request could not be completed.",
      meta: {},
    });
  });
});
