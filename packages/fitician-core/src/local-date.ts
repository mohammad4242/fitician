import { IRAN_TIME_ZONE } from "./iran-calendar.js";

export function localIsoDate(
  now: Date = new Date(),
  timeZone: string = resolvedIanaTimeZone(),
): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function resolvedIanaTimeZone(): string {
  try {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (typeof timeZone !== "string" || timeZone.length === 0) return IRAN_TIME_ZONE;
    new Intl.DateTimeFormat("en-US", { timeZone }).format();
    return timeZone;
  } catch {
    return IRAN_TIME_ZONE;
  }
}
