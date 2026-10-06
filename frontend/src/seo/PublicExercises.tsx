import { useEffect, useMemo, useState } from "react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { ExerciseCatalog, ExerciseCard, type CatalogPageData, type CatalogSource } from "../features/exercises/ExerciseCatalog";
import { ReadyExerciseDetail, type ExercisePresentationDetail } from "../features/exercises/ExerciseDetailPresentation";
import type { ExerciseCategories, ExerciseFilters } from "../features/exercises/types";
import language from "./exercise-language.json";
import type { PublicPayload } from "./registry";
import "../features/exercises/exercises.css";

const publicI18n = createInstance();
void publicI18n.init({ lng: "fa", fallbackLng: "fa", initAsync: false,
  resources: { fa: { translation: language } }, interpolation: { escapeValue: false } });

function localPage(records: ExercisePresentationDetail[], filters: ExerciseFilters): CatalogPageData {
  const matching = records.filter(record =>
    (!filters.body_region || record.body_region === filters.body_region)
    && (!filters.primary_muscle || record.primary_muscle === filters.primary_muscle)
    && (!filters.muscle_focus || record.muscle_focus === filters.muscle_focus)
    && (!filters.equipment || record.equipment.includes(filters.equipment))
    && (!filters.difficulty || record.difficulty === filters.difficulty)
    && (!filters.content_type || record.content_type === filters.content_type)
    && (!filters.labels?.length || filters.labels.every(label => record.labels?.includes(label)))
    && (!filters.exercise_type)
    && (!filters.search || `${record.name_fa} ${record.name_en}`.toLocaleLowerCase().includes(filters.search.toLocaleLowerCase())),
  );
  const page = filters.page ?? 1;
  const page_size = filters.page_size ?? 12;
  return { items: matching.slice((page - 1) * page_size, page * page_size), page, page_size,
    total: matching.length, total_pages: Math.ceil(matching.length / page_size) };
}
async function publicRead<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1/public/${path}`, { credentials: "omit" });
  if (!response.ok) throw new Error("Public catalogue unavailable");
  return response.json() as Promise<T>;
}
function queryString(filters: ExerciseFilters) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value)) value.forEach(item => query.append(key, item));
    else if (value !== undefined && value !== "") query.set(key, String(value));
  }
  return query.toString();
}
function PublicCatalog({ payload }: { payload: PublicPayload }) {
  const [query, setQuery] = useState(new URLSearchParams());
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    const read = () => setQuery(new URLSearchParams(window.location.search));
    read();
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, []);
  const source = useMemo<CatalogSource>(() => ({
    categories: () => publicRead<ExerciseCategories>("exercise-categories").catch(() => payload.categories!),
    list: async filters => {
      try {
        const page = await publicRead<CatalogPageData>(`exercises?${queryString(filters)}`);
        setOffline(false);
        return page;
      } catch {
        setOffline(true);
        return localPage(payload.exercises, filters);
      }
    },
  }), [payload]);
  function writeQuery(next: URLSearchParams) {
    const query = next.toString();
    window.history.pushState(null, "", `/exercise-library${query ? `?${query}` : ""}`);
    setQuery(next);
  }
  return <>
    {offline && <p className="public-library-note" role="status">اتصال به کتابخانه زنده در دسترس نیست؛ مجموعه منتشرشده را می‌بینی.</p>}
    <ExerciseCatalog publicMode source={source} searchParams={query} setSearchParams={writeQuery}
      initialCategories={payload.categories} initialPage={localPage(payload.exercises, {})} />
  </>;
}
function PublicDetail({ payload }: { payload: PublicPayload }) {
  const [exercise, setExercise] = useState(payload.exercise!);
  const [removed, setRemoved] = useState(false);
  const [catalogPath, setCatalogPath] = useState("/exercise-library");
  useEffect(() => {
    setCatalogPath(`/exercise-library${window.location.search}`);
    let active = true;
    void fetch(`/api/v1/public/exercises/${encodeURIComponent(payload.exercise!.slug)}`, { credentials: "omit" })
      .then(async response => {
        if (!active) return;
        if (response.status === 404) { setRemoved(true); return; }
        if (response.ok) {
          const data = await response.json() as ExercisePresentationDetail;
          if (active) setExercise(data);
        }
      }).catch(() => { /* Build-rendered educational content remains available offline. */ });
    return () => { active = false; };
  }, [payload]);
  if (removed) return <section className="exercise-detail-message"><h1>حرکت پیدا نشد</h1><a href="/exercise-library">بازگشت به کتابخانه حرکات</a></section>;
  return <div className="exercise-catalog-shell exercise-detail-shell">
    <div className="exercise-detail-main">
      <ReadyExerciseDetail publicMode exercise={exercise} catalogPath={catalogPath} isEnglish={false}
        mediaPresentation="male" mediaSwitching={false} mediaSwitchError={null} mediaSwitchUnavailable={false} />
      {payload.exercises.length > 0 && <section className="public-related-exercises"><h2 className="fitician-display">حرکات مرتبط با همین عضله</h2>
        <div className="exercise-card-grid">{payload.exercises.map(record => <ExerciseCard key={record.slug}
          exercise={record} categories={payload.categories!} isEnglish={false} publicMode
          catalogSearch="" returnTo={catalogPath} onDelete={() => undefined} />)}</div>
      </section>}
    </div>
  </div>;
}
export function PublicExercises({ payload }: { payload: PublicPayload }) {
  return <I18nextProvider i18n={publicI18n}>{payload.exercise
    ? <PublicDetail payload={payload} /> : <PublicCatalog payload={payload} />}</I18nextProvider>;
}
