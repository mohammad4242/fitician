import type { KeyboardEvent } from "react";

import type {
  SpecialistNavCount,
  SpecialistRole,
  SpecialistSection,
} from "./types";
import { specialistSectionLabel, specialistSections } from "./specialistWorkbenchSections";

import "./specialistWorkbench.css";

type SpecialistWorkbenchNavProps = {
  readonly activeSection: SpecialistSection;
  readonly counts?: SpecialistNavCount;
  readonly fa: boolean;
  readonly onSectionChange: (section: SpecialistSection) => void;
  readonly role: SpecialistRole;
};

export function SpecialistWorkbenchNav({
  activeSection,
  counts,
  fa,
  onSectionChange,
  role,
}: SpecialistWorkbenchNavProps) {
  function moveFocus(event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      const targetIndex = event.key === "Home" ? 0 : specialistSections.length - 1;
      const target = event.currentTarget.parentElement?.children[targetIndex] as HTMLButtonElement | undefined;
      target?.focus();
      onSectionChange(specialistSections[targetIndex]);
      return;
    }
    if (direction === 0) return;
    event.preventDefault();
    const targetIndex = (currentIndex + (fa ? -direction : direction) + specialistSections.length) % specialistSections.length;
    const target = event.currentTarget.parentElement?.children[targetIndex] as HTMLButtonElement | undefined;
    target?.focus();
    onSectionChange(specialistSections[targetIndex]);
  }

  return (
    <nav className="specialist-workbench-nav" aria-label={fa ? "بخش‌های میز کار" : "Workbench sections"} data-specialist-role={role}>
      <div className="specialist-workbench-nav__tabs" role="tablist" aria-label={fa ? "بخش‌های میز کار" : "Workbench sections"}>
        {specialistSections.map((section, index) => {
          const count = counts?.[section];
          return (
            <button
              aria-controls="specialist-workbench-panel"
              aria-selected={activeSection === section}
              data-section={section}
              key={section}
              onClick={() => onSectionChange(section)}
              onKeyDown={(event) => moveFocus(event, index)}
              role="tab"
              tabIndex={activeSection === section ? 0 : -1}
              type="button"
            >
              <span>{specialistSectionLabel(section, fa)}</span>
              {count === undefined ? null : <small>{count.toLocaleString(fa ? "fa-IR" : "en-US")}</small>}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
