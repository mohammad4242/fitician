import type { ReactNode } from "react";

import { SpecialistStatusBadge } from "./SpecialistStatusBadge";
import type {
  SpecialistCaseHeaderMeta,
  SpecialistStatusContext,
} from "./types";

import "./specialistWorkbench.css";

type SpecialistCaseHeaderProps = {
  readonly avatar: ReactNode;
  readonly backLabel: string;
  readonly context: SpecialistStatusContext;
  readonly fa: boolean;
  readonly meta?: readonly SpecialistCaseHeaderMeta[];
  readonly name: string;
  readonly onBack: () => void;
  readonly status: string;
  readonly eyebrow: string;
};

export function SpecialistCaseHeader({
  avatar,
  backLabel,
  context,
  fa,
  meta = [],
  name,
  onBack,
  status,
  eyebrow,
}: SpecialistCaseHeaderProps) {
  return (
    <header className="specialist-case-header" data-testid="specialist-case-header">
      <button className="specialist-case-header__back" data-testid="specialist-case-back" onClick={onBack} type="button">
        <span aria-hidden="true">{fa ? "→" : "←"}</span>
        {backLabel}
      </button>
      <div className="specialist-case-header__identity">
        {avatar}
        <div>
          <small>{eyebrow}</small>
          <h2>{name}</h2>
        </div>
      </div>
      <SpecialistStatusBadge context={context} fa={fa} status={status} />
      {meta.length > 0 ? (
        <dl className="specialist-case-header__meta">
          {meta.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
        </dl>
      ) : null}
    </header>
  );
}
