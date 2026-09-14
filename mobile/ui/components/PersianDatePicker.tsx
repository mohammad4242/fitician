import {
  daysInJalaliMonth,
  isoDateToJalaliParts,
  isoTimestampToTehranJalaliParts,
  jalaliPartsToIsoDate,
  isValidJalaliDate,
  PERSIAN_MONTH_NAMES_FA,
  type JalaliDateParts,
} from "@fitician/core";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { formatPersianNumber } from "../locale";
import { RTL_ROW, RTL_TEXT } from "../rtl";
import { fiticianTokens } from "../tokens";
import { AppIcon } from "./AppIcon";
import { Button } from "./Button";
import { FormField } from "./Input";
import { Sheet } from "./Overlay";

export interface PersianDatePickerProps {
  readonly accessibilityLabel?: string;
  readonly allowClear?: boolean;
  readonly disabled?: boolean;
  readonly error?: string;
  readonly label?: string;
  readonly max?: string;
  readonly min?: string;
  readonly onChange: (isoDate: string) => void;
  readonly testID?: string;
  readonly value: string;
}

type DatePart = "day" | "month" | "year";

const DEFAULT_MIN_YEAR = 1300;
const DEFAULT_MAX_YEAR = 1500;

function formatPersianDateValue(value: string): string | null {
  try {
    const parts = isoDateToJalaliParts(value);
    return `${formatPersianNumber(parts.day, { useGrouping: false })} ${PERSIAN_MONTH_NAMES_FA[parts.month - 1]} ${formatPersianNumber(parts.year, { useGrouping: false })}`;
  } catch {
    return null;
  }
}

function currentJalaliDate(): JalaliDateParts {
  const now = isoTimestampToTehranJalaliParts(new Date().toISOString());
  return { day: now.day, month: now.month, year: now.year };
}

function fallbackDate(min: string | undefined, max: string | undefined): JalaliDateParts {
  for (const candidate of [min, max]) {
    if (candidate !== undefined) {
      try {
        return isoDateToJalaliParts(candidate);
      } catch {
        // Continue to the next safe fallback.
      }
    }
  }
  return currentJalaliDate();
}

export function datePartsFromIso(value: string, min?: string, max?: string): JalaliDateParts {
  try {
    return isoDateToJalaliParts(value);
  } catch {
    return fallbackDate(min, max);
  }
}

function isoDateInRange(value: string, min?: string, max?: string): boolean {
  try {
    isoDateToJalaliParts(value);
  } catch {
    return false;
  }
  return (min === undefined || value >= min) && (max === undefined || value <= max);
}

function candidateIsoDate(parts: JalaliDateParts): string | null {
  try {
    return isValidJalaliDate(parts) ? jalaliPartsToIsoDate(parts) : null;
  } catch {
    return null;
  }
}

function optionParts(parts: JalaliDateParts, part: DatePart, value: number): JalaliDateParts {
  const next = { ...parts, [part]: value };
  if (part === "year" || part === "month") {
    next.day = Math.min(next.day, daysInJalaliMonth(next.year, next.month));
  }
  return next;
}

function optionIsDisabled(
  parts: JalaliDateParts,
  part: DatePart,
  value: number,
  min: string | undefined,
  max: string | undefined,
): boolean {
  const candidate = candidateIsoDate(optionParts(parts, part, value));
  return candidate === null || !isoDateInRange(candidate, min, max);
}

function optionValues(part: DatePart, parts: JalaliDateParts, min?: string, max?: string): number[] {
  if (part === "day") return Array.from({ length: daysInJalaliMonth(parts.year, parts.month) }, (_, index) => index + 1);
  if (part === "month") return Array.from({ length: 12 }, (_, index) => index + 1);

  let first = DEFAULT_MIN_YEAR;
  let last = DEFAULT_MAX_YEAR;
  for (const [boundary, fallback] of [[min, "first"], [max, "last"]] as const) {
    if (boundary === undefined) continue;
    try {
      const year = isoDateToJalaliParts(boundary).year;
      if (fallback === "first") first = Math.min(first, year);
      else last = Math.max(last, year);
    } catch {
      // Keep the broad supported Jalali range.
    }
  }
  first = Math.min(first, parts.year);
  last = Math.max(last, parts.year);
  return Array.from({ length: last - first + 1 }, (_, index) => first + index);
}

function optionLabel(part: DatePart, value: number): string {
  return part === "month"
    ? PERSIAN_MONTH_NAMES_FA[value - 1] ?? "—"
    : formatPersianNumber(value, { useGrouping: false });
}

export function JalaliDateFields({
  max,
  min,
  onChange,
  parts,
  testID,
}: {
  readonly max?: string;
  readonly min?: string;
  readonly onChange: (parts: JalaliDateParts) => void;
  readonly parts: JalaliDateParts;
  readonly testID: string;
}) {
  return (
    <View style={styles.fields}>
      {(["day", "month", "year"] as const).map((part) => {
        const values = optionValues(part, parts, min, max);
        return (
          <View key={part} style={styles.partField}>
            <Text style={styles.partLabel}>{part === "day" ? "روز" : part === "month" ? "ماه" : "سال"}</Text>
            <ScrollView
              horizontal
              contentContainerStyle={styles.options}
              showsHorizontalScrollIndicator={false}
            >
              {values.map((value) => {
                const selected = parts[part] === value;
                const disabled = optionIsDisabled(parts, part, value, min, max);
                return (
                  <Pressable
                    accessibilityLabel={optionLabel(part, value)}
                    accessibilityRole="radio"
                    accessibilityState={{ disabled, selected }}
                    disabled={disabled}
                    key={value}
                    onPress={() => onChange(optionParts(parts, part, value))}
                    style={[styles.option, selected && styles.optionSelected, disabled && styles.optionDisabled]}
                    testID={`${testID}-option-${part}-${value}`}
                  >
                    <Text style={[styles.optionText, selected && styles.optionTextSelected]}>{optionLabel(part, value)}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        );
      })}
    </View>
  );
}

export function PickerActions({
  allowClear,
  onCancel,
  onClear,
  onConfirm,
}: {
  readonly allowClear: boolean;
  readonly onCancel: () => void;
  readonly onClear: () => void;
  readonly onConfirm: () => void;
}) {
  return (
    <View style={[styles.actions, RTL_ROW]}>
      <Button label="انصراف" onPress={onCancel} variant="ghost" />
      {allowClear ? <Button label="پاک کردن" onPress={onClear} variant="secondary" /> : null}
      <Button label="انتخاب" onPress={onConfirm} />
    </View>
  );
}

export function PersianDatePicker({
  accessibilityLabel,
  allowClear = false,
  disabled = false,
  error,
  label,
  max,
  min,
  onChange,
  testID = "persian-date-picker",
  value,
}: PersianDatePickerProps) {
  const [visible, setVisible] = useState(false);
  const [draft, setDraft] = useState<JalaliDateParts>(() => datePartsFromIso(value, min, max));
  const [validationError, setValidationError] = useState<string | null>(null);
  const displayValue = formatPersianDateValue(value);

  function open(): void {
    setDraft(datePartsFromIso(value, min, max));
    setValidationError(null);
    setVisible(true);
  }

  function close(): void {
    setValidationError(null);
    setVisible(false);
  }

  function confirm(): void {
    const isoDate = candidateIsoDate(draft);
    if (isoDate === null || !isoDateInRange(isoDate, min, max)) {
      setValidationError("تاریخ انتخاب‌شده معتبر نیست.");
      return;
    }
    onChange(isoDate);
    close();
  }

  function clear(): void {
    onChange("");
    close();
  }

  return (
    <FormField error={validationError ?? error} label={label}>
      <Pressable
        accessibilityLabel={accessibilityLabel ?? label ?? "انتخاب تاریخ"}
        accessibilityRole="button"
        accessibilityState={{ disabled, expanded: visible }}
        accessibilityHint="برای انتخاب تاریخ باز می‌شود"
        disabled={disabled}
        onPress={open}
        style={[styles.trigger, disabled && styles.triggerDisabled]}
        testID={`${testID}-trigger`}
      >
        <Text style={[styles.triggerText, displayValue === null && styles.placeholder]}>
          {displayValue ?? "انتخاب تاریخ"}
        </Text>
        <AppIcon color={fiticianTokens.colors.aqua} name="chevronDown" size={20} />
      </Pressable>
      <Sheet onClose={close} title={label ?? "انتخاب تاریخ"} visible={visible}>
        <Text style={styles.summary}>{displayValue ?? "تاریخ جدید"}</Text>
        <JalaliDateFields
          max={max}
          min={min}
          onChange={setDraft}
          parts={draft}
          testID={testID}
        />
        {validationError !== null ? <Text style={styles.validationError}>{validationError}</Text> : null}
        <PickerActions allowClear={allowClear} onCancel={close} onClear={clear} onConfirm={confirm} />
      </Sheet>
    </FormField>
  );
}

export function dateTimePartsToDisplay(parts: JalaliDateParts & { readonly hour: number; readonly minute: number }): string {
  return `${formatPersianNumber(parts.day, { useGrouping: false })} ${PERSIAN_MONTH_NAMES_FA[parts.month - 1]} ${formatPersianNumber(parts.year, { useGrouping: false })} · ${formatPersianNumber(parts.hour, { useGrouping: false }).padStart(2, "۰")}:${formatPersianNumber(parts.minute, { useGrouping: false }).padStart(2, "۰")}`;
}

export function jalaliDateOptionValues(parts: JalaliDateParts, min?: string, max?: string): number[] {
  return optionValues("day", parts, min, max);
}

const styles = StyleSheet.create({
  actions: {
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
    justifyContent: "flex-start",
  },
  fields: {
    gap: fiticianTokens.spacing[4],
  },
  option: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.small,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    minWidth: 52,
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
  },
  optionDisabled: {
    opacity: 0.32,
  },
  optionSelected: {
    backgroundColor: fiticianTokens.colors.aquaAtmosphere,
    borderColor: fiticianTokens.colors.aqua,
  },
  optionText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
  },
  optionTextSelected: {
    color: fiticianTokens.colors.aqua,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  options: {
    flexDirection: "row",
    gap: fiticianTokens.spacing[2],
    paddingVertical: fiticianTokens.spacing[1],
  },
  partField: {
    gap: fiticianTokens.spacing[2],
  },
  partLabel: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.medium,
  },
  placeholder: {
    color: fiticianTokens.colors.muted,
  },
  summary: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  trigger: {
    ...RTL_ROW,
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surface,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    justifyContent: "space-between",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[4],
    paddingVertical: fiticianTokens.spacing[3],
  },
  triggerDisabled: {
    opacity: 0.48,
  },
  triggerText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    flex: 1,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
  },
  validationError: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.danger,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
  },
});
