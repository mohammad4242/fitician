import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatTehranDateForLocale } from "@fitician/core";
import {
  billingOrderStatuses,
  paymentProviderCodes,
  type BillingOrderStatus,
  type PaymentProviderCode,
} from "@fitician/core/billing";

import { AppErrorNotice } from "../../shared/AppErrorNotice";

import {
  getAdminBillingOrders,
  type AdminBillingOrder,
} from "./adminApi";

type OrderFilters = {
  status: BillingOrderStatus | "";
  provider: PaymentProviderCode | "";
  user_id: string;
};

const initialFilters: OrderFilters = { status: "", provider: "", user_id: "" };

export function AdminBillingOrdersPage() {
  const { i18n, t } = useTranslation();
  const [orders, setOrders] = useState<AdminBillingOrder[]>([]);
  const [filters, setFilters] = useState<OrderFilters>(initialFilters);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    void loadOrders(initialFilters);
  }, []);

  async function loadOrders(next: OrderFilters) {
    setState("loading");
    try {
      const result = await getAdminBillingOrders({
        status: next.status === "" ? undefined : next.status,
        provider: next.provider === "" ? undefined : next.provider,
        user_id: next.user_id.trim() === "" ? undefined : next.user_id.trim(),
      });
      setOrders(result);
      setLoadError(null);
      setState("ready");
    } catch (cause: unknown) {
      setLoadError(cause);
      setState("error");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadOrders(filters);
  }

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.orders")}</p>
            <h1>{t("adminAccess.ordersPayments")}</h1>
            <p>{t("adminAccess.ordersDescription")}</p>
          </div>
        </header>

        <form className="access-admin-search access-order-filters" onSubmit={submit}>
          <label>{t("adminAccess.status")}<select aria-label={t("adminAccess.status")} onChange={(event) => { const value = event.currentTarget.value as OrderFilters["status"]; setFilters((current) => ({ ...current, status: value })); }} value={filters.status}><option value="">{t("adminAccess.all")}</option>{billingOrderStatuses.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
          <label>{t("adminAccess.provider")}<select aria-label={t("adminAccess.provider")} onChange={(event) => { const value = event.currentTarget.value as OrderFilters["provider"]; setFilters((current) => ({ ...current, provider: value })); }} value={filters.provider}><option value="">{t("adminAccess.all")}</option>{paymentProviderCodes.map((provider) => <option key={provider} value={provider}>{provider}</option>)}</select></label>
          <label>{t("adminAccess.user")}<input aria-label={t("adminAccess.user")} onChange={(event) => { const value = event.currentTarget.value; setFilters((current) => ({ ...current, user_id: value })); }} value={filters.user_id} /></label>
          <button className="access-admin-button access-admin-button--primary" type="submit">{t("adminAccess.applyFilters")}</button>
        </form>

        {state === "loading" && <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>}
        {state === "error" && <AppErrorNotice audience="admin" context="billing" error={loadError} locale={english ? "en" : "fa"} onRetry={() => void loadOrders(filters)} />}
        {state === "ready" && orders.length === 0 && <p className="access-admin-status">{t("adminAccess.noOrders")}</p>}
        {state === "ready" && orders.length > 0 && (
          <div className="access-order-list">
            {orders.map((order) => (
              <article className="access-order-card" data-testid={`admin-order-${order.id}`} key={order.id}>
                <header>
                  <div><span className="access-admin-code">{order.id}</span><h2>{order.offer_code}</h2><p>{t(`entitlements.packageLabels.${order.package_code_snapshot}`, { defaultValue: order.package_code_snapshot })} · {order.duration_weeks_snapshot} {t("adminAccess.weeks")}</p></div>
                  <span className="access-order-card__status"><b>{order.status}</b><small>{order.provider}</small></span>
                </header>
                <dl>
                  <div><dt>{t("adminAccess.memberId")}</dt><dd>{order.user_id ?? "—"}</dd></div>
                  <div><dt>{t("adminAccess.amount")}</dt><dd>{formatAmount(order.amount_irr_snapshot, order.currency_snapshot, english)}</dd></div>
                  <div><dt>{t("adminAccess.created")}</dt><dd>{formatDate(order.created_at, english)}</dd></div>
                  <div><dt>{t("adminAccess.accessGrant")}</dt><dd>{order.access_grant_id ?? "—"}</dd></div>
                </dl>
                <footer>
                  {order.paid_at !== null && <span>{t("adminAccess.paidAt")} {formatDate(order.paid_at, english)}</span>}
                  {order.refunded_at !== null && <span>{t("adminAccess.refundedAt")} {formatDate(order.refunded_at, english)}</span>}
                  <Link className="access-admin-button access-admin-button--quiet" to={`/admin/billing/orders/${order.id}`}>{t("adminAccess.orderDetails")}</Link>
                </footer>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function formatDate(value: string, english: boolean): string {
  return formatTehranDateForLocale(value, english ? "en" : "fa-IR");
}

function formatAmount(value: number, currency: string, english: boolean): string {
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(value)} ${currency}`;
}
