import { readFileSync } from "node:fs";

import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { formatPersianDate, formatPersianDateWithWeekday } from "@fitician/core";

import { ReviewQueueGroupHeader } from "./ReviewQueueGroupHeader";

const reviewQueueGroupHeaderStyles = readFileSync("src/shared/reviewQueueGroupHeader.css", "utf8");

it("uses the vivid project aqua for the week accent", () => {
  expect(reviewQueueGroupHeaderStyles).toContain("border-inline-start: 0.3rem solid var(--fitician-aqua);");
});

it("starts collapsed and opens the selected queue group", () => {
  render(
    <details data-testid="review-group">
      <ReviewQueueGroupHeader
        collapsible
        count={1}
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
      />
      <div>پرونده هفته</div>
    </details>,
  );

  const group = screen.getByTestId("review-group");
  expect(group).not.toHaveAttribute("open");
  const summary = group.querySelector("summary");
  expect(summary).not.toBeNull();

  fireEvent.click(summary as HTMLElement);

  expect(group).toHaveAttribute("open");
});

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
