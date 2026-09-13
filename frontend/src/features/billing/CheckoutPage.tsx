import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { paymentProviderCodes, type BillingOffer } from "@fitician/core/billing";

import { createCheckout, createOrder, getOffers } from "./api";
import "./billing.css";

export function CheckoutPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { offerCode } = useParams();
  const [offer, setOffer] = useState<BillingOffer | null>(() => {
    const stateOffer = (location.state as { offer?: BillingOffer } | null)?.offer;
    return stateOffer !== undefined && stateOffer.offer_code === offerCode ? stateOffer : null;
  });
  const [state, setState] = useState<"loading" | "ready" | "submitting" | "error">(offer ? "ready" : "loading");
  const [error, setError] = useState(false);
  const idempotencyKey = useRef(createIdempotencyKey());
  const english = i18n.resolvedLanguage === "en";
  const provider = paymentProviderCodes[0];

  useEffect(() => {
    if (offer !== null || offerCode === undefined) return;
    let active = true;
    void getOffers()
      .then((offers) => {
        if (!active) return;
        const selected = offers.find((item) => item.offer_code === offerCode) ?? null;
        setOffer(selected);
        setState(selected === null ? "error" : "ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [offer, offerCode]);

  async function beginCheckout() {
    if (offer === null || !offer.is_available) return;
    setState("submitting");
    setError(false);
    try {
      const order = await createOrder({
        offer_code: offer.offer_code,
        provider,
        client_idempotency_key: idempotencyKey.current,
      });
      const checkout = await createCheckout(order.id, { provider: order.provider });
      if (checkout.checkout_url !== null) {
        const target = new URL(checkout.checkout_url, window.location.origin);
        if (target.origin === window.location.origin) {
          navigate(`${target.pathname}${target.search}`);
        } else {
          window.location.assign(checkout.checkout_url);
        }
        return;
      }
      navigate(`/billing/checkout-result?order_id=${order.id}&transaction_id=${checkout.transaction_id}`);
    } catch {
      setError(true);
      setState("error");
    }
  }

  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container billing-page__container--narrow">
        <header className="billing-hero">
          <p className="eyebrow eyebrow--accent">{t("billing.continueToPayment")}</p>
          <h1>{offer ? t(`entitlements.packageLabels.${offer.package_code}`, { defaultValue: offer.package_code }) : t("billing.plans")}</h1>
        </header>
        {state === "loading" && <p className="billing-status" role="status">{t("billing.loading")}</p>}
        {state === "error" && (
          <p className="billing-status billing-status--danger" role="alert">
            {error ? t("billing.orderError") : t("billing.offerUnavailable")}
          </p>
        )}
        {offer && state !== "loading" && (
          <section className="billing-checkout-card" aria-label={t("billing.continueToPayment")}>
            <div className="billing-checkout-card__row">
              <span>{t("billing.chooseDuration")}</span>
              <strong>{durationLabel(offer.duration_weeks, t)}</strong>
            </div>
            <div className="billing-checkout-card__row">
              <span>{t("billing.price")}</span>
              <strong>{offer.price_irr === null || offer.currency === null ? t("billing.offerUnavailable") : formatAmount(offer.price_irr, offer.currency, english)}</strong>
            </div>
            <button
              className="billing-button billing-button--primary"
              disabled={!offer.is_available || state === "submitting"}
              onClick={() => void beginCheckout()}
              type="button"
            >
              {state === "submitting" ? t("billing.paymentPending") : t("billing.continueToPayment")}
            </button>
          </section>
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

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
