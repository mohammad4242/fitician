import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@fitician/core";

import { AppErrorNotice } from "./AppErrorNotice";

describe("AppErrorNotice", () => {
  it("presents a member-safe actionable message", () => {
    render(
      <AppErrorNotice
        audience="member"
        context="workout_generation"
        error={new ApiError(422, "private provider detail", null, "PROFILE_WEIGHT_REQUIRED")}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("برنامه تمرینی ساخته نشد چون وزن شما در پروفایل ثبت نشده است");
    expect(alert).not.toHaveTextContent("PROFILE_WEIGHT_REQUIRED");
    expect(alert).not.toHaveTextContent("private provider detail");
  });

  it("shows safe diagnostics to an admin", () => {
    render(
      <AppErrorNotice
        audience="admin"
        context="body_analysis"
        error={new ApiError(503, "provider secret", null, "BODY_ANALYSIS_PROVIDER_UNAVAILABLE", {
          meta: { current_state: "queued" },
          requestId: "ui-request-1",
          retryable: true,
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("سرویس ارائه‌دهنده تحلیل بدن در دسترس نیست");
    expect(alert).toHaveTextContent("BODY_ANALYSIS_PROVIDER_UNAVAILABLE");
    expect(alert).toHaveTextContent("503");
    expect(alert).toHaveTextContent("ui-request-1");
    expect(alert).not.toHaveTextContent("provider secret");
  });

  it("localizes admin diagnostic labels", () => {
    render(
      <AppErrorNotice
        audience="admin"
        context="body_analysis"
        error={new ApiError(503, "private detail", null, "BODY_ANALYSIS_PROVIDER_UNAVAILABLE", {
          requestId: "ui-request-en-1",
        })}
        locale="en"
      />,
    );

    const details = screen.getByTestId("app-error-technical-details");
    expect(details).toHaveTextContent("Error code");
    expect(details).toHaveTextContent("Request ID");
    expect(details).toHaveTextContent("Retryable");
    expect(details).not.toHaveTextContent("کد خطا");
  });

  it("uses coach workflow language", () => {
    render(
      <AppErrorNotice
        audience="coach"
        context="specialist_review"
        error={new ApiError(403, "forbidden", null, "COACH_ROLE_REQUIRED")}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("این عملیات فقط برای مربی در دسترس است");
  });

  it("uses physician workflow language", () => {
    render(
      <AppErrorNotice
        audience="physician"
        context="specialist_review"
        error={new ApiError(404, "missing safety", null, "SAFETY_DECISION_NOT_FOUND")}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "بررسی این برنامه ممکن نیست چون ارزیابی ایمنی کاربر هنوز ثبت نشده است",
    );
  });

  it("does not render cancelled requests as a visible error", () => {
    render(
      <AppErrorNotice
        audience="member"
        context="generic"
        error={new DOMException("navigation", "AbortError")}
      />,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("localizes the retry action", () => {
    render(
      <AppErrorNotice
        audience="member"
        context="generic"
        error={new ApiError(503, "private detail", null, "SERVICE_UNAVAILABLE")}
        locale="en"
        onRetry={() => undefined}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent("Try again");
  });
});
