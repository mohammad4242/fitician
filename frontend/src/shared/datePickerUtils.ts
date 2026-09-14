import {
  daysInJalaliMonth,
  isoDateToJalaliParts,
  isoTimestampToTehranJalaliParts,
  PERSIAN_MONTH_NAMES_FA,
  type JalaliDateParts,
} from "@fitician/core/iran-calendar";

export function formatPersianNumber(value: number): string {
  return new Intl.NumberFormat("fa-IR", { useGrouping: false }).format(value);
}

export function formatPersianJalaliDate(parts: JalaliDateParts): string {
  return `${formatPersianNumber(parts.day)} ${PERSIAN_MONTH_NAMES_FA[parts.month - 1] ?? ""} ${formatPersianNumber(parts.year)}`;
}

export function formatPersianJalaliDateTime(
  parts: JalaliDateParts & { hour: number; minute: number },
): string {
  return `${formatPersianJalaliDate(parts)}\n${formatPersianNumber(parts.hour)}:${formatPersianNumber(parts.minute).padStart(2, "۰")}`;
}

export function jalaliDatePartsFromValue(
  value: string,
  fallback: string | undefined,
): JalaliDateParts {
  for (const candidate of [value, fallback]) {
    if (!candidate) continue;
    try {
      return isoDateToJalaliParts(candidate);
    } catch {
      continue;
    }
  }
  const current = isoTimestampToTehranJalaliParts(new Date().toISOString());
  return { year: current.year, month: current.month, day: current.day };
}

export function jalaliDateTimePartsFromValue(
  value: string,
  fallback: string | undefined,
) {
  for (const candidate of [value, fallback]) {
    if (!candidate) continue;
    try {
      return isoTimestampToTehranJalaliParts(candidate);
    } catch {
      continue;
    }
  }
  return isoTimestampToTehranJalaliParts(new Date().toISOString());
}

export function jalaliYearOptions(
  selected: JalaliDateParts,
  min: string | undefined,
  max: string | undefined,
): number[] {
  const boundaryYears = [selected.year, 1300, 1500];
  for (const value of [min, max]) {
    if (!value) continue;
    try {
      boundaryYears.push(isoDateToJalaliParts(value).year);
    } catch {
      continue;
    }
  }
  const minimum = Math.min(...boundaryYears);
  const maximum = Math.max(...boundaryYears);
  return Array.from({ length: maximum - minimum + 1 }, (_, index) => minimum + index);
}

export function dateOnlyIsInRange(value: string, min?: string, max?: string): boolean {
  return (min === undefined || min === "" || value >= min)
    && (max === undefined || max === "" || value <= max);
}

export function timestampIsInRange(value: string, min?: string, max?: string): boolean {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return false;
  const minimum = min ? Date.parse(min) : Number.NEGATIVE_INFINITY;
  const maximum = max ? Date.parse(max) : Number.POSITIVE_INFINITY;
  return timestamp >= minimum && timestamp <= maximum;
}

export function toDateTimeLocalValue(value: string | null | undefined): string {
  if (!value) return "";
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return "";
  const local = new Date(timestamp - new Date(timestamp).getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function dateTimeLocalValueToIso(value: string): string {
  return value === "" ? "" : new Date(value).toISOString();
}

export function daysForJalaliMonth(year: number, month: number): number {
  return daysInJalaliMonth(year, month);
}
