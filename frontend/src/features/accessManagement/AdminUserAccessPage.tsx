import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import {
  formatTehranDateForLocale,
  formatTehranDateTimeForLocale,
} from "@fitician/core";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { PersianDatePicker } from "../../shared/PersianDatePicker";
import {
  searchAccessUsers,
  type AdminMemberSummary,
  type Page,
} from "./adminAccessApi";

const PAGE_SIZE = 25;
const MAX_OFFSET = 1_000_000;
const SIGNUP_PERIODS = ["all", "today", "week", "month", "custom"] as const;
const SORT_ORDERS = ["newest", "oldest", "last_activity"] as const;

type SignupPeriod = (typeof SIGNUP_PERIODS)[number];
export function AdminUserAccessPage() {
  const { i18n, t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const offset = parseOffset(params.get("offset"));
  const period = parseChoice(params.get("signup_period"), SIGNUP_PERIODS, "all");
  const sort = parseChoice(params.get("sort"), SORT_ORDERS, "newest");
  const fromDate = params.get("from_date") ?? "";
  const toDate = params.get("to_date") ?? "";
  const customDatesValid = isValidIsoDate(fromDate) && isValidIsoDate(toDate);
  const customRangeInvalid = customDatesValid && fromDate > toDate;
  const customRangeIncomplete = period === "custom" && (!customDatesValid || customRangeInvalid);

  const [input, setInput] = useState(query);
  const [page, setPage] = useState<Page<AdminMemberSummary> | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const english = i18n.resolvedLanguage === "en";
  const locale = english ? "en" : "fa-IR";

  useEffect(() => {
    setInput(query);
    if (customRangeIncomplete) {
      setPage(null);
      setLoadError(null);
      setState("ready");
      return;
    }

    let active = true;
    setState("loading");
    void searchAccessUsers({
      q: query || undefined,
      limit: PAGE_SIZE,
      offset,
      signup_period: period,
      from_date: period === "custom" ? fromDate : undefined,
      to_date: period === "custom" ? toDate : undefined,
      sort,
    })
      .then((result) => {
        if (!active) return;
        setPage(result);
        setLoadError(null);
        setState("ready");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setLoadError(cause);
        setState("error");
      });
    return () => { active = false; };
  }, [query, offset, period, fromDate, toDate, sort, retryKey, customRangeIncomplete]);

  function update(next: Record<string, string>) {
    const values = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) values.set(key, value);
      else values.delete(key);
    }
    if (!("offset" in next)) values.delete("offset");
    setParams(values);
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update({ q: input.trim() });
  }

  function changePeriod(value: SignupPeriod) {
    update({ signup_period: value, from_date: "", to_date: "" });
  }

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.user")}</p>
            <h1>{t("adminAccess.usersAccess")}</h1>
            <p>{t("adminAccess.usersDescription")}</p>
          </div>
        </header>

        <form className="access-admin-search" onSubmit={submit} role="search">
          <label>
            {t("adminAccess.searchUsers")}
            <input
              aria-label={t("adminAccess.searchUsers")}
              onChange={(event) => setInput(event.currentTarget.value)}
              placeholder={t("adminAccess.searchPlaceholder")}
              type="search"
              value={input}
            />
          </label>
          <button className="access-admin-button access-admin-button--primary" type="submit">
            {t("adminAccess.search")}
          </button>
        </form>

        <div className="access-user-filters">
          <label>
            {t("adminAccess.signupDateFilter")}
            <select aria-label={t("adminAccess.signupDateFilter")} value={period} onChange={(event) => changePeriod(event.currentTarget.value as SignupPeriod)}>
              {SIGNUP_PERIODS.map((item) => (
                <option key={item} value={item}>{t(`adminAccess.signupPeriods.${item}`)}</option>
              ))}
            </select>
          </label>
          {period === "custom" && (
            <>
              <label>
                {t("adminAccess.fromDate")}
                {english
                  ? (
                    <input
                      aria-label={t("adminAccess.fromDate")}
                      max={isValidIsoDate(toDate) ? toDate : undefined}
                      onChange={(event) => update({ from_date: event.currentTarget.value })}
                      type="date"
                      value={fromDate}
                    />
                  )
                  : (
                    <PersianDatePicker
                      ariaLabel={t("adminAccess.fromDate")}
                      max={isValidIsoDate(toDate) ? toDate : undefined}
                      onChange={(value) => update({ from_date: value })}
                      value={fromDate}
                    />
                  )}
              </label>
              <label>
                {t("adminAccess.toDate")}
                {english
                  ? (
                    <input
                      aria-label={t("adminAccess.toDate")}
                      min={isValidIsoDate(fromDate) ? fromDate : undefined}
                      onChange={(event) => update({ to_date: event.currentTarget.value })}
                      type="date"
                      value={toDate}
                    />
                  )
                  : (
                    <PersianDatePicker
                      ariaLabel={t("adminAccess.toDate")}
                      min={isValidIsoDate(fromDate) ? fromDate : undefined}
                      onChange={(value) => update({ to_date: value })}
                      value={toDate}
                    />
                  )}
              </label>
            </>
          )}
          <label>
            {t("adminAccess.sortUsers")}
            <select aria-label={t("adminAccess.sortUsers")} value={sort} onChange={(event) => update({ sort: event.currentTarget.value })}>
              {SORT_ORDERS.map((item) => (
                <option key={item} value={item}>{t(`adminAccess.userSort.${item}`)}</option>
              ))}
            </select>
          </label>
        </div>

        {customRangeIncomplete && (
          <p className="access-admin-status" role="status">
            {customRangeInvalid ? t("adminAccess.customRangeInvalid") : t("adminAccess.customRangeNeedsBoth")}
          </p>
        )}
        {state === "loading" && !customRangeIncomplete && (
          <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>
        )}
        {state === "error" && !customRangeIncomplete && (
          <AppErrorNotice
            audience="admin"
            context="access"
            error={loadError}
            locale={english ? "en" : "fa"}
            onRetry={() => setRetryKey((value) => value + 1)}
          />
        )}
        {state === "ready" && page !== null && (
          <>
            <p className="access-user-total" role="status">
              {t("adminAccess.totalUsersFound", { count: page.total.toLocaleString(english ? "en-US" : "fa-IR") })}
            </p>
            {page.items.length === 0
              ? <p className="access-admin-status">{t("adminAccess.noUsers")}</p>
              : <UserList users={page.items} locale={locale} />}
            <UserPagination page={page} offset={offset} update={update} />
          </>
        )}
      </div>
    </main>
  );
}

function UserList({ users, locale }: { users: readonly AdminMemberSummary[]; locale: string }) {
  const { t } = useTranslation();
  return (
    <div className="access-user-list">
      {users.map((user) => (
        <article className="access-user-card" data-testid={`access-user-${user.user_id}`} key={user.user_id}>
          <div className="access-user-card__identity">
            <span className="access-admin-code">{user.user_id}</span>
            <h2>{user.display_name ?? user.email ?? user.phone_number ?? user.user_id}</h2>
            <p>{user.email ?? user.phone_number ?? "—"}</p>
          </div>
          <dl className="access-user-card__facts">
            <Fact label={t("adminAccess.signupDate")} value={formatDate(user.created_at, locale)} />
            <Fact label={t("adminAccess.currentPackage")} value={t(`entitlements.packageLabels.${user.primary_package}`, { defaultValue: user.primary_package })} />
            <Fact label={t("adminAccess.trialState")} value={user.trial_active ? t("entitlements.trialActive") : t("adminAccess.inactive")} />
            <Fact label={t("adminAccess.accessEnd")} value={user.paid_access_end ? formatDate(user.paid_access_end, locale) : "—"} />
            <Fact
              label={t("adminAccess.lastActivity")}
              value={user.last_activity_at ? formatTehranDateTimeForLocale(user.last_activity_at, locale) : t("adminAccess.noActivity")}
            />
          </dl>
          <Link className="access-admin-button access-admin-button--quiet" to={`/admin/billing/users/${user.user_id}`}>
            {t("adminAccess.viewAccess")}
          </Link>
        </article>
      ))}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function UserPagination({ page, offset, update }: { page: Page<AdminMemberSummary>; offset: number; update: (next: Record<string, string>) => void }) {
  const { t } = useTranslation();
  return (
    <nav className="access-user-pagination" aria-label={t("adminAccess.userPagination")}>
      <button
        className="access-admin-button access-admin-button--quiet"
        disabled={offset <= 0}
        onClick={() => update({ offset: String(Math.max(0, offset - PAGE_SIZE)) })}
        type="button"
      >
        {t("adminAccess.previousPage")}
      </button>
      <span>{t("adminAccess.pageOf", { current: Math.floor(offset / PAGE_SIZE) + 1, total: Math.max(1, Math.ceil(page.total / PAGE_SIZE)) })}</span>
      <button
        className="access-admin-button access-admin-button--quiet"
        disabled={offset + page.items.length >= page.total}
        onClick={() => update({ offset: String(offset + PAGE_SIZE) })}
        type="button"
      >
        {t("adminAccess.nextPage")}
      </button>
    </nav>
  );
}

function parseOffset(value: string | null): number {
  if (value === null || !/^(0|[1-9]\d*)$/.test(value)) return 0;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) return 0;
  return Math.min(parsed, MAX_OFFSET);
}

function parseChoice<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.find((option) => option === value) ?? fallback;
}

function isValidIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function formatDate(value: string, locale: string): string {
  return formatTehranDateForLocale(value, locale);
}
