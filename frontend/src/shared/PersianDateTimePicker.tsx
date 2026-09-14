import { useId, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  isoTimestampToTehranJalaliParts,
  tehranJalaliDateTimeToIso,
  type JalaliDateTimeParts,
} from "@fitician/core/iran-calendar";

import {
  formatPersianJalaliDateTime,
  jalaliDateTimePartsFromValue,
  timestampIsInRange,
  toDateTimeLocalValue,
  dateTimeLocalValueToIso,
} from "./datePickerUtils";
import { JalaliDateFields, PickerActions } from "./PersianDatePicker";
import "./datePickers.css";

export type PersianDateTimePickerProps = {
  value: string | null;
  onChange: (isoTimestamp: string | null) => void;
  min?: string;
  max?: string;
  disabled?: boolean;
  id?: string;
  label?: string;
  ariaLabel?: string;
  error?: string;
  allowClear?: boolean;
};

export function PersianDateTimePicker({
  value,
  onChange,
  min,
  max,
  disabled = false,
  id: providedId,
  label,
  ariaLabel,
  error,
  allowClear = true,
}: PersianDateTimePickerProps) {
  const { i18n } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const generatedId = useId().replaceAll(":", "");
  const id = providedId ?? generatedId;
  const panelId = `${id}-panel`;
  const errorId = `${id}-error`;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<JalaliDateTimeParts>(() => jalaliDateTimePartsFromValue(value ?? "", min ?? max));
  const [validationError, setValidationError] = useState<string | null>(null);
  const displayValue = getDisplayValue(value);
  const copy = english
    ? { cancel: "Cancel", clear: "Clear", confirm: "Select", invalid: "Select a valid Tehran date and time", label: "Date and time", placeholder: "Select date and time" }
    : { cancel: "لغو", clear: "پاک کردن", confirm: "انتخاب", invalid: "تاریخ و ساعت معتبر تهران را انتخاب کنید", label: "تاریخ و ساعت", placeholder: "انتخاب تاریخ و ساعت" };
  const accessibleLabel = ariaLabel ?? label ?? copy.label;

  function openPicker() {
    setDraft(jalaliDateTimePartsFromValue(value ?? "", min ?? max));
    setValidationError(null);
    setOpen(true);
  }

  function confirm() {
    try {
      const nextValue = tehranJalaliDateTimeToIso(draft);
      if (!timestampIsInRange(nextValue, min, max)) throw new RangeError(copy.invalid);
      onChange(nextValue);
      setOpen(false);
      setValidationError(null);
    } catch {
      setValidationError(copy.invalid);
    }
  }

  function clear() {
    onChange(null);
    setOpen(false);
    setValidationError(null);
  }

  if (english) {
    return (
      <div className="fitician-date-time-picker">
        {label && <label className="fitician-date-time-picker__label" htmlFor={id}>{label}</label>}
        <input
          aria-describedby={error ? errorId : undefined}
          aria-invalid={Boolean(error)}
          aria-label={ariaLabel}
          className="fitician-date-time-picker__native"
          disabled={disabled}
          id={id}
          max={toDateTimeLocalValue(max)}
          min={toDateTimeLocalValue(min)}
          onChange={(event) => onChange(event.currentTarget.value === "" ? null : dateTimeLocalValueToIso(event.currentTarget.value))}
          type="datetime-local"
          value={toDateTimeLocalValue(value)}
        />
        {allowClear && value && (
          <button className="fitician-date-time-picker__action fitician-date-time-picker__action--clear" onClick={clear} type="button">
            {copy.clear}
          </button>
        )}
        {error && <p className="fitician-date-time-picker__error" id={errorId}>{error}</p>}
      </div>
    );
  }

  return (
    <div className="fitician-date-time-picker">
      {label && <span className="fitician-date-time-picker__label" id={`${id}-label`}>{label}</span>}
      <button
        aria-controls={panelId}
        aria-describedby={error ? errorId : undefined}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-invalid={Boolean(error)}
        aria-label={accessibleLabel}
        className="fitician-date-time-picker__trigger"
        disabled={disabled}
        id={id}
        onClick={openPicker}
        onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
        type="button"
      >
        <span className={displayValue ? undefined : "fitician-date-time-picker__placeholder"}>
          {displayValue ?? copy.placeholder}
        </span>
        <span aria-hidden="true" className="fitician-date-time-picker__icon">◷</span>
      </button>
      {open && (
        <div
          aria-labelledby={label ? `${id}-label` : undefined}
          className="fitician-date-time-picker__panel"
          id={panelId}
          onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
          role="dialog"
          tabIndex={-1}
        >
          <JalaliDateFieldsWithTime max={max} min={min} onChange={setDraft} parts={draft} />
          <PickerActions
            cancelLabel={copy.cancel}
            clearLabel={copy.clear}
            confirmLabel={copy.confirm}
            onCancel={() => setOpen(false)}
            onClear={allowClear ? clear : undefined}
            onConfirm={confirm}
          />
          {validationError && <p className="fitician-date-time-picker__error" role="alert">{validationError}</p>}
        </div>
      )}
      {error && <p className="fitician-date-time-picker__error" id={errorId}>{error}</p>}
    </div>
  );

  function getDisplayValue(isoValue: string | null): string | null {
    if (!isoValue) return null;
    try {
      return formatPersianJalaliDateTime(isoTimestampToTehranJalaliParts(isoValue));
    } catch {
      return null;
    }
  }
}

function JalaliDateFieldsWithTime({
  parts,
  onChange,
  min,
  max,
}: {
  parts: JalaliDateTimeParts;
  onChange: (parts: JalaliDateTimeParts) => void;
  min?: string;
  max?: string;
}) {
  return (
    <>
      <JalaliDateFields
        labelPrefix="تاریخ"
        max={max}
        min={min}
        onChange={(date) => onChange({ ...parts, ...date })}
        parts={parts}
      />
      <div className="fitician-date-time-picker__time">
        <label className="fitician-date-time-picker__field">
          <span>ساعت</span>
          <input
            aria-label="ساعت"
            inputMode="numeric"
            max={23}
            min={0}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onChange({ ...parts, hour: Number(event.currentTarget.value) })}
            type="number"
            value={parts.hour}
          />
        </label>
        <label className="fitician-date-time-picker__field">
          <span>دقیقه</span>
          <input
            aria-label="دقیقه"
            inputMode="numeric"
            max={59}
            min={0}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onChange({ ...parts, minute: Number(event.currentTarget.value) })}
            type="number"
            value={parts.minute}
          />
        </label>
      </div>
    </>
  );
}
