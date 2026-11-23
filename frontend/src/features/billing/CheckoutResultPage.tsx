import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { useEntitlements } from "../entitlements/EntitlementContext";
import { getOrder, verifyPayment, verifyTetraPayReturn } from "./api";
import "./billing.css";

export function CheckoutResultPage() {
  const { i18n, t } = useTranslation();
  const [searchParams] = useSearchParams();
  const { refresh } = useEntitlements();
  const [state, setState] = useState<"loading" | "success" | "failed" | "pending" | "expired">("loading");
  const [error, setError] = useState<unknown | null>(null);
  const english = i18n.resolvedLanguage === "en";

  const [attempt, setAttempt] = useState(0);
  const token = searchParams.get("token");
  const transactionId = searchParams.get("transaction_id");
  const orderId = searchParams.get("order_id");
  const providerReference = searchParams.get("provider_reference");

  useEffect(() => {
    let active = true;
    setError(null);
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (token === null && (transactionId === null || orderId === null)) {
      setState("failed");
      return () => { active = false; };
    }
    const verification = token !== null ? verifyTetraPayReturn(token)
      : getOrder(orderId!).then((order) => verifyPayment(order.provider, {
        transaction_id: transactionId!, provider_reference: providerReference,
      }));
    void verification.then(async (result) => {
      if (!active) return;
      if (result.verified) {
        await refresh();
        // Keep the same idempotency key across reloads until server-confirmed completion.
        const order = await getOrder(result.order_id);
        sessionStorage.removeItem(`fitician-billing-key:${order.offer_code}`);
        if (active) setState("success");
      } else if (result.order_status === "expired") {
        setState("expired");
      } else if (["created", "pending"].includes(result.transaction_status)) {
        setState("pending");
        if (attempt < 4) timer = setTimeout(() => setAttempt((value) => value + 1), 15000);
      } else { setState("failed"); }
    }).catch((cause: unknown) => {
      if (!active) return;
      setError(cause);
      setState("pending");
    });
    return () => { active = false; clearTimeout(timer); };
  }, [orderId, providerReference, refresh, transactionId, token, attempt]);

  const success = state === "success";
  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container billing-page__container--narrow">
        {state === "loading" && <p className="billing-status" role="status">{t("billing.paymentPending")}</p>}
        {error !== null && <AppErrorNotice audience="member" context="billing" error={error} locale={english ? "en" : "fa"} />}
        {state !== "loading" && (
          <section className={`billing-result billing-result--${success ? "success" : "failed"}`}>
            <p className="eyebrow eyebrow--accent">{t("billing.plans")}</p>
            <h1>{success ? t("billing.paymentSuccessful") : state === "pending" ? t("billing.paymentPending") : state === "expired" ? (english ? "Payment expired" : "مهلت پرداخت تمام شده") : t("billing.paymentFailed")}</h1>
            <p>{success ? t("billing.accessActive") : state === "pending" ? t("billing.paymentPending") : t("billing.paymentFailed")}</p>
            <div className="billing-result__actions">
              {(state === "pending" || state === "expired") && <button className="billing-button billing-button--secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>{t("common.retry")}</button>}
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
