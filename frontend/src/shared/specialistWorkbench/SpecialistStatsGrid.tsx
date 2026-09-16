import type { SpecialistStat } from "./types";

import "./specialistWorkbench.css";

type SpecialistStatsGridProps = {
  readonly stats: readonly SpecialistStat[];
  readonly title?: string;
};

export function SpecialistStatsGrid({ stats, title }: SpecialistStatsGridProps) {
  return (
    <section className="specialist-stats" aria-label={title} data-testid="specialist-stats-grid">
      {title ? <h2>{title}</h2> : null}
      <div className="specialist-stats__grid">
        {stats.map((stat) => (
          <article className={`specialist-stat specialist-stat--${stat.tone ?? "neutral"}`} key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            {stat.hint ? <small>{stat.hint}</small> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
