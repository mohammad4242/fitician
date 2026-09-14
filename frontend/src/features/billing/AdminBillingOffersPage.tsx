import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { BillingOffer } from "@fitician/core/billing";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { PersianDateTimePicker } from "../../shared/PersianDateTimePicker";

import {
  getAdminBillingOffers,
  type AdminBillingOffer,
  type UpdateAdminBillingOfferInput,
  updateAdminBillingOffer,
} from "./adminApi";
import "./billing.css";

const offerCategories = [
  {
    key: "training",
    labelKey: "adminAccess.offerCategories.training",
    packageCodes: ["training", "training_coach"],
  },
  {
    key: "nutrition",
    labelKey: "adminAccess.offerCategories.nutrition",
    packageCodes: ["nutrition", "nutrition_physician"],
  },
  {
    key: "complete",
    labelKey: "adminAccess.offerCategories.complete",
    packageCodes: ["complete", "complete_care"],
  },
] as const;

type OfferCategoryKey = (typeof offerCategories)[number]["key"];

export function AdminBillingOffersPage() {
  const { i18n, t } = useTranslation();
  const [offers, setOffers] = useState<AdminBillingOffer[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [saveError, setSaveError] = useState<unknown | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [updated, setUpdated] = useState<string | null>(null);
  const [openCategoryKey, setOpenCategoryKey] = useState<OfferCategoryKey | null>(null);
  const [openOfferCode, setOpenOfferCode] = useState<string | null>(null);
  const savedOffers = useRef(new Map<string, AdminBillingOffer>());

  useEffect(() => {
    let active = true;
    void getAdminBillingOffers()
      .then((result) => {
        if (!active) return;
        setOffers(result);
        savedOffers.current = new Map(result.map((offer) => [offer.offer_code, offer]));
        setLoadError(null);
        setState("ready");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setLoadError(cause);
        setState("error");
      });
    return () => { active = false; };
  }, []);

  async function saveOffer(offer: AdminBillingOffer) {
    const previous = savedOffers.current.get(offer.offer_code);
    const input = buildUpdateInput(offer, previous);
    if (Object.keys(input).length === 0) return;
    setSaving(offer.offer_code);
    setUpdated(null);
    setSaveError(null);
    try {
      const result = await updateAdminBillingOffer(offer.offer_code, input);
      setOffers((current) => current.map((item) => item.offer_code === result.offer_code ? result : item));
      savedOffers.current.set(result.offer_code, result);
      setUpdated(result.offer_code);
    } catch (cause: unknown) {
      setSaveError(cause);
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
        {state === "error" && <AppErrorNotice audience="admin" context="billing" error={loadError} locale={i18n.resolvedLanguage === "en" ? "en" : "fa"} onRetry={() => window.location.reload()} />}
        {saveError !== null && <AppErrorNotice audience="admin" context="billing" error={saveError} locale={i18n.resolvedLanguage === "en" ? "en" : "fa"} />}
        {state === "ready" && (
          <div className="billing-admin-categories">
            {offerCategories.map((category) => {
              const categoryIsOpen = openCategoryKey === category.key;
              const categoryToggleId = `billing-admin-category-toggle-${category.key}`;
              const categoryPanelId = `billing-admin-category-panel-${category.key}`;

              return (
                <section
                  className={`billing-admin-category${categoryIsOpen ? " is-open" : ""}`}
                  data-testid={`billing-admin-category-${category.key}`}
                  key={category.key}
                >
                  <header className="billing-admin-category__header">
                    <button
                      aria-controls={categoryPanelId}
                      aria-expanded={categoryIsOpen}
                      className="billing-admin-category__toggle"
                      id={categoryToggleId}
                      onClick={() => toggleCategory(category.key)}
                      type="button"
                    >
                      <span className="billing-admin-category__name">{t(category.labelKey)}</span>
                      <span aria-hidden="true" className="billing-admin-chevron" />
                    </button>
                  </header>
                  <div
                    aria-hidden={!categoryIsOpen}
                    aria-labelledby={categoryToggleId}
                    className={`billing-admin-category__panel${categoryIsOpen ? " is-open" : ""}`}
                    id={categoryPanelId}
                    inert={!categoryIsOpen}
                    role="region"
                  >
                    <div className="billing-admin-category__panel-inner">
                      <div className="billing-admin-package-groups">
                        {category.packageCodes.map((packageCode) => {
                          const packageOffers = offers
                            .filter((offer) => offer.package_code === packageCode)
                            .sort((left, right) => left.duration_weeks - right.duration_weeks);

                          return (
                            <section
                              className="billing-admin-package-group"
                              data-testid={`billing-admin-package-${packageCode}`}
                              key={packageCode}
                            >
                              <header>
                                <h2>{packageLabel(packageCode, t)}</h2>
                              </header>
                              <div className="billing-admin-package-group__offers">
                                {packageOffers.map((offer) => renderOfferCard(offer))}
                              </div>
                            </section>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </section>
              );
            })}
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

  function toggleCategory(categoryKey: OfferCategoryKey) {
    setOpenCategoryKey((current) => current === categoryKey ? null : categoryKey);
    setOpenOfferCode(null);
  }

  function renderOfferCard(offer: AdminBillingOffer) {
    const offerIsOpen = openOfferCode === offer.offer_code;

    return (
      <article
        className={`billing-admin-card${offerIsOpen ? " is-open" : ""}`}
        data-testid={`admin-offer-${offer.offer_code}`}
        key={offer.offer_code}
      >
        <header className="billing-admin-card__header">
          <button
            aria-controls={`admin-offer-panel-${offer.offer_code}`}
            aria-expanded={offerIsOpen}
            className="billing-admin-card__toggle"
            onClick={() => setOpenOfferCode((current) => current === offer.offer_code ? null : offer.offer_code)}
            type="button"
          >
            <span className="billing-admin-card__summary">
              <span className="billing-admin-card__code">{offer.offer_code}</span>
              <span className="billing-admin-card__name">
                {packageLabel(offer.package_code, t)}
              </span>
              <span className="billing-admin-card__duration">{durationLabel(offer.duration_weeks, t)}</span>
            </span>
            <span className="billing-admin-card__summary-end">
              <span className="billing-admin-card__availability">
                {offer.is_active ? t("billing.active") : t("adminAccess.inactive")}
              </span>
              <span aria-hidden="true" className="billing-admin-chevron" />
            </span>
          </button>
        </header>
        <div
          aria-hidden={!offerIsOpen}
          className={`billing-admin-card__panel${offerIsOpen ? " is-open" : ""}`}
          id={`admin-offer-panel-${offer.offer_code}`}
          inert={!offerIsOpen}
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
              <div>
                <PersianDateTimePicker
                  ariaLabel={t("billing.availableFrom")}
                  label={t("billing.availableFrom")}
                  onChange={(value) => updateOffer(offer.offer_code, { available_from: value })}
                  value={offer.available_from}
                />
              </div>
              <div>
                <PersianDateTimePicker
                  ariaLabel={t("billing.availableUntil")}
                  label={t("billing.availableUntil")}
                  onChange={(value) => updateOffer(offer.offer_code, { available_until: value })}
                  value={offer.available_until}
                />
              </div>
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
    );
  }
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

function packageLabel(packageCode: BillingOffer["package_code"], t: (key: string) => string) {
  if (packageCode === "complete_care") return t("adminAccess.completeCareLabel");
  return t(`entitlements.packageLabels.${packageCode}`);
}
