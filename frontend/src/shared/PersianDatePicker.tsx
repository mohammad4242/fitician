import { useId, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  daysInJalaliMonth,
  isoDateToJalaliParts,
  jalaliPartsToIsoDate,
  PERSIAN_MONTH_NAMES_FA,
  type JalaliDateParts,
} from "@fitician/core/iran-calendar";

import {
  dateOnlyIsInRange,
  daysForJalaliMonth,
  formatPersianJalaliDate,
  formatPersianNumber,
  jalaliDatePartsFromValue,
  jalaliYearOptions,
} from "./datePickerUtils";
import "./datePickers.css";

export type PersianDatePickerProps = {
  value: string;
  onChange: (isoDate: string) => void;
  min?: string;
  max?: string;
  disabled?: boolean;
  id?: string;
  label?: string;
  ariaLabel?: string;
  error?: string;
  allowClear?: boolean;
};

type JalaliDateFieldsProps = {
  parts: JalaliDateParts;
  onChange: (parts: JalaliDateParts) => void;
  min?: string;
  max?: string;
  labelPrefix?: string;
};

export function JalaliDateFields({
  parts,
  onChange,
  min,
  max,
  labelPrefix = "تاریخ",
}: JalaliDateFieldsProps) {
  const dayCount = daysForJalaliMonth(parts.year, parts.month);
  const years = jalaliYearOptions(parts, min, max);

  function updateMonth(event: ChangeEvent<HTMLSelectElement>) {
    const month = Number(event.currentTarget.value);
    onChange({ ...parts, month, day: Math.min(parts.day, daysInJalaliMonth(parts.year, month)) });
  }

  function updateYear(event: ChangeEvent<HTMLSelectElement>) {
    const year = Number(event.currentTarget.value);
    onChange({ ...parts, year, day: Math.min(parts.day, daysInJalaliMonth(year, parts.month)) });
  }

  return (
    <div className="fitician-date-picker__fields">
      <label className="fitician-date-picker__field">
        <span>{`${labelPrefix} - روز`}</span>
        <select
          aria-label={`${labelPrefix} - روز`}
          onChange={(event) => onChange({ ...parts, day: Number(event.currentTarget.value) })}
          value={parts.day}
        >
          {Array.from({ length: dayCount }, (_, index) => index + 1).map((day) => (
            <option key={day} value={day}>{formatPersianNumber(day)}</option>
          ))}
        </select>
      </label>
      <label className="fitician-date-picker__field">
        <span>{`${labelPrefix} - ماه`}</span>
        <select aria-label={`${labelPrefix} - ماه`} onChange={updateMonth} value={parts.month}>
          {Array.from({ length: 12 }, (_, index) => index + 1).map((month) => (
            <option key={month} value={month}>{PERSIAN_MONTH_NAMES_FA[month - 1]}</option>
          ))}
        </select>
      </label>
      <label className="fitician-date-picker__field">
        <span>{`${labelPrefix} - سال`}</span>
        <select aria-label={`${labelPrefix} - سال`} onChange={updateYear} value={parts.year}>
          {years.map((year) => (
            <option key={year} value={year}>{formatPersianNumber(year)}</option>
          ))}
        </select>
      </label>
    </div>
  );
}

type PickerActionsProps = {
  onCancel: () => void;
  onConfirm: () => void;
  onClear?: () => void;
  confirmLabel: string;
  cancelLabel: string;
  clearLabel: string;
};

export function PickerActions({
  onCancel,
  onConfirm,
  onClear,
  confirmLabel,
  cancelLabel,
  clearLabel,
}: PickerActionsProps) {
  return (
    <div className="fitician-date-picker__actions">
      <button className="fitician-date-picker__action" onClick={onCancel} type="button">
        {cancelLabel}
      </button>
      <button className="fitician-date-picker__action fitician-date-picker__action--primary" onClick={onConfirm} type="button">
        {confirmLabel}
      </button>
      {onClear && (
        <button className="fitician-date-picker__action fitician-date-picker__action--clear" onClick={onClear} type="button">
          {clearLabel}
        </button>
      )}
    </div>
  );
}

export function PersianDatePicker({
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
}: PersianDatePickerProps) {
  const { i18n } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const generatedId = useId().replaceAll(":", "");
  const id = providedId ?? generatedId;
  const panelId = `${id}-panel`;
  const errorId = `${id}-error`;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<JalaliDateParts>(() => jalaliDatePartsFromValue(value, min ?? max));
  const [validationError, setValidationError] = useState<string | null>(null);
  const displayValue = getDisplayValue(value);
  const copy = english
    ? { cancel: "Cancel", clear: "Clear", confirm: "Select", invalid: "Select a valid date", label: "Date", placeholder: "Select a date" }
    : { cancel: "لغو", clear: "پاک کردن", confirm: "انتخاب", invalid: "یک تاریخ معتبر انتخاب کنید", label: "تاریخ", placeholder: "انتخاب تاریخ" };
  const accessibleLabel = ariaLabel ?? label ?? copy.label;

  function openPicker() {
    setDraft(jalaliDatePartsFromValue(value, min ?? max));
    setValidationError(null);
    setOpen(true);
  }

  function confirm() {
    try {
      const nextValue = jalaliPartsToIsoDate(draft);
      if (!dateOnlyIsInRange(nextValue, min, max)) throw new RangeError(copy.invalid);
      onChange(nextValue);
      setOpen(false);
      setValidationError(null);
    } catch {
      setValidationError(copy.invalid);
    }
  }

  function clear() {
    onChange("");
    setOpen(false);
    setValidationError(null);
  }

  if (english) {
    return (
      <div className="fitician-date-picker">
        {label && <label className="fitician-date-picker__label" htmlFor={id}>{label}</label>}
        <input
          aria-describedby={error ? errorId : undefined}
          aria-invalid={Boolean(error)}
          aria-label={ariaLabel}
          className="fitician-date-picker__native"
          disabled={disabled}
          id={id}
          max={max}
          min={min}
          onChange={(event) => onChange(event.currentTarget.value)}
          type="date"
          value={value}
        />
        {allowClear && value && (
          <button className="fitician-date-picker__action fitician-date-picker__action--clear" onClick={clear} type="button">
            {copy.clear}
          </button>
        )}
        {error && <p className="fitician-date-picker__error" id={errorId}>{error}</p>}
      </div>
    );
  }

  return (
    <div className="fitician-date-picker">
      {label && <span className="fitician-date-picker__label" id={`${id}-label`}>{label}</span>}
      <button
        aria-controls={panelId}
        aria-describedby={error ? errorId : undefined}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-invalid={Boolean(error)}
        aria-label={accessibleLabel}
        className="fitician-date-picker__trigger"
        disabled={disabled}
        id={id}
        onClick={openPicker}
        onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
        type="button"
      >
        <span className={displayValue ? undefined : "fitician-date-picker__placeholder"}>
          {displayValue ?? copy.placeholder}
        </span>
        <span aria-hidden="true" className="fitician-date-picker__icon">▣</span>
      </button>
      {open && (
        <div
          aria-labelledby={label ? `${id}-label` : undefined}
          className="fitician-date-picker__panel"
          id={panelId}
          onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
          role="dialog"
          tabIndex={-1}
        >
          <JalaliDateFields
            labelPrefix={label ?? copy.label}
            max={max}
            min={min}
            onChange={setDraft}
            parts={draft}
          />
          <PickerActions
            cancelLabel={copy.cancel}
            clearLabel={copy.clear}
            confirmLabel={copy.confirm}
            onCancel={() => setOpen(false)}
            onClear={allowClear ? clear : undefined}
            onConfirm={confirm}
          />
          {validationError && <p className="fitician-date-picker__error" role="alert">{validationError}</p>}
        </div>
      )}
      {error && <p className="fitician-date-picker__error" id={errorId}>{error}</p>}
    </div>
  );

  function getDisplayValue(isoValue: string): string | null {
    if (isoValue === "") return null;
    try {
      return formatPersianJalaliDate(isoDateToJalaliParts(isoValue));
    } catch {
      return null;
    }
  }
}
