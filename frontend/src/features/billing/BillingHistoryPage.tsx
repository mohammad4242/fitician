import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatTehranDateForLocale } from "@fitician/core";
import type { BillingOrder } from "@fitician/core/billing";

import { getOrders } from "./api";
import "./billing.css";

export function BillingHistoryPage() {
  const { i18n, t } = useTranslation();
  const [orders, setOrders] = useState<BillingOrder[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    let active = true;
    void getOrders()
      .then((result) => {
        if (!active) return;
        setOrders(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, []);

  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container billing-page__container--narrow">
        <header className="billing-hero">
          <p className="eyebrow eyebrow--accent">{t("billing.manageAccess")}</p>
          <h1>{t("billing.purchaseHistory")}</h1>
        </header>
        {state === "loading" && <p className="billing-status" role="status">{t("billing.loading")}</p>}
        {state === "error" && <p className="billing-status billing-status--danger" role="alert">{t("billing.historyError")}</p>}
        {state === "ready" && orders.length === 0 && <p className="billing-status">{t("billing.noOffers")}</p>}
        {state === "ready" && orders.length > 0 && (
          <div className="billing-history-list">
            {orders.map((order) => (
              <article className="billing-history-card" key={order.id}>
                <div>
                  <strong>{t(`entitlements.packageLabels.${order.package_code_snapshot}`, { defaultValue: order.package_code_snapshot })}</strong>
                  <span>{durationLabel(order.duration_weeks_snapshot, t)} · {order.offer_code}</span>
                </div>
                <div>
                  <strong>{formatAmount(order.amount_irr_snapshot, order.currency_snapshot, english)}</strong>
                  <span>{statusLabel(order.status, t)}</span>
                  <time dateTime={order.created_at}>{formatDate(order.created_at, english)}</time>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function durationLabel(duration: BillingOrder["duration_weeks_snapshot"], t: (key: string) => string) {
  if (duration === 4) return t("billing.fourWeeks");
  if (duration === 6) return t("billing.sixWeeks");
  return t("billing.eightWeeks");
}

function statusLabel(status: BillingOrder["status"], t: (key: string) => string) {
  if (status === "paid") return t("billing.paymentSuccessful");
  if (status === "pending") return t("billing.paymentPending");
  if (status === "failed") return t("billing.paymentFailed");
  if (status === "cancelled") return t("billing.paymentCancelled");
  if (status === "refunded") return t("billing.refund");
  return status;
}

function formatAmount(amount: number, currency: string, english: boolean) {
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(amount)} ${currency}`;
}

function formatDate(value: string, english: boolean) {
  return formatTehranDateForLocale(value, english ? "en" : "fa-IR");
}
