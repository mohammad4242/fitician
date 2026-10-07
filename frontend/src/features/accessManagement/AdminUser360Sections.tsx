import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  formatTehranDateForLocale,
  formatTehranDateTimeForLocale,
} from "@fitician/core";

import {
  getNutritionPlan,
  getNutritionPlans,
  getUserActivity,
  getUserBodyAnalyses,
  getUserInsights,
  getUserLogins,
  getUserProgress,
  getWorkoutPlan,
  getWorkoutPlans,
  type ActivityItem,
  type AnalysisItem,
  type LoginItem,
  type NutritionDetail,
  type NutritionHistoryItem,
  type Page,
  type ProgressItem,
  type UserInsights,
  type WorkoutDetail,
  type WorkoutHistoryItem,
} from "./adminAccessApi";

type Props = {
  accessContent?: React.ReactNode;
  billingContent?: React.ReactNode;
  accessRequest?: number;
  userId: string;
  member: {
    display_name: string | null;
    email: string | null;
    phone_number: string | null;
    user_id: string;
    created_at: string;
    primary_package: string;
    paid_access_end: string | null;
  };
};

type Tab = "activity" | "logins" | "plans" | "progress" | "accessTab" | "billingTab";
const PAGE_LIMIT = 25;

export function AdminUser360Sections({ userId, member, accessContent, billingContent, accessRequest = 0 }: Props) {
  const { i18n, t } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const [insights, setInsights] = useState<UserInsights | null>(null);
  const [insightsError, setInsightsError] = useState(false);
  const [insightsRetry, setInsightsRetry] = useState(0);
  const [tab, setTab] = useState<Tab>("activity");
  useEffect(() => { if (accessRequest > 0) setTab("accessTab"); }, [accessRequest]);
  const dateTime = (value: string) => formatTehranDateTimeForLocale(value, english ? "en" : "fa-IR", { dateStyle: "medium", timeStyle: "medium" });

  useEffect(() => {
    let live = true;
    setInsights(null);
    setInsightsError(false);
    void getUserInsights(userId)
      .then((value) => { if (live) setInsights(value); })
      .catch(() => {
        if (live) {
          setInsights(null);
          setInsightsError(true);
        }
      });
    return () => { live = false; };
  }, [userId, insightsRetry]);

  const summary: [string, string | number][] = [
    [t("adminAccess.userId"), member.user_id],
    [t("adminAccess.signupDate"), dateTime(member.created_at)],
    [t("adminAccess.phone"), member.phone_number ?? "—"],
    [t("adminAccess.lastActivity"), insights?.last_activity_at ? dateTime(insights.last_activity_at) : t("adminAccess.noActivity")],
    [t("adminAccess.loginCount"), insights?.login_count ?? "—"],
    [t("adminAccess.legacyLoginEvidence"), insights?.legacy_login_evidence_count ?? "—"],
    [t("adminAccess.currentPackage"), t(`entitlements.packageLabels.${member.primary_package}`, { defaultValue: member.primary_package })],
    [t("adminAccess.accessEnd"), member.paid_access_end ? dateTime(member.paid_access_end) : "—"],
    [t("adminAccess.workoutPlansHistory"), insights?.workout_plans ?? "—"],
    [t("adminAccess.nutritionPlansHistory"), insights?.nutrition_plans ?? "—"],
    [t("adminAccess.completedSessions"), insights?.completed_workout_sessions ?? "—"],
    [t("adminAccess.bodyAnalysisHistory"), insights?.body_analyses ?? "—"],
    [t("adminAccess.latestWeight"), insights?.latest_weight_kg == null ? "—" : `${insights.latest_weight_kg} kg`],
  ];

  return (
    <section className="access-user360" aria-labelledby="user360-title">
      <header className="access-user360__heading">
        <div>
          <p className="eyebrow eyebrow--accent">{t("adminAccess.user360")}</p>
          <h2 id="user360-title">{t("adminAccess.insights")}</h2>
        </div>
      </header>

      {insightsError && (
        <p role="alert">
          {t("adminAccess.loadError")} {" "}
          <button type="button" onClick={() => setInsightsRetry((value) => value + 1)}>
            {t("adminAccess.retry")}
          </button>
        </p>
      )}

      <dl className="access-user360__summary">
        {[1, 3, 4, 6, 7].map((index) => {
          const [label, value] = summary[index]!;
          return <div key={label}><dt>{label}</dt><dd><bdi>{value}</bdi></dd></div>;
        })}
      </dl>
      <dl className="access-user360__usage">
        {summary.slice(8).map(([label, value]) => <div key={label}><dt>{label}</dt><dd><bdi>{value}</bdi></dd></div>)}
      </dl>
      <details className="access-user360__identity-details">
        <summary>{t("adminAccess.identityDetails")}</summary>
        <dl>{[0, 2, 5].map((index) => {
          const [label, value] = summary[index]!;
          return <div key={label}><dt>{label}</dt><dd><bdi>{value}</bdi></dd></div>;
        })}</dl>
      </details>

      <nav className="access-user360__tabs" aria-label={t("adminAccess.user360")}>
        {(["activity", "logins", "plans", "progress", ...(accessContent ? ["accessTab"] as const : []), ...(billingContent ? ["billingTab"] as const : [])] as const).map((item) => (
          <button
            aria-pressed={tab === item}
            className="access-admin-button access-admin-button--quiet"
            key={item}
            onClick={() => setTab(item)}
            type="button"
          >
            {t(`adminAccess.${item}`)}
          </button>
        ))}
      </nav>

      {tab === "activity" && <ActivityTab userId={userId} dateTime={dateTime} />}
      {tab === "logins" && <LoginsTab userId={userId} dateTime={dateTime} />}
      {tab === "accessTab" && accessContent}
      {tab === "billingTab" && billingContent}
      {tab === "plans" && <PlansTab userId={userId} dateTime={dateTime} />}
      {tab === "progress" && <ProgressTab userId={userId} dateTime={dateTime} />}
    </section>
  );
}

function ActivityTab({ userId, dateTime }: { userId: string; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  return <PageSection key={`${userId}-activity`} title={t("adminAccess.activity")} className="access-user360__timeline"
    load={(offset) => getUserActivity(userId, { limit: PAGE_LIMIT, offset })}
    render={(item: ActivityItem) => <ActivityRow item={item} dateTime={dateTime} />} />;
}

function LoginsTab({ userId, dateTime }: { userId: string; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  return <><p className="access-user360__hint">{t("adminAccess.loginHistoryLimit")}</p>
    <PageSection key={`${userId}-logins`} title={t("adminAccess.logins")}
      load={(offset) => getUserLogins(userId, { limit: PAGE_LIMIT, offset })}
      render={(item: LoginItem) => <LoginRow item={item} dateTime={dateTime} />} /></>;
}

function PlansTab({ userId, dateTime }: { userId: string; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  return (
    <div className="access-user360__columns">
      <PageSection
        key={`${userId}-workout-plans`}
        title={t("adminAccess.workoutPlansHistory")}
        load={(offset) => getWorkoutPlans(userId, { limit: PAGE_LIMIT, offset })}
        render={(item: WorkoutHistoryItem) => <WorkoutCard userId={userId} item={item} dateTime={dateTime} />}
      />
      <PageSection
        key={`${userId}-nutrition-plans`}
        title={t("adminAccess.nutritionPlansHistory")}
        load={(offset) => getNutritionPlans(userId, { limit: PAGE_LIMIT, offset })}
        render={(item: NutritionHistoryItem) => <NutritionCard userId={userId} item={item} dateTime={dateTime} />}
      />
    </div>
  );
}

function ProgressTab({ userId, dateTime }: { userId: string; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  return (
    <div className="access-user360__columns">
      <PageSection
        key={`${userId}-progress`}
        title={t("adminAccess.progressHistory")}
        load={(offset) => getUserProgress(userId, { limit: PAGE_LIMIT, offset })}
        render={(item: ProgressItem) => <ProgressRow item={item} dateTime={dateTime} />}
      />
      <PageSection
        key={`${userId}-body-analyses`}
        title={t("adminAccess.bodyAnalysisHistory")}
        load={(offset) => getUserBodyAnalyses(userId, { limit: PAGE_LIMIT, offset })}
        render={(item: AnalysisItem) => <AnalysisRow item={item} dateTime={dateTime} />}
      />
    </div>
  );
}

function PageSection<T extends { id: string }>({
  title,
  load,
  render,
  className = "",
}: {
  title: string;
  className?: string;
  load: (offset: number) => Promise<Page<T>>;
  render: (item: T) => React.ReactNode;
}) {
  const { t } = useTranslation();
  const [page, setPage] = useState<Page<T> | null>(null);
  const [error, setError] = useState(false);
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const loader = useRef(load);
  loader.current = load;

  useEffect(() => {
    let live = true;
    setPage(null);
    setError(false);
    void loader.current(offset)
      .then((result) => { if (live) setPage(result); })
      .catch(() => { if (live) setError(true); });
    return () => { live = false; };
  }, [offset, retry]);

  return (
    <section className={`access-user360__panel ${className}`}>
      <h3>{title}</h3>
      {page === null && !error && <p role="status">{t("adminAccess.loading")}</p>}
      {error && (
        <div role="alert">
          <p>{t("adminAccess.loadError")}</p>
          <button type="button" onClick={() => setRetry((value) => value + 1)}>
            {t("adminAccess.retry")}
          </button>
        </div>
      )}
      {page?.items.length === 0 && <p>{t("adminAccess.noRecords")}</p>}
      {page && page.items.length > 0 && (
        <>
          <div className="access-user360__items" tabIndex={className ? 0 : undefined} role={className ? "region" : undefined} aria-label={className ? title : undefined}>
            {page.items.map((item) => <article key={item.id}>{render(item)}</article>)}
          </div>
          <small>{page.total} · {t("adminAccess.showingFirst", { count: page.items.length })}</small>
          <div className="access-user-pagination" aria-label={t("adminAccess.recordPagination")}>
            <button className="access-admin-button access-admin-button--quiet" type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - page.limit))}>
              {t("adminAccess.previousPage")}
            </button>
            <span>{Math.floor(offset / page.limit) + 1} / {Math.max(1, Math.ceil(page.total / page.limit))}</span>
            <button className="access-admin-button access-admin-button--quiet" type="button" disabled={offset + page.items.length >= page.total} onClick={() => setOffset(offset + page.limit)}>
              {t("adminAccess.nextPage")}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function ActivityRow({ item, dateTime }: { item: ActivityItem; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  const eventTitle = t(`adminAccess.activityTypes.${item.event_type}`, { defaultValue: t("adminAccess.otherActivity") });
  const metadata: string[] = [
    typeof item.metadata.platform === "string" && t(`adminAccess.platforms.${item.metadata.platform}`, { defaultValue: t("adminAccess.unknownValue") }),
    typeof item.metadata.auth_method === "string" && t(`adminAccess.authMethods.${item.metadata.auth_method}`, { defaultValue: t("adminAccess.unknownValue") }),
    typeof item.metadata.device_name === "string" && item.metadata.device_name,
  ].filter((value): value is string => typeof value === "string");

  for (const [key, value] of Object.entries(item.metadata)) {
    if (value == null) continue;
    if (key === "week" || key === "week_number") metadata.push(`${t("adminAccess.weekNumber")}: ${value}`);
    else if (key === "session" || key === "session_number") metadata.push(`${t("adminAccess.sessionNumber")}: ${value}`);
    else if (key === "weight_kg") metadata.push(`${t("adminAccess.weight")}: ${value} kg`);
    else if (key === "training_days") metadata.push(`${t("adminAccess.trainingDays")}: ${value}`);
    else if ((key === "goal" || key === "primary_goal") && typeof value === "string") {
      const goal = t(`adminAccess.goalLabels.${value}`, { defaultValue: t("adminAccess.unknownValue") });
      metadata.push(`${t("adminAccess.goal")}: ${goal}`);
    } else if (key === "revision") metadata.push(`${t("adminAccess.revision")}: ${value}`);
  }

  return (
    <>
      <span className="access-activity-marker" data-category={item.event_type.split(".")[0]} aria-hidden="true" />
      <strong>{eventTitle}</strong>
      <time dateTime={item.occurred_at}>{dateTime(item.occurred_at)}</time>
      {item.source === "historical" && <span className="access-status-badge">{t("adminAccess.historicalEvidence")}</span>}
      {metadata.length > 0 && <small>{metadata.join(" · ")}</small>}
    </>
  );
}

function LoginRow({ item, dateTime }: { item: LoginItem; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  const evidenceLabel = item.evidence === "explicit_login"
    ? t("adminAccess.explicitLogin")
    : item.evidence === "legacy_web_session"
      ? t("adminAccess.historicalWebSession")
      : t("adminAccess.historicalMobileToken");
  const details = [
    item.platform && t(`adminAccess.platforms.${item.platform}`, { defaultValue: t("adminAccess.unknownValue") }),
    item.auth_method && t(`adminAccess.authMethods.${item.auth_method}`, { defaultValue: t("adminAccess.unknownValue") }),
    item.device_name,
    item.app_version && `${t("adminAccess.appVersion")}: ${item.app_version}`,
  ].filter(Boolean).join(" · ");
  return (
    <>
      <strong className="access-login-title">{evidenceLabel}<span className="access-status-badge">{item.platform ? t(`adminAccess.platforms.${item.platform}`) : "—"}</span></strong>
      <time dateTime={item.occurred_at}>{dateTime(item.occurred_at)}</time>
      <small>{details || "—"}</small>
    </>
  );
}

function ProgressRow({ item, dateTime }: { item: ProgressItem; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  const measurements = [
    item.waist_circumference_cm != null && `${t("adminAccess.waist")}: ${item.waist_circumference_cm} cm`,
    item.hip_circumference_cm != null && `${t("adminAccess.hip")}: ${item.hip_circumference_cm} cm`,
    item.shoulder_circumference_cm != null && `${t("adminAccess.shoulder")}: ${item.shoulder_circumference_cm} cm`,
    item.shoulder_width_cm != null && `${t("adminAccess.shoulderWidth")}: ${item.shoulder_width_cm} cm`,
  ].filter(Boolean).join(" · ");
  return (
    <>
      <strong>
        {item.weight_kg == null
          ? t("adminAccess.bodyMeasurement")
          : `${t("adminAccess.weight")}: ${item.weight_kg} kg`}
      </strong>
      {item.observed_fields == null && <small>{t("adminAccess.legacyMeasurementNote")}</small>}
      <time>{dateTime(item.measured_at)}</time>
      {measurements && <small>{measurements}</small>}
    </>
  );
}

function AnalysisRow({ item, dateTime }: { item: AnalysisItem; dateTime: (value: string) => string }) {
  const { t } = useTranslation();
  return (
    <>
      <strong>{t(`adminAccess.analysisStatuses.${item.status}`, { defaultValue: t("adminAccess.unknownValue") })}</strong>
      <time>{dateTime(item.created_at)}</time>
      <small>
        {t("adminAccess.revision")}: {item.revision}
        {item.completed_at ? ` · ${dateTime(item.completed_at)}` : ""}
      </small>
    </>
  );
}

function WorkoutCard({ userId, item, dateTime }: { userId: string; item: WorkoutHistoryItem; dateTime: (value: string) => string }) {
  const { t, i18n } = useTranslation();
  const [detail, setDetail] = useState<WorkoutDetail | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => () => { requestId.current += 1; }, []);

  async function loadDetails() {
    if (loading || detail !== null) return;
    const current = ++requestId.current;
    setError(false);
    setLoading(true);
    try {
      const value = await getWorkoutPlan(userId, item.id);
      if (current === requestId.current) setDetail(value);
    } catch {
      if (current === requestId.current) setError(true);
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }

  return (
    <>
      <strong>{t("adminAccess.goal")}: {t(`adminAccess.goalLabels.${item.primary_goal}`, { defaultValue: t("adminAccess.unknownValue") })}</strong>
      <time>{dateTime(item.created_at)}</time>
      <small>
        {t(`adminAccess.statuses.${item.status}`, { defaultValue: t("adminAccess.unknownValue") })} · {" "}
        {t(`adminAccess.reviewStatuses.${item.review_status}`, { defaultValue: t("adminAccess.unknownValue") })} · {" "}
        {item.duration_weeks} {t("adminAccess.weeks")} · {item.training_days} {t("adminAccess.trainingDays")}
      </small>
      <details className="access-plan-disclosure" onToggle={(event) => { if (event.currentTarget.open) void loadDetails(); }}>
        <summary>{t("adminAccess.details")}</summary>
        {loading && <p role="status">{t("adminAccess.loading")}</p>}
        {error && (
          <p role="alert">
            {t("adminAccess.loadError")} {" "}
            <button type="button" onClick={() => void loadDetails()}>{t("adminAccess.retry")}</button>
          </p>
        )}
        {detail && <WorkoutPlanDetails detail={detail} english={english} />}
      </details>
    </>
  );
}

function WorkoutPlanDetails({ detail, english }: { detail: WorkoutDetail; english: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="access-user360__detail">
      {detail.days.map((day) => (
        <section key={day.day_number}>
          <strong>{english ? day.title_en : day.title_fa}</strong>
          {day.exercises.map((exercise, index) => {
            const amount = exercise.reps_min != null
              ? `${exercise.reps_min}${exercise.reps_max ? `–${exercise.reps_max}` : ""} ${t("adminAccess.repetitions")}`
              : `${exercise.duration_min_seconds ?? "—"} ${t("adminAccess.seconds")}`;
            return (
              <p key={`${exercise.name_en}-${index}`}>
                {english ? exercise.name_en : exercise.name_fa} · {exercise.sets} × {amount}
              </p>
            );
          })}
        </section>
      ))}
    </div>
  );
}

function NutritionCard({ userId, item, dateTime }: { userId: string; item: NutritionHistoryItem; dateTime: (value: string) => string }) {
  const { t, i18n } = useTranslation();
  const [detail, setDetail] = useState<NutritionDetail | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);
  const english = i18n.resolvedLanguage === "en";
  const dateOnly = (value: string) => formatTehranDateForLocale(new Date(`${value}T12:00:00Z`).toISOString(), english ? "en" : "fa-IR");

  useEffect(() => () => { requestId.current += 1; }, []);

  async function loadDetails() {
    if (loading || detail !== null) return;
    const current = ++requestId.current;
    setError(false);
    setLoading(true);
    try {
      const value = await getNutritionPlan(userId, item.id);
      if (current === requestId.current) setDetail(value);
    } catch {
      if (current === requestId.current) setError(true);
    } finally {
      if (current === requestId.current) setLoading(false);
    }
  }

  return (
    <>
      <strong>
        {t("adminAccess.revision")}: {item.revision} · {" "}
        {t(`adminAccess.lifecycleStatuses.${item.lifecycle_status}`, { defaultValue: t("adminAccess.unknownValue") })}
      </strong>
      <time>{dateTime(item.created_at)}</time>
      <small>
        {t(`adminAccess.reviewStatuses.${item.review_status}`, { defaultValue: t("adminAccess.unknownValue") })} · {" "}
        {t("adminAccess.startDate")}: {dateOnly(item.start_date)} · {" "}
        {t(`adminAccess.budgetStatuses.${item.budget_status}`, { defaultValue: t("adminAccess.unknownValue") })} · {" "}
        {item.selected ? t("adminAccess.selected") : t("adminAccess.notSelected")}
      </small>
      <details className="access-plan-disclosure" onToggle={(event) => { if (event.currentTarget.open) void loadDetails(); }}>
        <summary>{t("adminAccess.details")}</summary>
        {loading && <p role="status">{t("adminAccess.loading")}</p>}
        {error && (
          <p role="alert">
            {t("adminAccess.loadError")} {" "}
            <button type="button" onClick={() => void loadDetails()}>{t("adminAccess.retry")}</button>
          </p>
        )}
        {detail && <NutritionPlanDetails detail={detail} dateOnly={dateOnly} english={english} />}
      </details>
    </>
  );
}

function NutritionPlanDetails({ detail, dateOnly, english }: { detail: NutritionDetail; dateOnly: (value: string) => string; english: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="access-user360__detail">
      {detail.days.map((day) => (
        <section key={day.day_index}>
          <strong>{dateOnly(day.plan_date)}</strong>
          {day.meals.map((meal, index) => (
            <p key={`${meal.slot}-${index}`}>
              {t(`adminAccess.mealSlots.${meal.slot}`, { defaultValue: t("adminAccess.unknownValue") })}: {" "}
              {meal.foods.map((food) => `${english ? food.name_en : food.name_fa} (${food.grams}g)`).join(", ")}
            </p>
          ))}
        </section>
      ))}
    </div>
  );
}
