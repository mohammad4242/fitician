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

it("returns a usable IANA timezone with a safe fallback contract", () => {
  expect(resolvedIanaTimeZone()).toBeTruthy();
});

