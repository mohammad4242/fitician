import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  getAdminBillingOrder,
  type AdminBillingOrder,
} from "./adminApi";

export function AdminBillingOrderDetailPage() {
  const { i18n, t } = useTranslation();
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<AdminBillingOrder | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    let active = true;
    if (orderId === undefined) {
      setState("error");
      return () => { active = false; };
    }
    void getAdminBillingOrder(orderId)
      .then((result) => {
        if (!active) return;
        setOrder(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [orderId]);

  if (state === "loading") return <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>;
  if (state === "error" || order === null) return <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.orderNotFound")}</p>;

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <Link className="access-admin-back-link" to="/admin/billing/orders">{t("adminAccess.backToOrders")}</Link>
        <header className="access-user-detail__header">
          <div><p className="eyebrow eyebrow--accent">{t("adminAccess.orderId")}</p><h1>{order.id}</h1><p>{order.status} · {order.provider}</p></div>
          {order.user_id !== null && <Link className="access-admin-button access-admin-button--quiet" to={`/admin/billing/users/${order.user_id}`}>{t("adminAccess.viewUserAccess")}</Link>}
        </header>

        <section className="access-order-detail-card" aria-labelledby="admin-order-snapshot-title">
          <header><div><p className="eyebrow eyebrow--accent">{t("adminAccess.order")}</p><h2 id="admin-order-snapshot-title">{t("adminAccess.orderSnapshot")}</h2></div><span className="access-order-card__status"><b>{order.status}</b><small>{order.provider}</small></span></header>
          <dl>
            <div><dt>{t("adminAccess.offer")}</dt><dd>{order.offer_code}</dd></div>
            <div><dt>{t("adminAccess.package")}</dt><dd>{t(`entitlements.packageLabels.${order.package_code_snapshot}`, { defaultValue: order.package_code_snapshot })}</dd></div>
            <div><dt>{t("adminAccess.trainingTerm")}</dt><dd>{order.duration_weeks_snapshot} {t("adminAccess.weeks")}</dd></div>
            <div><dt>{t("adminAccess.amount")}</dt><dd>{formatAmount(order.amount_irr_snapshot, order.currency_snapshot, english)}</dd></div>
            <div><dt>{t("adminAccess.created")}</dt><dd>{formatDate(order.created_at, english)}</dd></div>
            <div><dt>{t("adminAccess.paidAt")}</dt><dd>{order.paid_at === null ? "—" : formatDate(order.paid_at, english)}</dd></div>
            <div><dt>{t("adminAccess.refundedAt")}</dt><dd>{order.refunded_at === null ? "—" : formatDate(order.refunded_at, english)}</dd></div>
            <div><dt>{t("adminAccess.accessGrant")}</dt><dd>{order.access_grant_id ?? "—"}</dd></div>
          </dl>
        </section>

        <section aria-label={t("adminAccess.transactions")} className="access-transaction-section">
          <header className="access-detail-section-heading"><div><p className="eyebrow eyebrow--accent">{t("adminAccess.transactions")}</p><h2>{t("adminAccess.transactions")}</h2></div><span>{order.transactions.length}</span></header>
          {order.transactions.length === 0 && <p className="access-admin-status">{t("adminAccess.noTransactions")}</p>}
          {order.transactions.length > 0 && <div className="access-transaction-list">{order.transactions.map((transaction) => <article className="access-transaction-card" key={transaction.id}><header><strong>{transaction.id}</strong><span>{transaction.status}</span></header><dl><div><dt>{t("adminAccess.provider")}</dt><dd>{transaction.provider}</dd></div><div><dt>{t("adminAccess.providerReference")}</dt><dd>{transaction.provider_reference ?? "—"}</dd></div><div><dt>{t("adminAccess.amount")}</dt><dd>{formatAmount(transaction.amount_irr, transaction.currency, english)}</dd></div><div><dt>{t("adminAccess.verifiedAt")}</dt><dd>{transaction.verified_at === null ? "—" : formatDate(transaction.verified_at, english)}</dd></div><div><dt>{t("adminAccess.failedAt")}</dt><dd>{transaction.failed_at === null ? "—" : formatDate(transaction.failed_at, english)}</dd></div><div><dt>{t("adminAccess.refundedAt")}</dt><dd>{transaction.refunded_at === null ? "—" : formatDate(transaction.refunded_at, english)}</dd></div></dl></article>)}</div>}
        </section>
      </div>
    </main>
  );
}

function formatDate(value: string, english: boolean): string {
  return new Intl.DateTimeFormat(english ? "en" : "fa-IR", { dateStyle: "medium" }).format(new Date(value));
}

function formatAmount(value: number, currency: string, english: boolean): string {
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(value)} ${currency}`;
}
