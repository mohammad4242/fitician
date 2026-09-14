import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { useEntitlements } from "../entitlements/EntitlementContext";
import { getOrder, verifyPayment } from "./api";
import "./billing.css";

export function CheckoutResultPage() {
  const { i18n, t } = useTranslation();
  const [searchParams] = useSearchParams();
  const { refresh } = useEntitlements();
  const [state, setState] = useState<"loading" | "success" | "failed">("loading");
  const [error, setError] = useState<unknown | null>(null);
  const english = i18n.resolvedLanguage === "en";

  const transactionId = searchParams.get("transaction_id");
  const orderId = searchParams.get("order_id");
  const providerReference = searchParams.get("provider_reference");

  useEffect(() => {
    let active = true;
    setError(null);
    if (transactionId === null || orderId === null) {
      setState("failed");
      return () => { active = false; };
    }
    void getOrder(orderId)
      .then(async (order) => {
        if (!active) return;
        const result = await verifyPayment(order.provider, {
          transaction_id: transactionId,
          provider_reference: providerReference,
        });
        if (!active) return;
        if (result.verified) {
          await refresh();
          if (active) setState("success");
        } else {
          setState("failed");
        }
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(cause);
        setState("failed");
      });
    return () => { active = false; };
  }, [orderId, providerReference, refresh, transactionId]);

  const success = state === "success";
  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container billing-page__container--narrow">
        {state === "loading" && <p className="billing-status" role="status">{t("billing.paymentPending")}</p>}
        {state === "failed" && error !== null && <AppErrorNotice audience="member" context="billing" error={error} locale={english ? "en" : "fa"} />}
        {state !== "loading" && error === null && (
          <section className={`billing-result billing-result--${success ? "success" : "failed"}`}>
            <p className="eyebrow eyebrow--accent">{t("billing.plans")}</p>
            <h1>{success ? t("billing.paymentSuccessful") : t("billing.paymentFailed")}</h1>
            <p>{success ? t("billing.accessActive") : t("billing.paymentFailed")}</p>
            <div className="billing-result__actions">
              <Link className="billing-button billing-button--primary" to={success ? "/dashboard" : "/plans"}>
                {success ? t("common.brand") : t("billing.viewPlans")}
              </Link>
              <Link className="billing-button billing-button--secondary" to="/billing/history">
                {t("billing.purchaseHistory")}
              </Link>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
