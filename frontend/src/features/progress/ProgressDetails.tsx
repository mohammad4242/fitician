import { useState } from "react";
import {
  calorieSeries,
  difficultyLabels,
  progressCopy,
  progressCount,
  progressDate,
  progressMetrics,
  progressNumber,
  progressPresentationCopy,
  recoveryLabels,
  recoverySeries,
  selfReportedProgressLabels,
  type BodyMetric,
  type ProgressOverview,
  type ProgressTab,
} from "@fitician/core";
import { TrendChart } from "./TrendChart";
import { MeasurementForm } from "./MeasurementForm";
type Props = {
  tab: ProgressTab;
  data: ProgressOverview;
  language: "fa" | "en";
  onSaved: () => void;
};
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="progress-stat">
      <span>{label}</span>
      <strong dir="auto">{value}</strong>
    </div>
  );
}
export default function ProgressDetails({
  tab,
  data,
  language,
  onSaved,
}: Props) {
  const c = progressCopy[language],
    p = progressPresentationCopy[language],
    n = (v: number | null | undefined, signed = false) =>
      progressNumber(v, language, signed),
    date = (v: string) => progressDate(v, language, data.context.timezone);
  const [metric, setMetric] = useState<BodyMetric>("weight"),
    [bodyIndex, setBodyIndex] = useState<number | null>(null),
    [dayIndex, setDayIndex] = useState<number | null>(null),
    [recording, setRecording] = useState(false);
  if (tab === "body") {
    const body = data.body_measurements[metric],
      point = body.points[bodyIndex ?? body.points.length - 1];
    return (
      <div className="progress-card progress-detail">
        <div className="progress-metric-selector" aria-label={c.body}>
          {progressMetrics.map((key) => (
            <button
              key={key}
              aria-pressed={metric === key}
              onClick={() => {
                setMetric(key);
                setBodyIndex(null);
              }}
            >
              {c[key]}
            </button>
          ))}
        </div>
        <h2>{c[metric]}</h2>
        {body.points.length ? (
          <>
            <div className="progress-detail-metric">
              <strong>
                <bdi dir="ltr">
                  {n(body.latest_value)} <small>{body.unit}</small>
                </bdi>
              </strong>
              {body.points.length > 1 && body.delta !== null && (
                <span>
                  <bdi dir="ltr">
                    {n(body.delta, true)} {body.unit}
                  </bdi>{" "}
                  · {c[data.context.preset]}
                </span>
              )}
            </div>
            {body.points.length > 1 ? (
              <TrendChart
                key={metric}
                series={[
                  body.points.map((p) => ({
                    date: p.recorded_at,
                    value: p.value,
                  })),
                ]}
                labels={[c[metric]]}
                unit={body.unit}
                language={language}
                onSelect={setBodyIndex}
              />
            ) : (
              <p className="progress-note">{c.onePoint}</p>
            )}
            {point && (
              <div className="progress-point" aria-live="polite">
                <time>{date(point.recorded_at)}</time>
                <b>
                  <bdi dir="ltr">
                    {n(point.value)} {body.unit}
                  </bdi>
                </b>
                <span>{point.source === "manual" ? c.manual : c.legacy}</span>
              </div>
            )}
          </>
        ) : (
          <p className="progress-empty">{c.noBody}</p>
        )}
        <button
          className="progress-secondary-cta"
          onClick={() => setRecording(!recording)}
        >
          {recording ? c.close : c.record}
        </button>
        {recording && (
          <MeasurementForm
            language={language}
            onSaved={() => {
              setRecording(false);
              onSaved();
            }}
          />
        )}
        <details>
          <summary>{c.details}</summary>
          <p>{c.legacyBody}</p>
        </details>
      </div>
    );
  }
  if (tab === "calories" && data.nutrition) {
    const t = data.nutrition,
      day =
        t.series[
          dayIndex ??
            Math.max(
              0,
              t.series.findLastIndex((p) => p.date <= data.context.today),
            )
        ];
    return (
      <div className="progress-card progress-detail">
        <h2>{p.caloriesTitle}</h2>
        <div className="progress-stats">
          <Stat
            label={c.coverage}
            value={progressCount(
              t.logged_days,
              t.elapsed_days,
              language,
              "days",
            )}
          />
          <Stat label={c.alignment} value={n(t.adherent_days)} />
          <Stat
            label={p.averageDifference}
            value={`${n(t.average_difference_kcal, true)} kcal`}
          />
        </div>
        <TrendChart
          series={calorieSeries(t)}
          labels={[c.target, c.actual]}
          unit="kcal"
          language={language}
          onSelect={setDayIndex}
        />
        {day && (
          <div className="progress-point" aria-live="polite">
            <time>
              {date(day.date)}
              {day.in_progress ? ` · ${c.inProgress}` : ""}
            </time>
            <span>
              {c.target}:{" "}
              <b>
                {day.target_kcal == null
                  ? c.missingTarget
                  : `${n(day.target_kcal)} kcal`}
              </b>
            </span>
            <span>
              {day.actual_kcal == null ? (
                day.logging_state === "invalid" ? (
                  c.invalidIntake
                ) : (
                  c.noIntake
                )
              ) : (
                <>
                  {c.actual}: <b>{n(day.actual_kcal)} kcal</b>
                </>
              )}
            </span>
            {day.target_kcal != null && day.actual_kcal != null && (
              <b>{n(day.actual_kcal - day.target_kcal, true)} kcal</b>
            )}
          </div>
        )}
        <details>
          <summary>{c.details}</summary>
          <p>{c.nutritionRule}</p>
        </details>
      </div>
    );
  }
  if (tab === "training" && data.training) {
    const t = data.training,
      max = Math.max(1, ...t.weeks.flatMap((w) => [w.planned, w.completed]));
    return (
      <div className="progress-card progress-detail">
        <h2>{c.training}</h2>
        <div className="progress-stats">
          <Stat
            label={p.completed}
            value={progressCount(
              t.completed_sessions,
              t.due_sessions,
              language,
              "sessions",
            )}
          />
          <Stat
            label={p.adherence}
            value={
              t.adherence_percent == null ? "—" : n(t.adherence_percent) + "%"
            }
          />
        </div>
        {!t.planned_sessions ? (
          <p className="progress-empty">{c.noTraining}</p>
        ) : (
          <>
            <div
              className="progress-training-chart"
              role="img"
              aria-label={t.weeks
                .map(
                  (w) =>
                    `${date(w.start_date)}: ${p.planned} ${n(w.planned)}, ${p.completed} ${n(w.completed)}`,
                )
                .join("; ")}
            >
              {t.weeks.map((w) => (
                <div key={w.start_date} className="progress-training-week">
                  <span className="progress-training-bars">
                    <i style={{ height: `${(w.planned / max) * 100}%` }} />
                    <i style={{ height: `${(w.completed / max) * 100}%` }} />
                  </span>
                  <b>
                    {n(w.completed)} / {n(w.planned)}
                  </b>
                  <time>{date(w.start_date)}</time>
                </div>
              ))}
            </div>
            <div className="progress-chart__legend">
              <span className="progress-chart__legend-planned">
                {p.planned}
              </span>
              <span>{p.completed}</span>
            </div>
          </>
        )}
        <div className="progress-small-stats">
          <span>
            {p.skipped} <b>{n(t.skipped_sessions)}</b>
          </span>
          <span>
            {p.rescheduled} <b>{n(t.rescheduled_sessions)}</b>
          </span>
          <span>
            {p.overdue} <b>{n(t.overdue_sessions)}</b>
          </span>
        </div>
        <details>
          <summary>{c.details}</summary>
          <p>{c.trainingRule}</p>
          {t.self_reported_cycle_progress && (
            <p>
              {c.selfReported}:{" "}
              {
                selfReportedProgressLabels[language][
                  t.self_reported_cycle_progress
                ]
              }
            </p>
          )}
        </details>
      </div>
    );
  }
  if (tab === "recovery") {
    const latest = data.recovery.at(-1);
    return (
      <div className="progress-card progress-detail">
        <h2>{c.recovery}</h2>
        {latest ? (
          <>
            <div className="progress-stats">
              <Stat
                label={c.recovery}
                value={recoveryLabels[language][latest.recovery]}
              />
              <Stat
                label={p.difficulty}
                value={difficultyLabels[language][latest.difficulty]}
              />
            </div>
            {data.recovery.length > 1 && (
              <TrendChart
                series={recoverySeries(data)}
                labels={[c.recovery]}
                unit=""
                language={language}
                valueLabels={{
                  1: recoveryLabels[language].poor,
                  2: recoveryLabels[language].average,
                  3: recoveryLabels[language].good,
                }}
              />
            )}
            <div className="progress-history">
              {data.recovery
                .slice()
                .reverse()
                .map((r, i) => (
                  <div key={r.recorded_at + i}>
                    <time>{date(r.recorded_at)}</time>
                    <b>{recoveryLabels[language][r.recovery]}</b>
                    <span>{difficultyLabels[language][r.difficulty]}</span>
                  </div>
                ))}
            </div>
          </>
        ) : (
          <p className="progress-empty">{p.noRecovery}</p>
        )}
      </div>
    );
  }
  return <p className="progress-empty">{p.notAvailable}</p>;
}
