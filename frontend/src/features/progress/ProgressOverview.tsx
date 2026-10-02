import {
  chartGeometry,
  overviewCards,
  type OverviewCard,
  type ProgressOverview,
  type ProgressTab,
} from "@fitician/core";
export function MiniTrend({ card }: { card: OverviewCard }) {
  const maxCal = Math.max(
    1,
    ...card.series.flatMap((s) =>
      s.flatMap((p) => (p.value == null ? [] : [p.value])),
    ),
  );
  const chart = chartGeometry(
    card.series,
    220,
    115,
    card.tab === "calories"
      ? [0, maxCal * 1.1]
      : card.tab === "recovery"
        ? [1, 3]
        : undefined,
  );
  const max = Math.max(
    1,
    ...(card.bars ?? []).flatMap((w) => [w.planned, w.completed]),
  );
  return (
    <svg
      className={`progress-mini progress-mini--${card.tab}`}
      viewBox="40 10 180 88"
      aria-hidden="true"
      focusable="false"
    >
      {card.series.length > 0 && (
        <>
          <line
            x1="48"
            x2="206"
            y1="83"
            y2="83"
            className="progress-chart__grid"
          />
          {chart.lines.map((line, i) => (
            <g key={i} className={`progress-chart__series-${i}`}>
              {card.tab === "calories"
                ? line.points.map((p) => (
                    <line
                      key={p.index}
                      x1={p.x + (i ? 3 : -3)}
                      x2={p.x + (i ? 3 : -3)}
                      y1={83}
                      y2={p.y}
                      strokeWidth={4}
                      strokeLinecap="round"
                    />
                  ))
                : line.segments.map((points, j) => (
                    <polyline
                      key={j}
                      points={points.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill="none"
                      strokeWidth={2.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  ))}
              {card.tab !== "calories" &&
                line.points.map((p) => (
                  <circle key={p.index} cx={p.x} cy={p.y} r={3} />
                ))}
            </g>
          ))}
        </>
      )}
      {card.bars?.slice(-7).map((w, i, rows) => {
        const x = 55 + i * (148 / rows.length);
        return (
          <g key={i}>
            <rect
              x={x}
              y={83 - (w.planned / max) * 58}
              width={12}
              height={(w.planned / max) * 58}
              rx={4}
              fill="var(--fitician-line)"
            />
            <rect
              x={x + 2}
              y={83 - (w.completed / max) * 58}
              width={8}
              height={(w.completed / max) * 58}
              rx={3}
              fill="var(--fitician-aqua)"
            />
          </g>
        );
      })}
      {!card.series.length &&
        !card.bars?.length &&
        (card.status ? (
          <g>
            {(["poor", "average", "good"] as const).map((state, i) => (
              <rect
                key={state}
                x={65 + i * 40}
                y={45 - i * 9}
                width={25}
                height={20 + i * 9}
                rx={7}
                fill={
                  card.status === state
                    ? "var(--fitician-aqua)"
                    : "var(--fitician-line)"
                }
              />
            ))}
          </g>
        ) : (
          <g
            stroke="var(--fitician-muted)"
            strokeWidth={1.5}
            fill="none"
            opacity={0.5}
          >
            {card.tab === "analysis" ? (
              <>
                <rect x={85} y={25} width={58} height={51} rx={13} />
                <circle cx={114} cy={50} r={13} />
                <path d="M85 38h7m44 0h7M85 65h7m44 0h7" />
              </>
            ) : (
              <>
                <rect x={85} y={25} width={58} height={51} rx={13} />
                <line x1={104} y1={50} x2={124} y2={50} />
              </>
            )}
          </g>
        ))}
    </svg>
  );
}
export function ProgressOverview({
  data,
  language,
  onSelect,
}: {
  data: ProgressOverview;
  language: "fa" | "en";
  onSelect: (tab: ProgressTab) => void;
}) {
  return (
    <div className="progress-overview">
      {overviewCards(data, language).map((card) => (
        <button
          className="progress-overview-card"
          key={card.tab}
          onClick={() => onSelect(card.tab)}
          aria-label={`${card.title} · ${card.value} · ${card.support}`}
        >
          <span className="progress-overview-card__heading">
            <span>{card.title}</span>
            <span className="progress-chevron" aria-hidden="true">
              {language === "fa" ? "‹" : "›"}
            </span>
          </span>
          <span className="progress-overview-card__body">
            <span className="progress-overview-card__copy">
              <strong>{card.value}</strong>
              <span>{card.support}</span>
              {card.extra && <small>{card.extra}</small>}
            </span>
            <MiniTrend card={card} />
          </span>
        </button>
      ))}
    </div>
  );
}
