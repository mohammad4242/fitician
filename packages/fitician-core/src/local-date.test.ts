import { expect, it } from "vitest";

import { localIsoDate, resolvedIanaTimeZone } from "./local-date.js";

it("formats the member-local calendar date from local Date fields", () => {
  const localBoundary = new Date(2026, 11, 31, 23, 59, 59);
  const expected = [
    localBoundary.getFullYear(),
    String(localBoundary.getMonth() + 1).padStart(2, "0"),
    String(localBoundary.getDate()).padStart(2, "0"),
  ].join("-");

  expect(localIsoDate(localBoundary)).toBe(expected);
});

it("formats an instant in the requested member timezone", () => {
  const instant = new Date("2026-09-13T20:45:00.000Z");

  expect(localIsoDate(instant, "Asia/Tehran")).toBe("2026-09-14");
  expect(localIsoDate(instant, "America/Los_Angeles")).toBe("2026-09-13");
});

it("returns a usable IANA timezone with a safe fallback contract", () => {
  expect(resolvedIanaTimeZone()).toBeTruthy();
});
