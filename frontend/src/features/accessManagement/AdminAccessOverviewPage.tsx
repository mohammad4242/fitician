import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  formatTehranDateForLocale,
  formatTehranDateTimeForLocale,
} from "@fitician/core";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { getAccessOverview, type AccessOverview } from "./adminAccessApi";

export function AdminAccessOverviewPage() {
  const { i18n, t } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const locale = english ? "en" : "fa-IR";
  const [data, setData] = useState<AccessOverview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void getAccessOverview()
      .then((value) => {
        if (!active) return;
        setData(value);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [retry]);

  if (loading) {
    return <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>;
  }
  if (error !== null) {
    return (
      <AppErrorNotice
        audience="admin"
        context="access"
        error={error}
        locale={english ? "en" : "fa"}
        onRetry={() => setRetry((value) => value + 1)}
      />
    );
  }
  if (data === null) return null;

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.overview")}</p>
            <h1>{t("adminAccess.overviewTitle")}</h1>
            <p>{t("adminAccess.metricsTimezone", { timezone: data.timezone })}</p>
          </div>
        </header>
        <details className="access-overview-definitions"><summary>{t("adminAccess.metricDefinitions")}</summary><p>{t("adminAccess.monthCalendarNote")} {t("adminAccess.activityMetricsNote")}</p></details>
        <OverviewMetrics data={data} locale={locale} english={english} />
        <DailySignupsChart data={data} locale={locale} english={english} />
        <RecentUsers data={data} locale={locale} />
      </div>
    </main>
  );
}

function OverviewMetrics({ data, locale, english }: { data: AccessOverview; locale: string; english: boolean }) {
  const { t } = useTranslation();
  const highlights: [string, number][] = [
    ["totalUsers", data.total_users], ["active7d", data.active_users_7d], ["paidUsers", data.active_paid_users],
  ];
  const groups: { title: string; metrics: [string, number][] }[] = [
    { title: "registrationGrowth", metrics: [["registrationsToday", data.registrations_today], ["registrationsWeek", data.registrations_week], ["registrationsMonth", data.registrations_month]] },
    { title: "userEngagement", metrics: [["active24h", data.active_users_24h], ["active30d", data.active_users_30d]] },
    { title: "successfulPurchases", metrics: [["purchasesToday", data.purchases_today], ["purchasesWeek", data.purchases_week], ["purchasesMonth", data.purchases_month]] },
    { title: "productUsage", metrics: [["workoutPlans", data.workout_plans], ["nutritionPlans", data.nutrition_plans], ["bodyAnalysesCompleted", data.body_analyses_completed]] },
  ];
  const number = (value: number) => value.toLocaleString(english ? "en-US" : locale);
  return (
    <section className="access-overview-metrics" aria-label={t("adminAccess.overviewMetrics")}>
      <div className="access-overview-highlights">
        {highlights.map(([key, value]) => (
          <article className="access-overview-metric" key={key}>
            <span>{t(`adminAccess.metrics.${key}`)}</span><strong>{number(value)}</strong>
          </article>
        ))}
      </div>
      <div className="access-overview-groups">
        {groups.map((group) => (
          <section className="access-overview-group" key={group.title}>
            <h2>{t(`adminAccess.${group.title}`)}</h2>
            <dl data-count={group.metrics.length}>{group.metrics.map(([key, value]) => (
              <div key={key}><dt>{t(`adminAccess.metrics.${key}`)}</dt><dd>{number(value)}</dd></div>
            ))}</dl>
          </section>
        ))}
      </div>
    </section>
  );
}

function DailySignupsChart({ data, locale, english }: { data: AccessOverview; locale: string; english: boolean }) {
  const { t } = useTranslation();
  const maximum = Math.max(1, ...data.daily_signups.map((point) => point.count));
  const dateLabel = (value: string) => formatTehranDateForLocale(
    new Date(`${value}T12:00:00Z`).toISOString(),
    locale,
  );
  const lastSignup = data.daily_signups[data.daily_signups.length - 1];
  const points = data.daily_signups.map((point, index) => ({
    ...point,
    x: index * 100 / Math.max(1, data.daily_signups.length),
    y: 94 - point.count * 78 / maximum,
    height: point.count * 78 / maximum,
  }));

  return (
    <section className="access-overview-panel" aria-labelledby="signup-chart-title">
      <header>
        <h2 id="signup-chart-title">{t("adminAccess.dailySignups")}</h2>
        <span>{t("adminAccess.last30Days")}</span>
      </header>
      <div className="access-overview-chart-layout">
        <div className="access-overview-chart-scale" aria-hidden="true">
          <span>{maximum}</span>
          <span>{Math.round(maximum / 2)}</span>
          <span>0</span>
        </div>
        <svg
          aria-label={t("adminAccess.dailySignupsChart")}
          className="access-overview-chart"
          preserveAspectRatio="none"
          role="img"
          viewBox="0 0 100 100"
        >
          <title>{t("adminAccess.dailySignupsScale", { max: maximum })}</title>
          {[16, 55, 94].map((y) => (
            <line
              key={y}
              x1="0"
              x2="100"
              y1={y}
              y2={y}
              stroke="var(--fitician-line)"
              strokeWidth=".5"
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {points.map((point) => (
            <rect
              key={point.date}
              x={point.x + 0.15}
              y={point.y}
              width={Math.max(0.3, 70 / Math.max(points.length, 1))}
              height={point.height}
              rx=".25"
              fill="var(--fitician-aqua)"
            >
              <title>{`${dateLabel(point.date)}: ${point.count.toLocaleString(english ? "en-US" : locale)}`}</title>
            </rect>
          ))}
        </svg>
      </div>
      <div className="access-overview-chart__labels">
        <span>{data.daily_signups[0] ? dateLabel(data.daily_signups[0].date) : "—"}</span>
        <span>{lastSignup ? dateLabel(lastSignup.date) : "—"}</span>
      </div>
      <details className="access-overview-chart-data">
        <summary>{t("adminAccess.chartData")}</summary>
        <ol>
          {points.map((point) => (
            <li key={point.date}>
              {dateLabel(point.date)}: {point.count.toLocaleString(english ? "en-US" : locale)}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

function RecentUsers({ data, locale }: { data: AccessOverview; locale: string }) {
  const { t } = useTranslation();
  return (
    <section className="access-overview-panel">
      <header>
        <h2>{t("adminAccess.recentUsers")}</h2>
        <Link to="/admin/billing/users">{t("adminAccess.usersAccess")}</Link>
      </header>
      {data.recent_users.length === 0
        ? <p className="access-admin-status">{t("adminAccess.noUsers")}</p>
        : (
          <div className="access-overview-recent">
            {data.recent_users.map((user) => (
              <article key={user.user_id}>
                <div>
                  <strong>{user.display_name ?? user.email ?? user.phone_number ?? user.user_id}</strong>
                  <small>{user.email ?? user.phone_number ?? "—"}</small>
                </div>
                <div><small>{t("adminAccess.signupDate")}</small><span>{formatTehranDateForLocale(user.created_at, locale)}</span></div>
                <div><small>{t("adminAccess.currentPackage")}</small><span>{t(`entitlements.packageLabels.${user.primary_package}`, { defaultValue: user.primary_package })}</span></div>
                <div><small>{t("adminAccess.lastActivity")}</small><span>
                  {user.last_activity_at
                    ? formatTehranDateTimeForLocale(user.last_activity_at, locale)
                    : t("adminAccess.noActivity")}
                </span></div>
                <span className="access-status-badge" data-status={user.usage_status}>{t(`adminAccess.usage.${user.usage_status ?? "no_recorded_activity"}`)}</span>
                <Link to={`/admin/billing/users/${user.user_id}`}>{t("adminAccess.viewAccess")}</Link>
              </article>
            ))}
          </div>
        )}
    </section>
  );
}
