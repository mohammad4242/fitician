import { afterEach, expect, it, vi } from "vitest";

import {
  FITICIAN_WEEKDAY_LABELS_FA,
  IRAN_TIME_ZONE,
  fiticianWeekdayFromIsoDate,
  formatPersianDate,
  formatPersianDateWithWeekday,
  formatPersianWeekday,
  formatIsoDate,
  formatTehranDateTime,
} from "./iran-calendar.js";
import { resolvedIanaTimeZone } from "./local-date.js";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

it("formats a known Gregorian date with the Persian calendar", () => {
  expect(formatPersianDate("2026-09-14")).toBe("۲۳ شهریور ۱۴۰۵");
  expect(formatPersianDateWithWeekday("2026-09-14")).toBe("دوشنبه ۲۳ شهریور ۱۴۰۵");
  expect(formatPersianWeekday("2026-09-14")).toBe("دوشنبه");
});

it("formats ISO date-only values with a stable Gregorian calendar", () => {
  expect(formatIsoDate("2026-09-14", "en-US")).toBe("Sep 14, 2026");
  expect(formatIsoDate("2026-09-14", "en-US", { day: "numeric", month: "short" })).toBe("Sep 14");
});

it("maps every Gregorian Saturday-through-Friday date to the Fitician weekday contract", () => {
  const dates = [
    "2026-09-12",
    "2026-09-13",
    "2026-09-14",
    "2026-09-15",
    "2026-09-16",
    "2026-09-17",
    "2026-09-18",
  ];

  expect(dates.map(fiticianWeekdayFromIsoDate)).toEqual([0, 1, 2, 3, 4, 5, 6]);
  expect(FITICIAN_WEEKDAY_LABELS_FA).toEqual([
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
  ]);
});

it("does not shift a date-only value under a negative machine timezone", () => {
  vi.stubEnv("TZ", "America/Los_Angeles");

  expect(formatPersianDate("2026-09-14")).toBe("۲۳ شهریور ۱۴۰۵");
  expect(formatPersianDateWithWeekday("2026-09-14")).toContain("دوشنبه");
});

it("formats an instant at the Tehran boundary in Tehran time", () => {
  expect(formatTehranDateTime("2026-09-13T20:45:00Z")).toBe("۲۳ شهریور ۱۴۰۵، ۰:۱۵");
  expect(IRAN_TIME_ZONE).toBe("Asia/Tehran");
});

it("rejects malformed or impossible ISO date-only values", () => {
  for (const value of ["", "2026-9-14", "2026-02-30", "2026-09-14T00:00:00Z"]) {
    expect(() => formatPersianDate(value)).toThrow(RangeError);
    expect(() => fiticianWeekdayFromIsoDate(value)).toThrow(RangeError);
  }
});

it("falls back to Tehran when the device timezone is unavailable or invalid", () => {
  const realDateTimeFormat = Intl.DateTimeFormat;
  vi.spyOn(Intl, "DateTimeFormat").mockImplementation((locales, options) => {
    if (locales === undefined && options === undefined) {
      return {
        resolvedOptions: () => ({ timeZone: "Not/AZone" }),
      } as Intl.DateTimeFormat;
    }
    return new realDateTimeFormat(locales, options);
  });

  expect(resolvedIanaTimeZone()).toBe(IRAN_TIME_ZONE);
});
