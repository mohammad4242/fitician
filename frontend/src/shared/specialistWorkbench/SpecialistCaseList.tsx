import type { ReactNode } from "react";

import type { SpecialistSortOption } from "./types";

import "./specialistWorkbench.css";

export type SpecialistCaseListProps<T> = {
  readonly emptyDescription: string;
  readonly emptyTitle: string;
  readonly fa?: boolean;
  readonly items: readonly T[];
  readonly loading?: boolean;
  readonly loadingLabel?: string;
  readonly onSearchChange: (value: string) => void;
  readonly onSortChange: (value: string) => void;
  readonly renderItem: (item: T) => ReactNode;
  readonly searchLabel: string;
  readonly searchPlaceholder?: string;
  readonly searchValue: string;
  readonly sortLabel: string;
  readonly sortOptions: readonly SpecialistSortOption[];
  readonly sortValue: string;
};

export function SpecialistCaseList<T>({
  emptyDescription,
  emptyTitle,
  fa = false,
  items,
  loading = false,
  loadingLabel,
  onSearchChange,
  onSortChange,
  renderItem,
  searchLabel,
  searchPlaceholder,
  searchValue,
  sortLabel,
  sortOptions,
  sortValue,
}: SpecialistCaseListProps<T>) {
  return (
    <section className="specialist-case-list" aria-label={fa ? "پرونده‌ها" : "Cases"} dir={fa ? "rtl" : "ltr"}>
      <div className="specialist-case-list__controls">
        <label>
          <span>{searchLabel}</span>
          <input
            type="search"
            value={searchValue}
            placeholder={searchPlaceholder}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>
        <label>
          <span>{sortLabel}</span>
          <select value={sortValue} onChange={(event) => onSortChange(event.target.value)}>
            {sortOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>
      {loading ? (
        <p className="specialist-case-list__state" role="status">{loadingLabel ?? (fa ? "در حال دریافت پرونده‌ها…" : "Loading cases…")}</p>
      ) : items.length === 0 ? (
        <div className="specialist-case-list__empty" role="status">
          <strong>{emptyTitle}</strong>
          {emptyDescription ? <p>{emptyDescription}</p> : null}
        </div>
      ) : (
        <ul className="specialist-case-list__items" dir={fa ? "rtl" : "ltr"}>
          {items.map(renderItem)}
        </ul>
      )}
    </section>
  );
}
