import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import type { BillingOffer } from "@fitician/core/billing";

import { useEntitlements } from "../entitlements/EntitlementContext";
import { getOffers } from "./api";
import "./billing.css";

const packageOrder = [
  "training",
  "training_coach",
  "nutrition",
  "nutrition_physician",
  "complete",
  "complete_care",
] as const;

export function PlansPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { snapshot } = useEntitlements();
  const [offers, setOffers] = useState<BillingOffer[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [requiredEntitlement] = useState(() => searchParams.get("required"));
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    let active = true;
    setState("loading");
    void getOffers()
      .then((result) => {
        if (!active) return;
        setOffers(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, []);

  const groupedOffers = useMemo(() => {
    const groups = new Map<string, BillingOffer[]>();
    for (const offer of offers) {
      const group = groups.get(offer.package_code) ?? [];
      group.push(offer);
      groups.set(offer.package_code, group);
    }
    return [...groups.entries()].sort(([first], [second]) => {
      const firstIndex = packageOrder.indexOf(first as (typeof packageOrder)[number]);
      const secondIndex = packageOrder.indexOf(second as (typeof packageOrder)[number]);
      return (firstIndex === -1 ? packageOrder.length : firstIndex)
        - (secondIndex === -1 ? packageOrder.length : secondIndex);
    });
  }, [offers]);

  return (
    <main className="billing-page fitsho-page">
      <div className="billing-page__container">
        <header className="billing-hero">
          <p className="eyebrow eyebrow--accent">{t("billing.plans")}</p>
          <h1>{t("billing.choosePlan")}</h1>
          <p>{t("billing.chooseDuration")}</p>
        </header>

        {snapshot && (
          <section className="billing-access-summary" aria-label={t("billing.currentPlan")}>
            <div>
              <span>{t("billing.currentPlan")}</span>
              <strong>{t(`entitlements.packageLabels.${snapshot.primary_package}`, { defaultValue: snapshot.primary_package })}</strong>
            </div>
            {snapshot.trial.active && snapshot.trial.ends_at && (
              <span>{t("billing.trialExpiration", { date: formatDate(snapshot.trial.ends_at, english) })}</span>
            )}
          </section>
        )}

        {state === "loading" && <p className="billing-status" role="status">{t("billing.loading")}</p>}
        {state === "error" && <p className="billing-status billing-status--danger" role="alert">{t("billing.loadError")}</p>}
        {state === "ready" && offers.length === 0 && <p className="billing-status">{t("billing.noOffers")}</p>}
        {state === "ready" && groupedOffers.length > 0 && (
          <div className="billing-offer-groups">
            {groupedOffers.map(([packageCode, packageOffers]) => (
              <section className="billing-package" key={packageCode}>
                <header className="billing-package__header">
                  <h2>{t(`entitlements.packageLabels.${packageCode}`, { defaultValue: packageCode })}</h2>
                  {snapshot?.primary_package === packageCode && <span>{t("billing.accessActive")}</span>}
                </header>
                <div className="billing-offer-grid">
                  {[...packageOffers].sort((first, second) => first.duration_weeks - second.duration_weeks).map((offer) => {
                    const eligible = requiredEntitlement !== null
                      && offer.entitlements.includes(requiredEntitlement as BillingOffer["entitlements"][number]);
                    const duration = durationLabel(offer.duration_weeks, t);
                    return (
                      <article
                        className={`billing-offer${eligible ? " billing-offer--eligible" : ""}${offer.is_available ? "" : " billing-offer--unavailable"}`}
                        data-testid={`billing-offer-${offer.offer_code}`}
                        key={offer.offer_code}
                      >
                        <div className="billing-offer__meta">
                          <span>{t("billing.chooseDuration")}</span>
                          <strong>{duration}</strong>
                        </div>
                        <p className="billing-offer__price">
                          {offer.price_irr === null || offer.currency === null
                            ? t("billing.offerUnavailable")
                            : formatAmount(offer.price_irr, offer.currency, english)}
                        </p>
                        {!offer.is_available && <p className="billing-offer__notice">{t("billing.offerUnavailable")}</p>}
                        <button
                          aria-label={`${t("billing.buy")} ${duration}`}
                          className="billing-button billing-button--primary"
                          disabled={!offer.is_available}
                          onClick={() => navigate(`/billing/checkout/${offer.offer_code}`, { state: { offer } })}
                          type="button"
                        >
                          {t("billing.buy")}
                        </button>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function durationLabel(duration: BillingOffer["duration_weeks"], t: (key: string) => string) {
  if (duration === 4) return t("billing.fourWeeks");
  if (duration === 6) return t("billing.sixWeeks");
  return t("billing.eightWeeks");
}

function formatAmount(amount: number, currency: string, english: boolean) {
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(amount)} ${currency}`;
}

function formatDate(value: string, english: boolean) {
  return new Intl.DateTimeFormat(english ? "en" : "fa-IR", { dateStyle: "medium" }).format(new Date(value));
}
