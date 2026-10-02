import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import {
  progressCopy,
  progressPresentationCopy,
  resolvedIanaTimeZone,
  type ProgressOverview,
  type ProgressPreset,
  type ProgressTab,
} from "@fitician/core";
import { useAuth } from "../auth/AuthContext";
import { progressApi as api } from "./api";
import { ProgressTabs } from "./ProgressTabs";
import { ProgressOverview as Overview } from "./ProgressOverview";
import "./progress.css";
const Details = lazy(() => import("./ProgressDetails"));
const AnalysisDetails = lazy(() =>
  import("../bodyPhotos/BodyProgressPage").then((m) => ({
    default: m.BodyProgressPage,
  })),
);
export function ProgressPage() {
  const { user } = useAuth();
  return <ProgressContent key={user?.id} />;
}
function ProgressContent() {
  const { i18n } = useTranslation(),
    language = i18n.resolvedLanguage === "en" ? "en" : "fa",
    c = progressCopy[language],
    p = progressPresentationCopy[language],
    { user } = useAuth();
  const [preset, setPreset] = useState<ProgressPreset>("week"),
    [tab, setTab] = useState<ProgressTab>("overview"),
    [data, setData] = useState<ProgressOverview | null>(null),
    [error, setError] = useState(false);
  const epoch = useRef(0),
    identity = user?.id;
  const load = useCallback(async () => {
    const current = ++epoch.current;
    setError(false);
    setData(null);
    if (!identity) return;
    try {
      const next = await api.overview(preset, resolvedIanaTimeZone());
      if (epoch.current === current) setData(next);
    } catch {
      if (epoch.current === current) setError(true);
    }
  }, [preset, identity]);
  useEffect(() => {
    void load();
    return () => {
      // This ref is a request generation, not a DOM node.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      epoch.current++;
    };
  }, [load]);
  return (
    <main
      className="progress-page fitician-page"
      dir={language === "fa" ? "rtl" : "ltr"}
    >
      <header className="progress-heading">
        <h1>{c.title}</h1>
      </header>
      <ProgressTabs
        data={data}
        selected={tab}
        language={language}
        onSelect={setTab}
      />
      <div className="progress-toolbar">
        <span>
          {data?.context.week_number != null
            ? `${c.programWeek} ${new Intl.NumberFormat(language).format(data.context.week_number)} · ${c.program}`
            : c[preset]}
        </span>
        <label>
          <span className="progress-visually-hidden">{p.period}</span>
          <select
            aria-label={p.period}
            value={preset}
            onChange={(e) => setPreset(e.target.value as ProgressPreset)}
          >
            {(["week", "four_weeks", "current_program"] as const).map(
              (range) => (
                <option key={range} value={range}>
                  {c[range]}
                </option>
              ),
            )}
          </select>
        </label>
      </div>
      {error ? (
        <div role="alert" className="progress-card">
          <p>{c.error}</p>
          <button onClick={() => void load()}>{c.retry}</button>
        </div>
      ) : !data ? (
        <div role="status" className="progress-skeleton">
          {c.loading}
        </div>
      ) : (
        <section
          role="tabpanel"
          id={`progress-panel-${tab}`}
          aria-labelledby={`progress-tab-${tab}`}
          tabIndex={0}
        >
          {data.context.range_clipped && (
            <p className="progress-note">{c.clipped}</p>
          )}
          {tab === "overview" ? (
            <Overview data={data} language={language} onSelect={setTab} />
          ) : (
            <Suspense fallback={<p role="status">{c.loading}</p>}>
              {tab === "analysis" ? (
                <div className="progress-analysis">
                  <AnalysisDetails embedded />
                </div>
              ) : (
                <Details
                  key={preset}
                  tab={tab}
                  data={data}
                  language={language}
                  onSaved={load}
                />
              )}
            </Suspense>
          )}
        </section>
      )}
    </main>
  );
}
