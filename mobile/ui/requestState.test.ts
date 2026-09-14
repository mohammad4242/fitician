import { expect, it } from "vitest";

import { ApiError, TransportError } from "@fitician/core";

import {
  classifyMobileStateError,
  getMobileViewState,
  mobileRequestErrorMessage,
  type MobileQueryResult,
} from "./requestState";

function result<TData>(overrides: Partial<MobileQueryResult<TData>> = {}): MobileQueryResult<TData> {
  return {
    data: undefined,
    error: null,
    isError: false,
    isFetching: false,
    isPending: true,
    isStale: false,
    ...overrides,
  };
}

it("normalizes loading, empty, ready, and stale query states", () => {
  expect(getMobileViewState(result())).toEqual({ status: "loading" });
  expect(
    getMobileViewState(result({ data: [], isPending: false }), { isEmpty: (data) => data.length === 0 }),
  ).toEqual({ data: [], isStale: false, status: "empty" });
  expect(getMobileViewState(result({ data: ["plan"], isPending: false }))).toEqual({
    data: ["plan"],
    status: "ready",
  });
  expect(
    getMobileViewState(result({ data: ["plan"], isFetching: true, isPending: false })),
  ).toEqual({ data: ["plan"], status: "stale" });
});

it("keeps offline state explicit with or without cached data", () => {
  expect(
    getMobileViewState(result(), { connectivityStatus: "offline" }),
  ).toEqual({ status: "offline" });
  expect(
    getMobileViewState(
      result({ data: ["cached"], isPending: false }),
      { connectivityStatus: "offline" },
    ),
  ).toEqual({ data: ["cached"], isStale: false, status: "offline" });
});

it("classifies validation, permission, and server failures", () => {
  expect(
    getMobileViewState(
      result({ error: new ApiError(422, "Invalid value"), isError: true, isPending: false }),
    ),
  ).toMatchObject({ status: "error", error: { kind: "validation", retryable: false, status: 422 } });
  expect(
    getMobileViewState(
      result({ error: new ApiError(403, "Forbidden"), isError: true, isPending: false }),
    ),
  ).toMatchObject({ status: "error", error: { kind: "permission", retryable: false, status: 403 } });
  expect(
    getMobileViewState(
      result({ error: new ApiError(503, "Unavailable"), isError: true, isPending: false }),
    ),
  ).toMatchObject({ status: "error", error: { kind: "server", retryable: true, status: 503 } });
});

it.each([
  [400, "BAD_REQUEST"],
  [401, "UNAUTHORIZED"],
  [403, "FORBIDDEN"],
  [404, "NOT_FOUND"],
  [409, "CONFLICT"],
  [422, "VALIDATION_ERROR"],
  [429, "RATE_LIMITED"],
  [500, "INTERNAL_SERVER_ERROR"],
  [502, "BAD_GATEWAY"],
  [503, "SERVICE_UNAVAILABLE"],
] as const)("keeps HTTP %s failures distinct in the shared state", (status, code) => {
  expect(classifyMobileStateError(new ApiError(status, "raw secret detail"))).toMatchObject({
    code,
    status,
  });
});

it("maps transport failures to offline state without leaking raw errors", () => {
  const state = getMobileViewState(
    result({ error: new TransportError("offline"), isError: true, isPending: false }),
  );

  expect(state).toEqual({ status: "offline" });
});

it("keeps network and timeout failures separate from offline", () => {
  expect(
    getMobileViewState(
      result({ error: new TransportError("network"), isError: true, isPending: false }),
    ),
  ).toMatchObject({
    error: { code: "NETWORK_ERROR", message: "ارتباط با سرویس برقرار نشد. دوباره تلاش کنید." },
    status: "error",
  });
  expect(
    classifyMobileStateError(new TransportError("timeout")),
  ).toMatchObject({
    code: "REQUEST_TIMEOUT",
    message: "پاسخ سرویس بیش از حد طول کشید. دوباره تلاش کنید.",
  });
});

it("does not turn an aborted request into a visible error state", () => {
  expect(
    getMobileViewState(
      result({ error: new TransportError("aborted"), isError: true, isPending: false }),
    ),
  ).toEqual({ status: "loading" });
});

it("uses audience and context for API presentation", () => {
  const state = getMobileViewState(
    result({
      error: new ApiError(403, "raw permission detail", null, "SPECIALIST_RELATIONSHIP_REQUIRED"),
      isError: true,
      isPending: false,
    }),
    { audience: "physician", context: "specialist_review" },
  );

  expect(state).toMatchObject({
    error: {
      message: "این متخصص به پرونده موردنظر دسترسی ندارد.",
      code: "SPECIALIST_RELATIONSHIP_REQUIRED",
    },
  });
});

it.each([
  ["member", "PROFILE_WEIGHT_REQUIRED", "وزن شما در پروفایل"],
  ["admin", "BODY_ANALYSIS_PROVIDER_UNAVAILABLE", "سرویس ارائه‌دهنده تحلیل بدن"],
  ["coach", "COACH_ROLE_REQUIRED", "مربی"],
  ["physician", "SAFETY_DECISION_NOT_FOUND", "ارزیابی ایمنی"],
] as const)("resolves API errors for the %s audience", (audience, code, expected) => {
  const result = classifyMobileStateError(
    new ApiError(403, "raw secret detail", null, code, { requestId: "role-request-1" }),
    { audience, context: audience === "physician" ? "specialist_review" : "generic" },
  );

  expect(result.message).toContain(expected);
  expect(result.message).not.toContain("raw secret detail");
  if (audience === "admin") expect(result.presentation.showTechnicalDetails).toBe(true);
});

it("presents API failures without exposing server or provider messages", () => {
  const fallback = "عملیات انجام نشد.";
  expect(mobileRequestErrorMessage(new ApiError(422, "internal provider detail"), fallback)).toBe(
    "اطلاعات واردشده را بررسی و موارد مشخص‌شده را اصلاح کنید.",
  );
  expect(mobileRequestErrorMessage(new ApiError(403, "secret permission detail"), fallback)).toBe(
    "برای این عملیات دسترسی لازم وجود ندارد.",
  );
  expect(mobileRequestErrorMessage(new ApiError(503, "upstream failure"), fallback)).toBe(
    "سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.",
  );
});
