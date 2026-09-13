import { IRAN_TIME_ZONE } from "./iran-calendar.js";

export function localIsoDate(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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
