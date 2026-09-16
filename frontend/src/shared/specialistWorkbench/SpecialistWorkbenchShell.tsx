import type { ReactNode } from "react";

import { SpecialistWorkbenchNav } from "./SpecialistWorkbenchNav";
import { SpecialistStatsGrid } from "./SpecialistStatsGrid";
import type {
  SpecialistNavCount,
  SpecialistRole,
  SpecialistSection,
  SpecialistStat,
} from "./types";

import "./specialistWorkbench.css";

type SpecialistWorkbenchShellProps = {
  readonly activeSection: SpecialistSection;
  readonly children: ReactNode;
  readonly counts?: SpecialistNavCount;
  readonly description?: string;
  readonly error?: ReactNode;
  readonly fa: boolean;
  readonly headerAction?: ReactNode;
  readonly onSectionChange: (section: SpecialistSection) => void;
  readonly role: SpecialistRole;
  readonly stats?: readonly SpecialistStat[];
  readonly title: string;
};

export function SpecialistWorkbenchShell({
  activeSection,
  children,
  counts,
  description,
  error,
  fa,
  headerAction,
  onSectionChange,
  role,
  stats,
  title,
}: SpecialistWorkbenchShellProps) {
  return (
    <div className={`specialist-workbench-shell specialist-workbench-shell--${role}`} dir={fa ? "rtl" : "ltr"}>
      <main className="specialist-workbench-page">
        <header className="specialist-workbench-hero">
          <div>
            <p className="specialist-workbench-hero__eyebrow">{fa ? "فضای کاری تخصصی" : "Specialist workbench"}</p>
            <h1>{title}</h1>
            {description ? <p className="specialist-workbench-hero__description">{description}</p> : null}
          </div>
          {headerAction ? <div className="specialist-workbench-hero__action">{headerAction}</div> : null}
        </header>
        {error}
        <SpecialistWorkbenchNav
          activeSection={activeSection}
          counts={counts}
          fa={fa}
          onSectionChange={onSectionChange}
          role={role}
        />
        {stats ? <SpecialistStatsGrid stats={stats} /> : null}
        <section aria-live="polite" className="specialist-workbench-panel" data-section={activeSection} id="specialist-workbench-panel">
          {children}
        </section>
      </main>
    </div>
  );
}
