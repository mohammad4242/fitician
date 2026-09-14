import { render, screen } from "@testing-library/react-native";
import { expect, test } from "@jest/globals";

import { formatPersianDate } from "@fitician/core";

import { ReviewQueueGroupHeader } from "./ReviewQueueGroupHeader";

test("renders the real week offset and date range in separate rows", () => {
  render(
    <ReviewQueueGroupHeader
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

  expect(screen.getByText("۴ هفته قبل")).toBeTruthy();
  expect(screen.getByText(`${formatPersianDate("2026-08-18")} تا ${formatPersianDate("2026-08-24")}`)).toBeTruthy();
  expect(screen.queryByText(/هفتهٔ/)).toBeNull();
});

test("keeps today as its own day header", () => {
  render(
    <ReviewQueueGroupHeader
      group={{ date: "2026-09-14", items: [], key: "2026-09-14", kind: "day" }}
    />,
  );

  expect(screen.getByText("امروز")).toBeTruthy();
  expect(screen.getByText("۲۳ شهریور ۱۴۰۵")).toBeTruthy();
});
