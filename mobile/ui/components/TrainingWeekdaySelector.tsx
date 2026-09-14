import { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { FITICIAN_WEEKDAY_LABELS_FA } from "@fitician/core";
import {
  getPrimaryTrainingWeekdayPreset,
  getTrainingWeekdayPresets,
  preferredWeekdays,
  isTrainingWeekdayPreset,
} from "@fitician/core/profile";

import { RTL_LAYOUT, RTL_TEXT } from "../rtl";
import { fiticianTokens } from "../tokens";

export interface TrainingWeekdaySelectorProps {
  readonly error?: string;
  readonly onChange: (weekdays: number[]) => void;
  readonly selectedWeekdays: readonly number[];
  readonly trainingDays: number;
}

export function TrainingWeekdaySelector({
  error,
  onChange,
  selectedWeekdays,
  trainingDays,
}: TrainingWeekdaySelectorProps) {
  const presets = getTrainingWeekdayPresets(trainingDays);
  const primaryPreset = getPrimaryTrainingWeekdayPreset(trainingDays);
  const [customMode, setCustomMode] = useState(
    () => selectedWeekdays.length > 0 && !isTrainingWeekdayPreset(trainingDays, selectedWeekdays),
  );
  const mountedTrainingDays = useRef(trainingDays);

  useEffect(() => {
    if (mountedTrainingDays.current !== trainingDays) {
      mountedTrainingDays.current = trainingDays;
      setCustomMode(false);
    }
  }, [trainingDays]);

  if (presets.length === 0 || primaryPreset === null) return null;

  const displaySelection = selectedWeekdays.length > 0 ? selectedWeekdays : primaryPreset;
  const countSelection = customMode ? selectedWeekdays : displaySelection;
  const sortedDisplaySelection = [...displaySelection].sort((a, b) => a - b);
  const selectedPresetIndex = customMode
    ? -1
    : presets.findIndex(
      (preset) =>
        preset.length === sortedDisplaySelection.length
        && preset.every((day, index) => day === sortedDisplaySelection[index]),
    );
  const numberFormat = new Intl.NumberFormat("fa-IR");

  function toggleWeekday(day: number) {
    const selected = selectedWeekdays.includes(day);
    if (!selected && selectedWeekdays.length >= trainingDays) return;
    onChange(
      selected
        ? selectedWeekdays.filter((item) => item !== day)
        : [...selectedWeekdays, day].sort((a, b) => a - b),
    );
  }

  return (
    <View style={[styles.selector, RTL_LAYOUT]}>
      <Text accessibilityRole="header" style={styles.title}>روزهای تمرینت</Text>
      <Text style={styles.subtitle}>
        یکی از برنامه‌های پیشنهادی فیتیشن را انتخاب کن یا روزها را خودت تعیین کن.
      </Text>
      <View
        accessible
        accessibilityLabel="روزهای تمرینت"
        accessibilityRole="radiogroup"
        style={styles.presetList}
      >
        {presets.map((preset, index) => {
          const label = weekdayLabel(preset);
          const isSelected = selectedPresetIndex === index;
          return (
            <Pressable
              accessible
              accessibilityLabel={label}
              accessibilityRole="radio"
              accessibilityState={{ selected: isSelected }}
              key={label}
              onPress={() => {
                setCustomMode(false);
                onChange([...preset]);
              }}
              style={({ pressed }) => [styles.preset, isSelected && styles.selected, pressed && styles.pressed]}
            >
              {index === 0 ? <Text style={styles.recommended}>پیشنهاد فیتیشن</Text> : null}
              <Text style={[styles.presetText, isSelected && styles.selectedText]}>{label}</Text>
              {trainingDays === 5 ? (
                <Text style={styles.restText}>استراحت: {weekdayLabel(preferredWeekdays.filter((day) => !new Set(preset).has(day)))}</Text>
              ) : null}
            </Pressable>
          );
        })}
        <Pressable
          accessible
          accessibilityLabel="روزهای تمرین را خودم انتخاب می‌کنم"
          accessibilityRole="radio"
          accessibilityState={{ selected: customMode }}
          onPress={() => setCustomMode(true)}
          style={({ pressed }) => [styles.preset, styles.customPreset, customMode && styles.selected, pressed && styles.pressed]}
        >
          <Text style={[styles.presetText, customMode && styles.selectedText]}>روزهای تمرین را خودم انتخاب می‌کنم</Text>
        </Pressable>
      </View>
      {customMode ? (
        <View accessible accessibilityLabel="روزهای دلخواه" style={styles.customBox}>
          <Text style={styles.customTitle}>روزهای دلخواه</Text>
          <View style={styles.weekdayGrid}>
            {preferredWeekdays.map((day) => {
              const checked = selectedWeekdays.includes(day);
              const disabled = !checked && selectedWeekdays.length >= trainingDays;
              return (
                <Pressable
                  accessible
                  accessibilityLabel={FITICIAN_WEEKDAY_LABELS_FA[day] ?? String(day)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked, disabled }}
                  disabled={disabled}
                  key={day}
                  onPress={() => toggleWeekday(day)}
                  style={({ pressed }) => [styles.weekday, checked && styles.selected, disabled && styles.disabled, pressed && styles.pressed]}
                >
                  <Text style={[styles.weekdayText, checked && styles.selectedText]}>
                    {FITICIAN_WEEKDAY_LABELS_FA[day] ?? String(day)}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      ) : null}
      <Text accessibilityLiveRegion="polite" style={styles.count}>
        {numberFormat.format(countSelection.length)} از {numberFormat.format(trainingDays)} روز انتخاب شده
      </Text>
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    </View>
  );
}

function weekdayLabel(weekdays: readonly number[]): string {
  return weekdays.map((day) => FITICIAN_WEEKDAY_LABELS_FA[day] ?? String(day)).join(" · ");
}

const styles = StyleSheet.create({
  count: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  customBox: {
    backgroundColor: fiticianTokens.colors.surfaceInteractive,
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.medium,
    borderStyle: "dashed",
    borderWidth: 1,
    gap: fiticianTokens.spacing[2],
    padding: fiticianTokens.spacing[3],
  },
  customPreset: {
    flexBasis: "100%",
  },
  customTitle: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  disabled: {
    opacity: 0.45,
  },
  error: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.danger,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  preset: {
    alignItems: "flex-start",
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    flexBasis: "48%",
    flexGrow: 1,
    gap: fiticianTokens.spacing[1],
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    minWidth: 0,
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
  },
  presetList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
  },
  presetText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    lineHeight: 22,
  },
  recommended: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  restText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  selected: {
    backgroundColor: fiticianTokens.colors.surfaceInteractive,
    borderColor: fiticianTokens.colors.aqua,
  },
  selectedText: {
    color: fiticianTokens.colors.aqua,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  pressed: {
    opacity: 0.86,
    transform: [{ scale: fiticianTokens.motion.pressedScale }],
  },
  selector: {
    gap: fiticianTokens.spacing[2],
  },
  subtitle: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    lineHeight: 20,
  },
  title: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.lg,
    lineHeight: 28,
  },
  weekday: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.small,
    borderWidth: 1,
    flexBasis: "30%",
    flexGrow: 1,
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    minWidth: 0,
    paddingHorizontal: fiticianTokens.spacing[2],
    paddingVertical: fiticianTokens.spacing[2],
  },
  weekdayGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
  },
  weekdayText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
});
