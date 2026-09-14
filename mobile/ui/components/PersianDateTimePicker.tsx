import {
  isoTimestampToTehranJalaliParts,
  jalaliPartsToIsoDate,
  tehranJalaliDateTimeToIso,
  type JalaliDateTimeParts,
} from "@fitician/core";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { formatPersianNumber } from "../locale";
import { RTL_ROW, RTL_TEXT } from "../rtl";
import { fiticianTokens } from "../tokens";
import {
  datePartsFromIso,
  dateTimePartsToDisplay,
  JalaliDateFields,
  PickerActions,
} from "./PersianDatePicker";
import { FormField } from "./Input";
import { Sheet } from "./Overlay";

export interface PersianDateTimePickerProps {
  readonly accessibilityLabel?: string;
  readonly allowClear?: boolean;
  readonly disabled?: boolean;
  readonly error?: string;
  readonly label?: string;
  readonly max?: string;
  readonly min?: string;
  readonly onChange: (isoTimestamp: string) => void;
  readonly testID?: string;
  readonly value: string;
}

function formatPersianDateTimeValue(value: string): string | null {
  try {
    return dateTimePartsToDisplay(isoTimestampToTehranJalaliParts(value));
  } catch {
    return null;
  }
}

function dateTimePartsFromIso(value: string, min?: string, max?: string): JalaliDateTimeParts {
  try {
    return isoTimestampToTehranJalaliParts(value);
  } catch {
    for (const candidate of [min, max]) {
      if (candidate === undefined) continue;
      try {
        return isoTimestampToTehranJalaliParts(candidate);
      } catch {
        // Continue to the current Tehran time fallback.
      }
    }
    const date = datePartsFromIso("");
    return { ...date, hour: 12, minute: 0 };
  }
}

function timestampInRange(value: string, min?: string, max?: string): boolean {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return false;
  return (min === undefined || timestamp >= Date.parse(min))
    && (max === undefined || timestamp <= Date.parse(max));
}

function timestampBoundaryToDate(value: string | undefined): string | undefined {
  if (value === undefined) return undefined;
  try {
    const parts = isoTimestampToTehranJalaliParts(value);
    return jalaliPartsToIsoDate(parts);
  } catch {
    return undefined;
  }
}

function TimeOptions({
  max,
  minute,
  min,
  onChange,
  part,
  testID,
  value,
}: {
  readonly max: number;
  readonly minute: number;
  readonly min: number;
  readonly onChange: (value: number) => void;
  readonly part: "hour" | "minute";
  readonly testID: string;
  readonly value: number;
}) {
  const options = Array.from({ length: max - min + 1 }, (_, index) => min + index);
  const label = part === "hour" ? "ساعت" : "دقیقه";
  return (
    <View style={styles.partField}>
      <Text style={styles.partLabel}>{label}</Text>
      <ScrollView horizontal contentContainerStyle={styles.options} showsHorizontalScrollIndicator={false}>
        {options.map((option) => {
          const selected = value === option;
          return (
            <Pressable
              accessibilityLabel={formatPersianNumber(option)}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              key={option}
              onPress={() => onChange(option)}
              style={[styles.option, selected && styles.optionSelected]}
              testID={`${testID}-option-${part}-${option}`}
            >
              <Text style={[styles.optionText, selected && styles.optionTextSelected]}>
                {formatPersianNumber(option, { useGrouping: false }).padStart(2, "۰")}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
      <Text accessibilityLabel={`${label} انتخاب‌شده`} style={styles.selectedTime}>
        {formatPersianNumber(part === "hour" ? value : minute, { useGrouping: false }).padStart(2, "۰")}
      </Text>
    </View>
  );
}

export function PersianDateTimePicker({
  accessibilityLabel,
  allowClear = false,
  disabled = false,
  error,
  label,
  max,
  min,
  onChange,
  testID = "persian-datetime-picker",
  value,
}: PersianDateTimePickerProps) {
  const [visible, setVisible] = useState(false);
  const [draft, setDraft] = useState<JalaliDateTimeParts>(() => dateTimePartsFromIso(value, min, max));
  const [validationError, setValidationError] = useState<string | null>(null);
  const displayValue = formatPersianDateTimeValue(value);
  const minDate = timestampBoundaryToDate(min);
  const maxDate = timestampBoundaryToDate(max);

  function open(): void {
    setDraft(dateTimePartsFromIso(value, min, max));
    setValidationError(null);
    setVisible(true);
  }

  function close(): void {
    setValidationError(null);
    setVisible(false);
  }

  function confirm(): void {
    try {
      const isoTimestamp = tehranJalaliDateTimeToIso(draft);
      if (!timestampInRange(isoTimestamp, min, max)) throw new RangeError("out of range");
      onChange(isoTimestamp);
      close();
    } catch {
      setValidationError("زمان انتخاب‌شده معتبر نیست.");
    }
  }

  function clear(): void {
    onChange("");
    close();
  }

  return (
    <FormField error={validationError ?? error} label={label}>
      <Pressable
        accessibilityLabel={accessibilityLabel ?? label ?? "انتخاب زمان"}
        accessibilityRole="button"
        accessibilityState={{ disabled, expanded: visible }}
        accessibilityHint="برای انتخاب تاریخ و زمان باز می‌شود"
        disabled={disabled}
        onPress={open}
        style={[styles.trigger, disabled && styles.triggerDisabled]}
        testID={`${testID}-trigger`}
      >
        <Text style={[styles.triggerText, displayValue === null && styles.placeholder]}>
          {displayValue ?? "انتخاب تاریخ و زمان"}
        </Text>
        <Text style={styles.chevron}>⌄</Text>
      </Pressable>
      <Sheet onClose={close} title={label ?? "انتخاب تاریخ و زمان"} visible={visible}>
        <Text style={styles.summary}>{displayValue ?? "زمان جدید"}</Text>
        <JalaliDateFields
          max={maxDate}
          min={minDate}
          onChange={(parts) => setDraft((current) => ({ ...current, ...parts }))}
          parts={draft}
          testID={testID}
        />
        <View style={styles.timeFields}>
          <TimeOptions
            max={23}
            minute={draft.minute}
            min={0}
            onChange={(hour) => setDraft((current) => ({ ...current, hour }))}
            part="hour"
            testID={testID}
            value={draft.hour}
          />
          <TimeOptions
            max={59}
            minute={draft.minute}
            min={0}
            onChange={(minute) => setDraft((current) => ({ ...current, minute }))}
            part="minute"
            testID={testID}
            value={draft.minute}
          />
        </View>
        {validationError !== null ? <Text style={styles.validationError}>{validationError}</Text> : null}
        <PickerActions allowClear={allowClear} onCancel={close} onClear={clear} onConfirm={confirm} />
      </Sheet>
    </FormField>
  );
}

const styles = StyleSheet.create({
  chevron: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish,
    fontSize: 24,
    lineHeight: 24,
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
  selectedTime: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  summary: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  timeFields: {
    gap: fiticianTokens.spacing[4],
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
