import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { getNutritionCatalogueOptions } from "./api";
import type { NutritionCatalogueTarget } from "./types";

type CatalogueTargetMultiSelectProps<T extends NutritionCatalogueTarget> = {
  label: string;
  value: T[];
  onChange: (value: T[]) => void;
  placeholder?: string;
  language?: "fa" | "en";
  disabled?: boolean;
  includeDetails?: boolean;
};

function targetKey(target: Pick<NutritionCatalogueTarget, "target_type" | "target_id">): string {
  return `${target.target_type}:${target.target_id}`;
}

function targetTypeLabel(targetType: NutritionCatalogueTarget["target_type"], language: "fa" | "en") {
  if (language === "en") return targetType === "food" ? "Food" : "Meal";
  return targetType === "food" ? "ماده غذایی" : "وعده";
}

export function CatalogueTargetMultiSelect<T extends NutritionCatalogueTarget = NutritionCatalogueTarget>({
  label,
  value,
  onChange,
  placeholder = "جست‌وجو در فهرست مواد غذایی و وعده‌ها…",
  language = "fa",
  disabled = false,
  includeDetails = false,
}: CatalogueTargetMultiSelectProps<T>) {
  const inputId = useId();
  const listboxId = `${inputId}-options`;
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const requestSequence = useRef(0);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<NutritionCatalogueTarget[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!open) return undefined;
    const closeWhenClickedOutside = (event: PointerEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", closeWhenClickedOutside);
    return () => document.removeEventListener("pointerdown", closeWhenClickedOutside);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const sequence = requestSequence.current + 1;
    requestSequence.current = sequence;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(false);
      void getNutritionCatalogueOptions({ query: query.trim(), limit: 20 }, controller.signal)
        .then((response) => {
          if (requestSequence.current !== sequence) return;
          setOptions(response.items);
          setActiveIndex(response.items.length > 0 ? 0 : -1);
        })
        .catch(() => {
          if (controller.signal.aborted || requestSequence.current !== sequence) return;
          setOptions([]);
          setActiveIndex(-1);
          setError(true);
        })
        .finally(() => {
          if (requestSequence.current === sequence) setLoading(false);
        });
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, query, retry]);

  function selectOption(option: NutritionCatalogueTarget) {
    if (value.some((item) => targetKey(item) === targetKey(option))) {
      setQuery("");
      return;
    }
    const selected = (includeDetails ? { ...option, details: null } : option) as T;
    onChange([...value, selected]);
    setQuery("");
    setOpen(true);
    inputRef.current?.focus();
  }

  function removeOption(option: NutritionCatalogueTarget) {
    onChange(value.filter((item) => targetKey(item) !== targetKey(option)));
  }

  function onInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) setOpen(true);
      else if (options.length > 0) setActiveIndex((current) => (current + 1) % options.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (options.length > 0) setActiveIndex((current) => (current <= 0 ? options.length - 1 : current - 1));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const option = activeIndex >= 0 ? options[activeIndex] : undefined;
      if (option !== undefined) selectOption(option);
    }
  }

  return (
    <div ref={wrapperRef} className="catalogue-target-picker">
      <label className="catalogue-target-picker__label" htmlFor={inputId}>{label}</label>
      {value.length > 0 && (
        <ul className="catalogue-target-picker__selected" aria-label={language === "en" ? "Selected catalogue items" : "موارد انتخاب‌شده"}>
          {value.map((item) => (
            <li className="catalogue-target-picker__chip" key={targetKey(item)}>
              <span className="catalogue-target-picker__chip-text">
                <span>{item.name_fa}</span>
                <small>{targetTypeLabel(item.target_type, language)}</small>
              </span>
              <button
                type="button"
                className="catalogue-target-picker__remove"
                aria-label={language === "en" ? `Remove ${item.name_fa}` : `حذف ${item.name_fa}`}
                disabled={disabled}
                onClick={() => removeOption(item)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="catalogue-target-picker__control">
        <input
          ref={inputRef}
          id={inputId}
          className="catalogue-target-picker__input"
          type="search"
          role="combobox"
          value={query}
          disabled={disabled}
          placeholder={placeholder}
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-expanded={open}
          aria-haspopup="listbox"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onKeyDown={onInputKeyDown}
        />
      </div>
      {open && (
        <div className="catalogue-target-picker__menu">
          {loading && <p className="catalogue-target-picker__state" role="status">{language === "en" ? "Searching…" : "در حال جست‌وجو…"}</p>}
          {!loading && error && (
            <div className="catalogue-target-picker__state catalogue-target-picker__state--error" role="alert">
              <span>{language === "en" ? "Catalogue search failed." : "جست‌وجوی فهرست انجام نشد."}</span>
              <button type="button" onClick={() => setRetry((current) => current + 1)}>{language === "en" ? "Retry" : "تلاش دوباره"}</button>
            </div>
          )}
          {!loading && !error && options.length === 0 && (
            <p className="catalogue-target-picker__state">{language === "en" ? "No verified catalogue match." : "مورد تأییدشده‌ای پیدا نشد."}</p>
          )}
          {!loading && !error && options.length > 0 && (
            <ul id={listboxId} className="catalogue-target-picker__options" role="listbox" aria-label={label}>
              {options.map((option, index) => {
                const selected = value.some((item) => targetKey(item) === targetKey(option));
                return (
                  <li key={targetKey(option)} role="option" aria-selected={selected}>
                    <button
                      type="button"
                      className={`catalogue-target-picker__option ${index === activeIndex ? "is-active" : ""} ${selected ? "is-selected" : ""}`}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => selectOption(option)}
                    >
                      {option.image_url && <img src={option.image_url} alt="" aria-hidden="true" />}
                      <span className="catalogue-target-picker__option-copy">
                        <strong>{option.name_fa}</strong>
                        {option.name_en && <small>{option.name_en}</small>}
                      </span>
                      <span className="catalogue-target-picker__type-badge">{targetTypeLabel(option.target_type, language)}</span>
                      {selected && <span aria-hidden="true">✓</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
