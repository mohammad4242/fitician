import {
  isLeapJalaaliYear,
  isValidJalaaliDate as isValidJalaaliDateFromLibrary,
  jalaaliMonthLength,
  toGregorian,
  toJalaali,
} from "jalaali-js";

export const IRAN_TIME_ZONE = "Asia/Tehran";
export const PERSIAN_CALENDAR_LOCALE = "fa-IR-u-ca-persian";

export const PERSIAN_MONTH_NAMES_FA = [
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
] as const;

export type JalaliDateParts = {
  year: number;
  month: number;
  day: number;
};

export type JalaliDateTimeParts = JalaliDateParts & {
  hour: number;
  minute: number;
};

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

const TEHRAN_DATE_TIME_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  hour: "2-digit",
  hourCycle: "h23",
  minute: "2-digit",
  month: "2-digit",
  timeZone: IRAN_TIME_ZONE,
  year: "numeric",
});

const TEHRAN_OFFSET_FORMATTER = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  hourCycle: "h23",
  minute: "2-digit",
  timeZone: IRAN_TIME_ZONE,
  timeZoneName: "longOffset",
});

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

function isoDateOnlyParts(value: string): JalaliDateParts {
  const match = ISO_DATE_ONLY.exec(value);
  if (match === null) throw new RangeError("Expected an ISO date-only value");

  const parts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
  dateOnlyAsUtcNoon(value);
  return parts;
}

function timestampAsDate(value: string): Date {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new RangeError("Expected a valid ISO timestamp");
  return date;
}

function formatPersianCalendarNumber(value: number): string {
  return value.toLocaleString("fa-IR", { useGrouping: false });
}

function assertInteger(value: number, name: string): void {
  if (!Number.isInteger(value)) throw new RangeError(`Expected an integer ${name}`);
}

function assertValidJalaliDate(parts: JalaliDateParts): void {
  if (!isValidJalaliDate(parts)) throw new RangeError("Expected a valid Jalali date");
}

function utcMillisecondsFromGregorianParts(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
): number {
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(hour, minute, 0, 0);
  return date.getTime();
}

function numericDateTimeParts(date: Date): Record<string, number> {
  const formattedParts = TEHRAN_DATE_TIME_PARTS_FORMATTER.formatToParts(date);
  return Object.fromEntries(
    formattedParts
      .filter((part) => ["year", "month", "day", "hour", "minute"].includes(part.type))
      .map((part) => [part.type, Number(part.value)]),
  );
}

function tehranOffsetInMinutes(date: Date): number {
  const offsetPart = TEHRAN_OFFSET_FORMATTER.formatToParts(date)
    .find((part) => part.type === "timeZoneName")?.value;
  if (offsetPart === undefined) throw new RangeError("Unable to resolve Tehran timezone offset");

  const match = /^GMT(?:(?<sign>[+-])(?<hours>\d{2})(?::?(?<minutes>\d{2}))?)?$/.exec(offsetPart);
  if (match === null) throw new RangeError("Unable to resolve Tehran timezone offset");

  const sign = match.groups?.sign === "-" ? -1 : 1;
  const hours = Number(match.groups?.hours ?? 0);
  const minutes = Number(match.groups?.minutes ?? 0);
  return sign * (hours * 60 + minutes);
}

export function isoDateToJalaliParts(isoDate: string): JalaliDateParts {
  const gregorian = isoDateOnlyParts(isoDate);
  const jalali = toJalaali(gregorian.year, gregorian.month, gregorian.day);
  return { year: jalali.jy, month: jalali.jm, day: jalali.jd };
}

export function jalaliPartsToIsoDate(parts: JalaliDateParts): string {
  assertValidJalaliDate(parts);
  const gregorian = toGregorian(parts.year, parts.month, parts.day);
  return `${String(gregorian.gy).padStart(4, "0")}-${String(gregorian.gm).padStart(2, "0")}-${String(gregorian.gd).padStart(2, "0")}`;
}

export function isValidJalaliDate(parts: JalaliDateParts): boolean {
  if (![parts.year, parts.month, parts.day].every(Number.isInteger)) return false;
  try {
    return isValidJalaaliDateFromLibrary(parts.year, parts.month, parts.day);
  } catch {
    return false;
  }
}

export function daysInJalaliMonth(year: number, month: number): number {
  assertInteger(year, "Jalali year");
  assertInteger(month, "Jalali month");
  if (month < 1 || month > 12) throw new RangeError("Expected a Jalali month from 1 to 12");
  if (!isValidJalaaliDateFromLibrary(year, 1, 1)) {
    throw new RangeError("Expected a supported Jalali year");
  }
  return month === 12
    ? isLeapJalaaliYear(year) ? 30 : 29
    : jalaaliMonthLength(year, month);
}

export function isoTimestampToTehranJalaliParts(isoTimestamp: string): JalaliDateTimeParts {
  const date = timestampAsDate(isoTimestamp);
  const gregorian = numericDateTimeParts(date);
  const jalali = toJalaali(gregorian.year, gregorian.month, gregorian.day);
  return {
    year: jalali.jy,
    month: jalali.jm,
    day: jalali.jd,
    hour: gregorian.hour,
    minute: gregorian.minute,
  };
}

export function tehranJalaliDateTimeToIso(parts: JalaliDateTimeParts): string {
  assertValidJalaliDate(parts);
  assertInteger(parts.hour, "hour");
  assertInteger(parts.minute, "minute");
  if (parts.hour < 0 || parts.hour > 23 || parts.minute < 0 || parts.minute > 59) {
    throw new RangeError("Expected a valid time of day");
  }

  const gregorian = toGregorian(parts.year, parts.month, parts.day);
  const localWallClockMs = utcMillisecondsFromGregorianParts(
    gregorian.gy,
    gregorian.gm,
    gregorian.gd,
    parts.hour,
    parts.minute,
  );

  let instantMs = localWallClockMs - tehranOffsetInMinutes(new Date(localWallClockMs)) * 60_000;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    instantMs = localWallClockMs - tehranOffsetInMinutes(new Date(instantMs)) * 60_000;
  }

  const resolved = numericDateTimeParts(new Date(instantMs));
  if (
    resolved.year !== gregorian.gy
    || resolved.month !== gregorian.gm
    || resolved.day !== gregorian.gd
    || resolved.hour !== parts.hour
    || resolved.minute !== parts.minute
  ) {
    throw new RangeError("The Tehran local datetime does not exist");
  }

  return new Date(instantMs).toISOString();
}

export function formatIsoDate(
  isoDate: string,
  locale: string,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium" },
): string {
  return new Intl.DateTimeFormat(locale, {
    ...options,
    timeZone: "UTC",
  }).format(dateOnlyAsUtcNoon(isoDate));
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

export function formatTehranDate(isoTimestamp: string): string {
  const parts = isoTimestampToTehranJalaliParts(isoTimestamp);
  return `${formatPersianCalendarNumber(parts.day)} ${PERSIAN_MONTH_NAMES_FA[parts.month - 1]} ${formatPersianCalendarNumber(parts.year)}`;
}

export function formatTehranTime(isoTimestamp: string): string {
  const parts = isoTimestampToTehranJalaliParts(isoTimestamp);
  return `${formatPersianCalendarNumber(parts.hour).padStart(2, "۰")}:${formatPersianCalendarNumber(parts.minute).padStart(2, "۰")}`;
}
