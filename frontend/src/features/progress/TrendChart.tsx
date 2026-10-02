import { useState } from "react";
import { chartGeometry, type ChartDatum } from "@fitician/core";
export function TrendChart({
  series,
  labels,
  unit,
  language,
  onSelect,
}: {
  series: ChartDatum[][];
  labels: string[];
  unit: string;
  language: "fa" | "en";
  onSelect?: (index: number) => void;
}) {
  const chart = chartGeometry(series, 680, 245),
    [selected, setSelected] = useState<number | null>(null),
    format = (value: number) =>
      new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(
        value,
      ),
    date = (value: number) =>
      new Intl.DateTimeFormat(language, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(value);
  return (
    <figure className="progress-chart" dir="ltr">
      <svg
        viewBox="0 0 680 245"
        role="group"
        aria-label={labels.join(" / ") + " (" + unit + ")"}
      >
        {[0, 0.5, 1].map((f) => {
          const y =
              chart.padding.top +
              f * (chart.height - chart.padding.top - chart.padding.bottom),
            value = chart.maxY - f * (chart.maxY - chart.minY);
          return (
            <g key={f}>
              <line
                x1={chart.padding.left}
                y1={y}
                x2="666"
                y2={y}
                className="progress-chart__grid"
              />
              <text
                x="40"
                y={y + 4}
                textAnchor="end"
                className="progress-chart__label"
              >
                {format(value)}
              </text>
            </g>
          );
        })}
        <text x="48" y="236" className="progress-chart__label">
          {date(chart.minX)}
        </text>
        <text
          x="666"
          y="236"
          textAnchor="end"
          className="progress-chart__label"
        >
          {date(chart.maxX)}
        </text>
        {chart.lines.map((line, i) => (
          <g key={i} className={`progress-chart__series-${i}`}>
            {line.segments.map((points, j) => (
              <polyline
                key={j}
                points={points.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                strokeWidth="2.5"
                strokeDasharray={
                  series.length > 1 && i === 0 ? "6 5" : undefined
                }
              />
            ))}
            {line.points.map((p) => (
              <g key={p.index}>
                <circle cx={p.x} cy={p.y} r={selected === p.index ? 5 : 3} />
                <circle
                  cx={p.x}
                  cy={p.y}
                  r="12"
                  className="progress-chart__hit"
                  role="button"
                  tabIndex={0}
                  aria-label={`${labels[i]}, ${date(Date.parse(p.date))}: ${format(p.value)} ${unit}`}
                  onClick={() => {
                    setSelected(p.index);
                    onSelect?.(p.index);
                  }}
                  onFocus={() => {
                    setSelected(p.index);
                    onSelect?.(p.index);
                  }}
                  onMouseEnter={() => {
                    setSelected(p.index);
                    onSelect?.(p.index);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelected(p.index);
                      onSelect?.(p.index);
                    }
                  }}
                >
                  <title>
                    {labels[i]}: {format(p.value)} {unit}
                  </title>
                </circle>
              </g>
            ))}
          </g>
        ))}
      </svg>
      <figcaption
        className="progress-chart__legend"
        dir={language === "fa" ? "rtl" : "ltr"}
      >
        {labels.map((label, i) => (
          <span key={label} className={`progress-chart__legend-${i}`}>
            {label}
          </span>
        ))}{" "}
        <small>{unit}</small>
      </figcaption>
    </figure>
  );
}
