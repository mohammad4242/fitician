import { useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import {
  createMessageRequestId,
  progressCopy,
  progressMetrics,
  type BodyMetric,
  type MeasurementInput,
  type createProgressApi,
} from "@fitician/core";
import { Button } from "../ui/components/Button";
import { TextField } from "../ui/components/Input";
import { fiticianTokens as tokens } from "../ui/tokens";
export function MeasurementForm({
  language,
  api,
  onSaved,
}: {
  language: "fa" | "en";
  api: ReturnType<typeof createProgressApi>;
  onSaved: () => void;
}) {
  const c = progressCopy[language],
    [values, setValues] = useState<Record<BodyMetric, string>>({
      weight: "",
      waist: "",
      hip: "",
      shoulder_width: "",
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false),
    pending = useRef<{ key: string; id: string } | null>(null),
    sending = useRef(false);
  async function save() {
    if (sending.current) return;
    const fields = {
      weight: "weight_kg",
      waist: "waist_circumference_cm",
      hip: "hip_circumference_cm",
      shoulder_width: "shoulder_width_cm",
    } as const;
    const entered = Object.fromEntries(
      progressMetrics
        .filter((k) => values[k].trim() !== "")
        .map((k) => [
          fields[k],
          Number(
            values[k]
              .replace(/[۰-۹]/g, (x) => String(x.charCodeAt(0) - 1776))
              .replace(/[٠-٩]/g, (x) => String(x.charCodeAt(0) - 1632))
              .replace("٫", "."),
          ),
        ]),
    );
    if (
      !Object.keys(entered).length ||
      Object.values(entered).some((v) => !Number.isFinite(v))
    ) {
      setError(true);
      return;
    }
    const key = JSON.stringify(entered);
    if (pending.current?.key !== key)
      pending.current = { key, id: createMessageRequestId() };
    sending.current = true;
    setBusy(true);
    setError(false);
    try {
      await api.recordMeasurement({
        ...entered,
        request_id: pending.current.id,
      } as MeasurementInput);
      onSaved();
    } catch {
      setError(true);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  return (
    <View style={styles.stack}>
      <Text style={styles.text}>{c.measurementHint}</Text>
      {progressMetrics.map((metric) => (
        <TextField
          key={metric}
          label={`${c[metric]} (${metric === "weight" ? "kg" : "cm"})`}
          keyboardType="decimal-pad"
          value={values[metric]}
          editable={!busy}
          onChangeText={(value) =>
            setValues((prev) => ({ ...prev, [metric]: value }))
          }
        />
      ))}
      {error && (
        <Text accessibilityRole="alert" style={styles.text}>
          {c.recordError}
        </Text>
      )}
      <Button
        label={c.save}
        loading={busy}
        disabled={!Object.values(values).some(Boolean)}
        onPress={() => void save()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  stack: { gap: 16 },
  text: {
    color: tokens.colors.muted,
    fontFamily: tokens.typography.fontFamily.bodyPersian,
    fontSize: 13,
    lineHeight: 24,
  },
});
