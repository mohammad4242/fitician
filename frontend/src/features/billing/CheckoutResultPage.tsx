import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { useEntitlements } from "../entitlements/EntitlementContext";
import { verifyPayment } from "./api";
import "./billing.css";

export function CheckoutResultPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const { refresh } = useEntitlements();
  const [state, setState] = useState<"loading" | "success" | "failed">("loading");

  const transactionId = searchParams.get("transaction_id");
  const providerReference = searchParams.get("provider_reference");

  useEffect(() => {
    let active = true;
    if (transactionId === null) {
      setState("failed");
      return () => { active = false; };
    }
    void verifyPayment("fake", {
      transaction_id: transactionId,
      provider_reference: providerReference,
    })
      .then(async (result) => {
        if (!active) return;
        if (result.verified) {
          await refresh();
          if (active) setState("success");
        } else {
          setState("failed");
        }
      })
      .catch(() => {
        if (active) setState("failed");
      });
    return () => { active = false; };
  }, [providerReference, refresh, transactionId]);

  const success = state === "success";
  return (
    <main className="billing-page fitsho-page">
      <div className="billing-page__container billing-page__container--narrow">
        {state === "loading" && <p className="billing-status" role="status">{t("billing.paymentPending")}</p>}
        {state !== "loading" && (
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
