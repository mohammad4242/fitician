import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { BillingOffer } from "@fitician/core/billing";

import {
  getAdminBillingOffers,
  type AdminBillingOffer,
  type UpdateAdminBillingOfferInput,
  updateAdminBillingOffer,
} from "./adminApi";
import "./billing.css";

export function AdminBillingOffersPage() {
  const { t } = useTranslation();
  const [offers, setOffers] = useState<AdminBillingOffer[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState<string | null>(null);
  const [updated, setUpdated] = useState<string | null>(null);
  const [openOfferCode, setOpenOfferCode] = useState<string | null>(null);
  const savedOffers = useRef(new Map<string, AdminBillingOffer>());

  useEffect(() => {
    let active = true;
    void getAdminBillingOffers()
      .then((result) => {
        if (!active) return;
        setOffers(result);
        savedOffers.current = new Map(result.map((offer) => [offer.offer_code, offer]));
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, []);

  async function saveOffer(offer: AdminBillingOffer) {
    const previous = savedOffers.current.get(offer.offer_code);
    const input = buildUpdateInput(offer, previous);
    if (Object.keys(input).length === 0) return;
    setSaving(offer.offer_code);
    setUpdated(null);
    try {
      const result = await updateAdminBillingOffer(offer.offer_code, input);
      setOffers((current) => current.map((item) => item.offer_code === result.offer_code ? result : item));
      savedOffers.current.set(result.offer_code, result);
      setUpdated(result.offer_code);
    } catch {
      setState("error");
    } finally {
      setSaving(null);
    }
  }

  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container">
        <header className="billing-hero">
          <p className="eyebrow eyebrow--accent">{t("billing.manageAccess")}</p>
          <h1>{t("billing.adminOffers")}</h1>
          <p>{t("billing.choosePlan")}</p>
        </header>
        {state === "loading" && <p className="billing-status" role="status">{t("billing.loading")}</p>}
        {state === "error" && <p className="billing-status billing-status--danger" role="alert">{t("billing.adminLoadError")}</p>}
        {state === "ready" && (
          <div className="billing-admin-list">
            {offers.map((offer) => (
              <article
                className={`billing-admin-card${openOfferCode === offer.offer_code ? " is-open" : ""}`}
                data-testid={`admin-offer-${offer.offer_code}`}
                key={offer.offer_code}
              >
                <header className="billing-admin-card__header">
                  <button
                    aria-controls={`admin-offer-panel-${offer.offer_code}`}
                    aria-expanded={openOfferCode === offer.offer_code}
                    className="billing-admin-card__toggle"
                    onClick={() => setOpenOfferCode((current) => current === offer.offer_code ? null : offer.offer_code)}
                    type="button"
                  >
                    <span className="billing-admin-card__summary">
                      <span className="billing-admin-card__code">{offer.offer_code}</span>
                      <span className="billing-admin-card__name" role="heading" aria-level={2}>
                        {t(`entitlements.packageLabels.${offer.package_code}`, { defaultValue: offer.package_code })}
                      </span>
                      <span className="billing-admin-card__duration">{durationLabel(offer.duration_weeks, t)}</span>
                    </span>
                    <span className="billing-admin-card__summary-end">
                      <span className="billing-admin-card__availability">
                        {offer.is_active ? t("billing.active") : t("adminAccess.inactive")}
                      </span>
                      <span aria-hidden="true" className="billing-admin-card__chevron" />
                    </span>
                  </button>
                </header>
                <div
                  aria-hidden={openOfferCode !== offer.offer_code}
                  className={`billing-admin-card__panel${openOfferCode === offer.offer_code ? " is-open" : ""}`}
                  id={`admin-offer-panel-${offer.offer_code}`}
                  inert={openOfferCode !== offer.offer_code}
                >
                  <div className="billing-admin-card__panel-inner">
                    <div className="billing-admin-card__fields">
                      <label>
                        {t("billing.price")}
                        <input
                          aria-label={t("billing.price")}
                          min="0"
                          onChange={(event) => updateOffer(offer.offer_code, { price_irr: event.currentTarget.value === "" ? null : Number(event.currentTarget.value) })}
                          type="number"
                          value={offer.price_irr ?? ""}
                        />
                      </label>
                      <label>
                        {t("billing.availableFrom")}
                        <input
                          aria-label={t("billing.availableFrom")}
                          onChange={(event) => updateOffer(offer.offer_code, { available_from: toIsoDateTime(event.currentTarget.value) })}
                          type="datetime-local"
                          value={toDateTimeLocal(offer.available_from)}
                        />
                      </label>
                      <label>
                        {t("billing.availableUntil")}
                        <input
                          aria-label={t("billing.availableUntil")}
                          onChange={(event) => updateOffer(offer.offer_code, { available_until: toIsoDateTime(event.currentTarget.value) })}
                          type="datetime-local"
                          value={toDateTimeLocal(offer.available_until)}
                        />
                      </label>
                      <label className="billing-admin-card__check">
                        <input
                          aria-label={t("billing.active")}
                          checked={offer.is_active}
                          onChange={(event) => updateOffer(offer.offer_code, { is_active: event.currentTarget.checked })}
                          type="checkbox"
                        />
                        {t("billing.active")}
                      </label>
                    </div>
                    <footer>
                      <button
                        className="billing-button billing-button--primary"
                        disabled={saving === offer.offer_code}
                        onClick={() => void saveOffer(offer)}
                        type="button"
                      >
                        {saving === offer.offer_code ? t("billing.saving") : t("billing.save")}
                      </button>
                      {updated === offer.offer_code && <span className="billing-admin-card__success" role="status">{t("billing.updateSuccess")}</span>}
                    </footer>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );

  function updateOffer(
    code: BillingOffer["offer_code"],
    changes: {
      price_irr?: number | null;
      is_active?: boolean;
      available_from?: string | null;
      available_until?: string | null;
    },
  ) {
    setUpdated(null);
    setOffers((current) => current.map((offer) => offer.offer_code === code ? { ...offer, ...changes } : offer));
  }
}

function toDateTimeLocal(value: string | null): string {
  if (value === null) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const timezoneOffset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 16);
}

function toIsoDateTime(value: string): string | null {
  return value === "" ? null : new Date(value).toISOString();
}

function buildUpdateInput(offer: AdminBillingOffer, previous: AdminBillingOffer | undefined): UpdateAdminBillingOfferInput {
  if (previous === undefined) return offer.price_irr === null ? {} : { price_irr: offer.price_irr, is_active: offer.is_active };
  const input: UpdateAdminBillingOfferInput = {};
  if (offer.price_irr !== previous.price_irr && offer.price_irr !== null) input.price_irr = offer.price_irr;
  if (offer.is_active !== previous.is_active) input.is_active = offer.is_active;
  if (offer.available_from !== previous.available_from) input.available_from = offer.available_from;
  if (offer.available_until !== previous.available_until) input.available_until = offer.available_until;
  if (offer.currency !== previous.currency) input.currency = offer.currency ?? undefined;
  return input;
}

function durationLabel(duration: BillingOffer["duration_weeks"], t: (key: string) => string) {
  if (duration === 4) return t("billing.fourWeeks");
  if (duration === 6) return t("billing.sixWeeks");
  return t("billing.eightWeeks");
}
