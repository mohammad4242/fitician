import { afterEach, expect, it, vi } from "vitest";

import {
  FITICIAN_WEEKDAY_LABELS_FA,
  IRAN_TIME_ZONE,
  PERSIAN_MONTH_NAMES_FA,
  fiticianWeekdayFromIsoDate,
  formatPersianDate,
  formatPersianDateWithWeekday,
  formatPersianWeekday,
  formatIsoDate,
  formatTehranDate,
  formatTehranDateForLocale,
  formatTehranDateTime,
  formatTehranDateTimeForLocale,
  formatTehranTime,
  formatTehranTimeForLocale,
  daysInJalaliMonth,
  isValidJalaliDate,
  isoDateToJalaliParts,
  isoTimestampToTehranJalaliParts,
  jalaliPartsToIsoDate,
  tehranJalaliDateTimeToIso,
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

it("exposes the canonical Persian month names", () => {
  expect(PERSIAN_MONTH_NAMES_FA).toEqual([
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
  ]);
});

it("converts an ISO date-only value to Jalali without a timezone shift", () => {
  vi.stubEnv("TZ", "America/Los_Angeles");

  expect(isoDateToJalaliParts("2026-09-14")).toEqual({ year: 1405, month: 6, day: 23 });
  expect(jalaliPartsToIsoDate({ year: 1405, month: 6, day: 23 })).toBe("2026-09-14");
});

it("round-trips ISO and Jalali date-only values", () => {
  const dates = ["2020-03-20", "2021-03-21", "2026-09-14"];

  for (const isoDate of dates) {
    expect(jalaliPartsToIsoDate(isoDateToJalaliParts(isoDate))).toBe(isoDate);
  }
});

it("handles Jalali month lengths and leap Esfand", () => {
  expect(daysInJalaliMonth(1405, 1)).toBe(31);
  expect(daysInJalaliMonth(1405, 6)).toBe(31);
  expect(daysInJalaliMonth(1405, 7)).toBe(30);
  expect(daysInJalaliMonth(1399, 12)).toBe(30);
  expect(daysInJalaliMonth(1400, 12)).toBe(29);
  expect(isValidJalaliDate({ year: 1399, month: 12, day: 30 })).toBe(true);
  expect(isValidJalaliDate({ year: 1400, month: 12, day: 30 })).toBe(false);
});

it("rejects invalid Jalali date parts", () => {
  expect(isValidJalaliDate({ year: 1405, month: 0, day: 1 })).toBe(false);
  expect(isValidJalaliDate({ year: 1405, month: 13, day: 1 })).toBe(false);
  expect(isValidJalaliDate({ year: 1405, month: 1, day: 32 })).toBe(false);
  expect(isValidJalaliDate({ year: 1405, month: 7, day: 31 })).toBe(false);
  expect(() => jalaliPartsToIsoDate({ year: 1405, month: 12, day: 30 })).toThrow(RangeError);
});

it("converts Tehran Jalali datetime values to stable ISO instants", () => {
  vi.stubEnv("TZ", "Europe/Berlin");

  const parts = { year: 1405, month: 6, day: 23, hour: 18, minute: 30 };
  const isoTimestamp = tehranJalaliDateTimeToIso(parts);

  expect(isoTimestamp).toBe("2026-09-14T15:00:00.000Z");
  expect(isoTimestampToTehranJalaliParts(isoTimestamp)).toEqual(parts);
});

it("round-trips an existing ISO datetime through Tehran Jalali parts", () => {
  const isoTimestamp = "2024-02-19T15:45:00.000Z";
  expect(tehranJalaliDateTimeToIso(isoTimestampToTehranJalaliParts(isoTimestamp))).toBe(isoTimestamp);
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
  expect(formatTehranDate("2026-09-13T20:45:00Z")).toBe("۲۳ شهریور ۱۴۰۵");
  expect(formatTehranTime("2026-09-13T20:45:00Z")).toBe("۰۰:۱۵");
  expect(formatTehranDateTime("2026-09-13T20:45:00Z")).toBe("۲۳ شهریور ۱۴۰۵، ۰:۱۵");
  expect(IRAN_TIME_ZONE).toBe("Asia/Tehran");
});

it("formats Tehran instants for the requested locale", () => {
  const value = "2026-09-13T20:45:00Z";

  expect(formatTehranDateForLocale(value, "en-US")).toBe("Sep 14, 2026");
  expect(formatTehranDateTimeForLocale(value, "en-US")).toBe("Sep 14, 2026, 12:15 AM");
  expect(formatTehranTimeForLocale(value, "en-US")).toBe("12:15 AM");
  expect(formatTehranDateForLocale(value, "fa-IR")).toBe("۲۳ شهریور ۱۴۰۵");
  expect(() => formatTehranDateForLocale("not-a-timestamp", "en-US")).toThrow(RangeError);
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

it("preserves a valid traveler device timezone", () => {
  const realDateTimeFormat = Intl.DateTimeFormat;
  vi.spyOn(Intl, "DateTimeFormat").mockImplementation(function (locales, options) {
    if (locales === undefined && options === undefined) {
      return {
        resolvedOptions: () => ({ timeZone: "America/Los_Angeles" }),
      } as Intl.DateTimeFormat;
    }
    return new realDateTimeFormat(locales, options);
  });

  expect(resolvedIanaTimeZone()).toBe("America/Los_Angeles");
});
