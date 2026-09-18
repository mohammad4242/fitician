import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import type {
  NutritionCatalogueConstraint,
  NutritionCatalogueTarget,
} from "@fitician/core/nutrition";
import { Sheet } from "../ui/components/Overlay";
import { RTL_LAYOUT, RTL_ROW, RTL_TEXT } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";

type SearchResponse = { readonly items: NutritionCatalogueTarget[] };
export type CatalogueTargetSearchOptions = (
  input: { readonly query?: string; readonly limit?: number },
) => Promise<SearchResponse>;

type CatalogueTargetPickerProps<T extends NutritionCatalogueTarget> = {
  readonly label: string;
  readonly value: readonly T[];
  readonly onChange: (value: T[]) => void;
  readonly searchOptions: CatalogueTargetSearchOptions;
  readonly disabled?: boolean;
  readonly includeDetails?: boolean;
};

function targetKey(target: Pick<NutritionCatalogueTarget, "target_type" | "target_id">): string {
  return `${target.target_type}:${target.target_id}`;
}

function typeLabel(target: NutritionCatalogueTarget): string {
  return target.target_type === "food" ? "ماده غذایی" : "وعده";
}

export function CatalogueTargetPicker<T extends NutritionCatalogueTarget = NutritionCatalogueTarget>({
  disabled = false,
  includeDetails = false,
  label,
  onChange,
  searchOptions,
  value,
}: CatalogueTargetPickerProps<T>) {
  const [visible, setVisible] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<NutritionCatalogueTarget[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const requestSequence = useRef(0);

  useEffect(() => {
    if (!visible) return undefined;
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    const timer = setTimeout(() => {
      setLoading(true);
      setError(false);
      void searchOptions({ limit: 20, query: query.trim() })
        .then((response) => {
          if (requestSequence.current !== sequence) return;
          setOptions(response.items);
        })
        .catch(() => {
          if (requestSequence.current !== sequence) return;
          setOptions([]);
          setError(true);
        })
        .finally(() => {
          if (requestSequence.current === sequence) setLoading(false);
        });
    }, 250);
    return () => clearTimeout(timer);
  }, [query, searchOptions, visible]);

  function select(option: NutritionCatalogueTarget) {
    if (value.some((item) => targetKey(item) === targetKey(option))) return;
    const selected = (includeDetails ? { ...option, details: null } : option) as T;
    onChange([...value, selected]);
    setQuery("");
  }

  function remove(target: T) {
    onChange(value.filter((item) => targetKey(item) !== targetKey(target)));
  }

  return (
    <View style={[styles.container, RTL_LAYOUT]}>
      <Text style={styles.label}>{label}</Text>
      {value.length > 0 ? (
        <View accessibilityLabel={`${label} انتخاب‌شده`} style={styles.chips}>
          {value.map((item) => (
            <View key={targetKey(item)} style={[styles.chip, RTL_ROW]}>
              <View style={styles.chipCopy}>
                <Text numberOfLines={1} style={styles.chipName}>{item.name_fa}</Text>
                <Text style={styles.chipType}>{typeLabel(item)}</Text>
              </View>
              <Pressable
                accessibilityLabel={`حذف ${item.name_fa}`}
                accessibilityRole="button"
                disabled={disabled}
                hitSlop={fiticianTokens.spacing[2]}
                onPress={() => remove(item)}
                style={styles.remove}
              >
                <Text style={styles.removeText}>×</Text>
              </Pressable>
            </View>
          ))}
        </View>
      ) : null}
      <Pressable
        accessibilityLabel={`${label} افزودن`}
        accessibilityRole="button"
        disabled={disabled}
        onPress={() => setVisible(true)}
        style={({ pressed }) => [styles.addButton, pressed && styles.pressed, disabled && styles.disabled]}
      >
        <Text style={styles.addButtonText}>+ افزودن</Text>
      </Pressable>
      <Sheet closeLabel="بستن" onClose={() => setVisible(false)} title={label} visible={visible}>
        <TextInput
          accessibilityLabel={`${label} جست‌وجو`}
          autoCapitalize="none"
          autoCorrect={false}
          autoFocus
          onChangeText={(text) => {
            setQuery(text);
            setError(false);
          }}
          placeholder="جست‌وجو در فهرست تأییدشده…"
          placeholderTextColor={fiticianTokens.colors.muted}
          style={styles.searchInput}
          textAlign="right"
          value={query}
        />
        {loading ? <ActivityIndicator accessibilityLabel="در حال جست‌وجو" color={fiticianTokens.colors.aqua} /> : null}
        {error ? (
          <Text accessibilityRole="alert" style={styles.error}>جست‌وجوی فهرست انجام نشد. دوباره تلاش کن.</Text>
        ) : null}
        {!loading && !error && options.length === 0 ? (
          <Text style={styles.empty}>مورد تأییدشده‌ای پیدا نشد.</Text>
        ) : null}
        {!loading && !error ? options.map((option) => {
          const selected = value.some((item) => targetKey(item) === targetKey(option));
          return (
            <Pressable
              accessibilityLabel={`${option.name_fa}، ${typeLabel(option)}`}
              accessibilityRole="button"
              key={targetKey(option)}
              onPress={() => select(option)}
              style={({ pressed }) => [styles.option, selected && styles.selected, pressed && styles.pressed]}
            >
              {option.image_url ? <Image accessibilityIgnoresInvertColors source={{ uri: option.image_url }} style={styles.image} /> : null}
              <View style={styles.optionCopy}>
                <Text style={styles.optionName}>{option.name_fa}</Text>
                {option.name_en ? <Text style={styles.optionEnglish}>{option.name_en}</Text> : null}
              </View>
              <Text style={styles.typeBadge}>{typeLabel(option)}</Text>
              {selected ? <Text accessibilityLabel="انتخاب‌شده" style={styles.check}>✓</Text> : null}
            </Pressable>
          );
        }) : null}
      </Sheet>
    </View>
  );
}

export type { NutritionCatalogueConstraint };

const styles = StyleSheet.create({
  addButton: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceInteractive,
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[4],
  },
  addButtonText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  check: {
    color: fiticianTokens.colors.success,
    fontSize: fiticianTokens.typography.fontSize.lg,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  chip: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.aquaAtmosphere,
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.pill,
    borderWidth: 1,
    gap: fiticianTokens.spacing[2],
    maxWidth: "100%",
    paddingLeft: fiticianTokens.spacing[2],
    paddingRight: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[1],
  },
  chipCopy: {
    alignItems: "flex-start",
    flexShrink: 1,
    gap: 1,
  },
  chipName: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
  },
  chipType: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  chips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
  },
  container: {
    gap: fiticianTokens.spacing[2],
  },
  disabled: {
    opacity: 0.55,
  },
  empty: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    paddingVertical: fiticianTokens.spacing[3],
  },
  error: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.danger,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
  },
  image: {
    borderRadius: fiticianTokens.radii.small,
    height: 44,
    width: 44,
  },
  label: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.medium,
  },
  option: {
    alignItems: "center",
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    flexDirection: "row-reverse",
    gap: fiticianTokens.spacing[3],
    minHeight: 60,
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
  },
  optionCopy: {
    flex: 1,
    gap: 2,
  },
  optionEnglish: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish,
    fontSize: fiticianTokens.typography.fontSize.xs,
  },
  optionName: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  pressed: {
    opacity: 0.78,
  },
  remove: {
    alignItems: "center",
    height: fiticianTokens.layout.minimumTouchTarget,
    justifyContent: "center",
    width: fiticianTokens.layout.minimumTouchTarget,
  },
  removeText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish,
    fontSize: 24,
    lineHeight: 24,
  },
  searchInput: {
    ...RTL_TEXT,
    backgroundColor: fiticianTokens.colors.surfaceRaised,
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[4],
    paddingVertical: fiticianTokens.spacing[3],
  },
  selected: {
    backgroundColor: fiticianTokens.colors.aquaAtmosphere,
    borderColor: fiticianTokens.colors.aqua,
  },
  typeBadge: {
    ...RTL_TEXT,
    backgroundColor: fiticianTokens.colors.warningSurface,
    borderRadius: fiticianTokens.radii.pill,
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    overflow: "hidden",
    paddingHorizontal: fiticianTokens.spacing[2],
    paddingVertical: fiticianTokens.spacing[1],
  },
});
