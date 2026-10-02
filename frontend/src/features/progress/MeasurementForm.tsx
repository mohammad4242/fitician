import { useRef, useState } from "react";
import {
  createMessageRequestId,
  progressCopy,
  progressMetrics,
  type BodyMetric,
  type MeasurementInput,
} from "@fitician/core";
import { progressApi as api } from "./api";
export function MeasurementForm({
  language,
  onSaved,
}: {
  language: "fa" | "en";
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
        .filter((k) => values[k] !== "")
        .map((k) => [fields[k], Number(values[k])]),
    );
    if (!Object.keys(entered).length) return;
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
    <form
      className="progress-measurement-form"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <p>{c.measurementHint}</p>
      {progressMetrics.map((metric) => (
        <label key={metric}>
          {c[metric]} ({metric === "weight" ? "kg" : "cm"})
          <input
            type="number"
            inputMode="decimal"
            min={
              metric === "weight" ? 35 : metric === "shoulder_width" ? 20 : 40
            }
            max={
              metric === "weight" ? 300 : metric === "shoulder_width" ? 80 : 250
            }
            step="0.01"
            value={values[metric]}
            disabled={busy}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, [metric]: e.target.value }))
            }
          />
        </label>
      ))}
      {error && <p role="alert">{c.recordError}</p>}
      <button disabled={busy || !Object.values(values).some(Boolean)}>
        {busy ? c.loading : c.save}
      </button>
    </form>
  );
}
