export const IRAN_TIME_ZONE = "Asia/Tehran";
export const PERSIAN_CALENDAR_LOCALE = "fa-IR-u-ca-persian";

export const FITICIAN_WEEKDAY_LABELS_FA = [
  "شنبه",
  "یکشنبه",
  "دوشنبه",
  "سه‌شنبه",
  "چهارشنبه",
  "پنجشنبه",
  "جمعه",
] as const;

const ISO_DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

function dateOnlyAsUtcNoon(value: string): Date {
  const match = ISO_DATE_ONLY.exec(value);
  if (match === null) throw new RangeError("Expected an ISO date-only value");

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(12, 0, 0, 0);
  if (
    date.getUTCFullYear() !== year
    || date.getUTCMonth() !== month - 1
    || date.getUTCDate() !== day
  ) {
    throw new RangeError("Expected a real ISO date-only value");
  }
  return date;
}

function timestampAsDate(value: string): Date {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new RangeError("Expected a valid ISO timestamp");
  return date;
}

export function fiticianWeekdayFromIsoDate(isoDate: string): number {
  return (dateOnlyAsUtcNoon(isoDate).getUTCDay() + 1) % 7;
}

export function formatPersianDate(isoDate: string): string {
  return new Intl.DateTimeFormat(PERSIAN_CALENDAR_LOCALE, {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
    year: "numeric",
  }).format(dateOnlyAsUtcNoon(isoDate));
}

export function formatPersianWeekday(isoDate: string): string {
  return FITICIAN_WEEKDAY_LABELS_FA[fiticianWeekdayFromIsoDate(isoDate)] ?? "";
}

export function formatPersianDateWithWeekday(isoDate: string): string {
  return `${formatPersianWeekday(isoDate)} ${formatPersianDate(isoDate)}`;
}

export function formatTehranDateTime(isoTimestamp: string): string {
  return new Intl.DateTimeFormat(PERSIAN_CALENDAR_LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: IRAN_TIME_ZONE,
  }).format(timestampAsDate(isoTimestamp));
}
