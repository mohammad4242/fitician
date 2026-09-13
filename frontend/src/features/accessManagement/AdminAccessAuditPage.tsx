import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  getAdminAuditEvents,
  type AdminAuditEvent,
} from "./adminAccessApi";

const auditActions = [
  "billing.offer.updated",
  "access.campaign.created",
  "access.campaign.updated",
  "access.campaign.activated",
  "access.campaign.deactivated",
  "access.grant.created",
  "access.grant.revoked",
  "access.campaign.manually_redeemed",
] as const;

type AuditFilters = {
  action: string;
  actor_user_id: string;
  target_user_id: string;
  resource_type: string;
  from_datetime: string;
  to_datetime: string;
};

const initialFilters: AuditFilters = {
  action: "",
  actor_user_id: "",
  target_user_id: "",
  resource_type: "",
  from_datetime: "",
  to_datetime: "",
};

export function AdminAccessAuditPage() {
  const { i18n, t } = useTranslation();
  const [events, setEvents] = useState<AdminAuditEvent[]>([]);
  const [filters, setFilters] = useState<AuditFilters>(initialFilters);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    void loadEvents(initialFilters);
  }, []);

  async function loadEvents(next: AuditFilters) {
    setState("loading");
    try {
      const result = await getAdminAuditEvents({
        action: optional(next.action),
        actor_user_id: optional(next.actor_user_id),
        target_user_id: optional(next.target_user_id),
        resource_type: optional(next.resource_type),
        from_datetime: toIsoDateTime(next.from_datetime),
        to_datetime: toIsoDateTime(next.to_datetime),
      });
      setEvents(result);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadEvents(filters);
  }

  return (
    <main className="access-admin-page fitsho-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div><p className="eyebrow eyebrow--accent">{t("adminAccess.audit")}</p><h1>{t("adminAccess.changeHistory")}</h1><p>{t("adminAccess.auditDescription", "تغییرات حساس مدیریتی به‌صورت خواندنی و قابل پیگیری ثبت می‌شوند.")}</p></div>
        </header>

        <form className="access-admin-search access-audit-filters" onSubmit={submit}>
          <label>{t("adminAccess.action", "عملیات")}<select aria-label={t("adminAccess.action", "عملیات")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, action: value })); }} value={filters.action}><option value="">{t("adminAccess.all")}</option>{auditActions.map((action) => <option key={action} value={action}>{action}</option>)}</select></label>
          <label>{t("adminAccess.actor")}<input aria-label={t("adminAccess.actor")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, actor_user_id: value })); }} value={filters.actor_user_id} /></label>
          <label>{t("adminAccess.targetUser")}<input aria-label={t("adminAccess.targetUser")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, target_user_id: value })); }} value={filters.target_user_id} /></label>
          <label>{t("adminAccess.resource")}<input aria-label={t("adminAccess.resource")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, resource_type: value })); }} value={filters.resource_type} /></label>
          <label>{t("adminAccess.from", "از")}<input aria-label={t("adminAccess.from", "از")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, from_datetime: value })); }} type="datetime-local" value={filters.from_datetime} /></label>
          <label>{t("adminAccess.to", "تا")}<input aria-label={t("adminAccess.to", "تا")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, to_datetime: value })); }} type="datetime-local" value={filters.to_datetime} /></label>
          <button className="access-admin-button access-admin-button--primary" type="submit">{t("adminAccess.applyFilters", "اعمال فیلتر")}</button>
        </form>

        {state === "loading" && <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>}
        {state === "error" && <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.loadError")}</p>}
        {state === "ready" && events.length === 0 && <p className="access-admin-status">{t("adminAccess.noAuditEvents")}</p>}
        {state === "ready" && events.length > 0 && <div className="access-audit-list">{events.map((event) => <AuditRow english={english} event={event} key={event.id} t={t} />)}</div>}
      </div>
    </main>
  );
}

function AuditRow({ event, english, t }: { event: AdminAuditEvent; english: boolean; t: (key: string) => string }) {
  const actor = event.actor?.display_name ?? event.actor?.email ?? event.actor?.phone_number ?? "—";
  const target = event.target?.display_name ?? event.target?.email ?? event.target?.phone_number ?? "—";
  return (
    <article className="access-audit-card" data-testid={`admin-audit-event-${event.id}`}>
      <header>
        <time dateTime={event.created_at}>{formatDate(event.created_at, english)}</time>
        <span>{actionLabel(event.action, t)}</span>
      </header>
      <p><strong>{actor}</strong> · {actionLabel(event.action, t)} · <strong>{target}</strong></p>
      <dl><div><dt>{t("adminAccess.resource")}</dt><dd>{event.resource_type} / {event.resource_key}</dd></div><div><dt>{t("adminAccess.reason")}</dt><dd>{event.reason ?? "—"}</dd></div></dl>
      <details><summary>{t("adminAccess.details", "جزئیات")}</summary><div className="access-audit-card__state"><div><h3>{t("adminAccess.before")}</h3><pre>{formatState(event.before_state)}</pre></div><div><h3>{t("adminAccess.after")}</h3><pre>{formatState(event.after_state)}</pre></div></div></details>
    </article>
  );
}

function actionLabel(action: string, t: (key: string) => string): string {
  const labels: Record<string, string> = {
    "billing.offer.updated": t("adminAccess.offerUpdated"),
    "access.campaign.created": t("adminAccess.campaignCreated"),
    "access.campaign.updated": t("adminAccess.campaignUpdated"),
    "access.campaign.activated": t("adminAccess.campaignActivated"),
    "access.campaign.deactivated": t("adminAccess.campaignDeactivated"),
    "access.grant.created": t("adminAccess.grantCreated"),
    "access.grant.revoked": t("adminAccess.grantRevoked"),
    "access.campaign.manually_redeemed": t("adminAccess.campaignManuallyRedeemed"),
  };
  return labels[action] ?? action;
}

function optional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed === "" ? undefined : trimmed;
}

function toIsoDateTime(value: string): string | undefined {
  return value === "" ? undefined : new Date(value).toISOString();
}

function formatState(state: Record<string, unknown> | null): string {
  return state === null ? "—" : JSON.stringify(state, null, 2);
}

function formatDate(value: string, english: boolean): string {
  return new Intl.DateTimeFormat(english ? "en" : "fa-IR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
