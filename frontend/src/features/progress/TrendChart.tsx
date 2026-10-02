import {
  useEffect,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent,
} from "react";
import { chartGeometry, progressNumber, type ChartDatum } from "@fitician/core";
export function TrendChart({
  series,
  labels,
  unit,
  language,
  onSelect,
  valueLabels,
}: {
  series: ChartDatum[][];
  labels: string[];
  unit: string;
  language: "fa" | "en";
  valueLabels?: Record<number, string>;
  onSelect?: (index: number) => void;
}) {
  const ref = useRef<HTMLElement>(null),
    [width, setWidth] = useState(600),
    [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    if (!ref.current || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(Math.max(240, w));
    });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  const height = width < 450 ? 220 : 265,
    chart = chartGeometry(
      series,
      width,
      height,
      valueLabels ? [1, 3] : undefined,
    ),
    format = (v: number) => valueLabels?.[v] ?? progressNumber(v, language),
    date = (v: number) =>
      new Intl.DateTimeFormat(language, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(v);
  const select = (index: number) => {
    setSelected(index);
    onSelect?.(index);
  };
  const dates = series[0] ?? [];
  const xAt = (d: string) =>
    chart.padding.left +
    (chart.maxX === chart.minX
      ? 0.5
      : (Date.parse(d) - chart.minX) / (chart.maxX - chart.minX)) *
      (width - chart.padding.left - chart.padding.right);
  const selectNearest = (
    event: MouseEvent<SVGSVGElement> | PointerEvent<SVGSVGElement>,
  ) => {
    if (!dates.length) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) * width) / bounds.width;
    const y = ((event.clientY - bounds.top) * height) / bounds.height;
    if (!Number.isFinite(x) || y < 14 || y > height - 32) return;
    const index = dates.reduce(
      (best, point, i) =>
        Math.abs(xAt(point.date) - x) < Math.abs(xAt(dates[best].date) - x)
          ? i
          : best,
      0,
    );
    select(index);
  };
  return (
    <figure ref={ref} className="progress-chart" dir="ltr">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        onPointerMove={selectNearest}
        onClick={selectNearest}
        role="group"
        aria-label={labels.join(" / ") + " (" + unit + ")"}
      >
        <desc>
          {language === "fa"
            ? "نقطه‌ها را برای مشاهده جزئیات انتخاب کن. فاصله‌ها نشان‌دهنده ثبت‌های ناموجودند."
            : "Select a date to inspect its values. Gaps indicate missing records."}
        </desc>
        {(valueLabels
          ? Object.keys(valueLabels)
              .map(Number)
              .map((v) => (chart.maxY - v) / (chart.maxY - chart.minY))
          : [0, 0.5, 1]
        ).map((f) => {
          const y =
            chart.padding.top +
            f * (height - chart.padding.top - chart.padding.bottom);
          return (
            <g key={f}>
              <line
                x1={48}
                y1={y}
                x2={width - 14}
                y2={y}
                className="progress-chart__grid"
              />
              <text
                x={40}
                y={y + 4}
                textAnchor="end"
                className="progress-chart__label"
              >
                {format(
                  valueLabels
                    ? Math.round(chart.maxY - f * (chart.maxY - chart.minY))
                    : chart.maxY - f * (chart.maxY - chart.minY),
                )}
              </text>
            </g>
          );
        })}
        {dates.length > 0 && (
          <>
            <text x={48} y={height - 6} className="progress-chart__label">
              {date(chart.minX)}
            </text>
            <text
              x={width - 14}
              y={height - 6}
              textAnchor="end"
              className="progress-chart__label"
            >
              {date(chart.maxX)}
            </text>
          </>
        )}
        {selected !== null && dates[selected] && (
          <line
            x1={xAt(dates[selected].date)}
            x2={xAt(dates[selected].date)}
            y1={14}
            y2={height - 32}
            stroke="var(--fitician-muted)"
            strokeOpacity={0.5}
            strokeDasharray="3 4"
          />
        )}
        {chart.lines.map((line, i) => (
          <g key={i} className={`progress-chart__series-${i}`}>
            {line.segments.map((ps, j) => (
              <polyline
                key={j}
                points={ps.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={
                  series.length > 1 && i === 0 ? "6 5" : undefined
                }
              />
            ))}
            {line.points.map((p) => (
              <circle
                key={p.index}
                cx={p.x}
                cy={p.y}
                r={selected === p.index ? 5.5 : 3.5}
                stroke="var(--fitician-surface)"
                strokeWidth={2}
              />
            ))}
          </g>
        ))}
        {dates.map((p, index) => {
          const x = xAt(p.date),
            left = index ? (xAt(dates[index - 1].date) + x) / 2 : 48,
            right =
              index + 1 < dates.length
                ? (x + xAt(dates[index + 1].date)) / 2
                : width - 14;
          return (
            <rect
              key={index}
              x={left}
              y={14}
              width={Math.max(44, right - left)}
              height={height - 46}
              className="progress-chart__hit"
              role="button"
              tabIndex={0}
              aria-label={`${date(Date.parse(p.date))}: ${series.map((s, i) => `${labels[i]} ${s[index]?.value == null ? "—" : format(s[index].value!)} ${unit}`).join(", ")}`}
              onClick={() => select(index)}
              onMouseEnter={() => select(index)}
              onFocus={() => select(index)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  select(index);
                }
                if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                  e.preventDefault();
                  const next = Math.max(
                    0,
                    Math.min(
                      dates.length - 1,
                      index + (e.key === "ArrowRight" ? 1 : -1),
                    ),
                  );
                  e.currentTarget.parentElement
                    ?.querySelectorAll<SVGElement>(".progress-chart__hit")
                    [next]?.focus();
                }
              }}
            />
          );
        })}
      </svg>
      <figcaption
        className="progress-chart__legend"
        dir={language === "fa" ? "rtl" : "ltr"}
      >
        {labels.map((label, i) => (
          <span key={label} className={`progress-chart__legend-${i}`}>
            {label}
          </span>
        ))}
        <small>{unit}</small>
      </figcaption>
    </figure>
  );
}
