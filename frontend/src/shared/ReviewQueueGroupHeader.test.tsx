import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { formatPersianDate, formatPersianDateWithWeekday } from "@fitician/core";

import { ReviewQueueGroupHeader } from "./ReviewQueueGroupHeader";

it("renders a week title and date range as separate RTL-safe rows", () => {
  render(
    <ReviewQueueGroupHeader
      count={3}
      fa
      headingId="review-week-4"
      group={{
        endDate: "2026-08-24",
        items: [],
        key: "week-4",
        kind: "week",
        startDate: "2026-08-18",
        weekOffset: 4,
      }}
    />,
  );

  expect(screen.getByRole("heading", { name: "۴ هفته قبل" })).toBeInTheDocument();
  expect(screen.getByText(`${formatPersianDate("2026-08-18")} تا ${formatPersianDate("2026-08-24")}`)).toBeInTheDocument();
  expect(screen.queryByText(/هفتهٔ/)).not.toBeInTheDocument();
  expect(screen.getByRole("heading").parentElement).toHaveClass("review-queue-group-header__copy");
});

it("keeps today as a separate day header", () => {
  render(
    <ReviewQueueGroupHeader
      count={1}
      fa
      headingId="review-today"
      group={{ date: "2026-09-14", items: [], key: "2026-09-14", kind: "day" }}
    />,
  );

  expect(screen.getByRole("heading", { name: "امروز" })).toBeInTheDocument();
  expect(screen.getByText(formatPersianDateWithWeekday("2026-09-14"))).toBeInTheDocument();
});
