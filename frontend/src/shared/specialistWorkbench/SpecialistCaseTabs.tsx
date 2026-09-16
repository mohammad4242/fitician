import type { KeyboardEvent } from "react";

import "./specialistWorkbench.css";

export type SpecialistCaseTabOption<T extends string> = {
  readonly id: T;
  readonly label: string;
};

type SpecialistCaseTabsProps<T extends string> = {
  readonly activeTab: T;
  readonly ariaLabel: string;
  readonly className?: string;
  readonly fa: boolean;
  readonly onChange: (tab: T) => void;
  readonly panelIdPrefix: string;
  readonly tabIdPrefix: string;
  readonly tabs: readonly SpecialistCaseTabOption<T>[];
};

export function SpecialistCaseTabs<T extends string>({
  activeTab,
  ariaLabel,
  className,
  fa,
  onChange,
  panelIdPrefix,
  tabIdPrefix,
  tabs,
}: SpecialistCaseTabsProps<T>) {
  function moveFocus(event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    let targetIndex: number | null = null;
    if (event.key === "Home") targetIndex = 0;
    if (event.key === "End") targetIndex = tabs.length - 1;
    if (direction !== 0) targetIndex = (currentIndex + (fa ? -direction : direction) + tabs.length) % tabs.length;
    if (targetIndex === null || !tabs[targetIndex]) return;
    event.preventDefault();
    const target = event.currentTarget.parentElement?.children[targetIndex] as HTMLButtonElement | undefined;
    target?.focus();
    onChange(tabs[targetIndex].id);
  }

  return (
    <nav aria-label={ariaLabel} className={["specialist-case-tabs", className].filter(Boolean).join(" ")} role="tablist">
      {tabs.map((tab, index) => (
        <button
          aria-controls={`${panelIdPrefix}-${tab.id}`}
          aria-selected={activeTab === tab.id}
          id={`${tabIdPrefix}-${tab.id}`}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => moveFocus(event, index)}
          role="tab"
          tabIndex={activeTab === tab.id ? 0 : -1}
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
