import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  billingCategories,
  defaultBillingCategory,
  formatTehranDateForLocale,
  getBodyAnalysisQuotaEstimate,
  groupBillingOffers,
  isBillingPackageCode,
  packagesForBillingCategory,
  type BillingCategory,
  type BillingPackageCode,
  type EntitlementSnapshot,
} from "@fitician/core";
import type { BillingOffer } from "@fitician/core/billing";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { AppIcon, type IconName } from "../../shared/AppIcon";
import { useEntitlements } from "../entitlements/EntitlementContext";
import { getOffers } from "./api";
import "./billing.css";

const packageTranslationKeys: Record<BillingPackageCode, string> = {
  training: "training", training_coach: "trainingCoach", nutrition: "nutrition",
  nutrition_physician: "nutritionPhysician", complete: "complete", complete_care: "completeCare",
};

const packageIcons: Record<BillingPackageCode, IconName> = {
  training: "dumbbell", training_coach: "award", nutrition: "nutrition",
  nutrition_physician: "heart", complete: "sparkles", complete_care: "shield",
};

export function PlansPage() {
  const { i18n, t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { snapshot } = useEntitlements();
  const [offers, setOffers] = useState<BillingOffer[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [requiredEntitlement] = useState(() => searchParams.get("required"));
  const [category, setCategory] = useState<BillingCategory>(() => defaultBillingCategory(snapshot?.primary_package));
  const [selectedDurations, setSelectedDurations] = useState<Partial<Record<BillingPackageCode, BillingOffer["duration_weeks"]>>>({});
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => { setCategory(defaultBillingCategory(snapshot?.primary_package)); }, [snapshot?.primary_package]);

  useEffect(() => {
    let active = true;
    setState("loading");
    void getOffers().then((result) => {
      if (!active) return;
      setOffers(result);
      setLoadError(null);
      setState("ready");
    }).catch((cause: unknown) => {
      if (!active) return;
      setLoadError(cause);
      setState("error");
    });
    return () => { active = false; };
  }, []);

  const groupedOffers = useMemo(() => groupBillingOffers(offers), [offers]);
  const visiblePackages = packagesForBillingCategory[category].filter((code) => groupedOffers.has(code));

  return (
    <main className="billing-page fitician-page">
      <div className="billing-page__container billing-pricing">
        <header className="billing-hero billing-pricing__hero">
          <p className="eyebrow eyebrow--accent">{t("billing.plans")}</p>
          <h1>{t("billing.choosePlan")}</h1>
          <p>{t("billing.pricingSubtitle")}</p>
        </header>

        {snapshot && <CurrentPackageCard english={english} snapshot={snapshot} />}

        <div className="billing-category-selector" role="tablist" aria-label={t("billing.plans")}>
          {billingCategories.map((item) => (
            <button aria-selected={category === item} className={category === item ? "is-active" : ""} key={item} onClick={() => setCategory(item)} role="tab" type="button">
              {t(`billing.categories.${item}`)}
            </button>
          ))}
        </div>

        {state === "loading" && <p className="billing-status" role="status">{t("billing.loading")}</p>}
        {state === "error" && <AppErrorNotice audience="member" context="billing" error={loadError} locale={english ? "en" : "fa"} onRetry={() => window.location.reload()} />}
        {state === "ready" && offers.length === 0 && <p className="billing-status">{t("billing.noOffers")}</p>}
        {state === "ready" && visiblePackages.length > 0 && (
          <div className="billing-package-grid">
            {visiblePackages.map((packageCode) => {
              const packageOffers = groupedOffers.get(packageCode) ?? [];
              const duration = selectedDurations[packageCode] ?? packageOffers[0]?.duration_weeks;
              const selectedOffer = packageOffers.find((item) => item.duration_weeks === duration) ?? packageOffers[0];
              if (!selectedOffer) return null;
              return (
                <PackageCard
                  active={snapshot?.primary_package === packageCode}
                  eligible={requiredEntitlement !== null && packageOffers.some((item) => item.entitlements.includes(requiredEntitlement as BillingOffer["entitlements"][number]))}
                  english={english}
                  key={packageCode}
                  offers={packageOffers}
                  onBuy={(item) => navigate(`/billing/checkout/${item.offer_code}`, { state: { offer: item } })}
                  onSelectDuration={(nextDuration) => setSelectedDurations((current) => ({ ...current, [packageCode]: nextDuration }))}
                  packageCode={packageCode}
                  selectedOffer={selectedOffer}
                />
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}

type PackageCardProps = {
  readonly active: boolean;
  readonly eligible: boolean;
  readonly english: boolean;
  readonly offers: readonly BillingOffer[];
  readonly onBuy: (offer: BillingOffer) => void;
  readonly onSelectDuration: (duration: BillingOffer["duration_weeks"]) => void;
  readonly packageCode: BillingPackageCode;
  readonly selectedOffer: BillingOffer;
};

function PackageCard({ active, eligible, english, offers, onBuy, onSelectDuration, packageCode, selectedOffer }: PackageCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const key = `billing.packageDetails.${packageTranslationKeys[packageCode]}`;
  const name = t(`${key}.name`);
  const features = t(`${key}.features`, { returnObjects: true }) as unknown as string[];
  const badge = t(`${key}.badge`);
  const quota = getBodyAnalysisQuotaEstimate(selectedOffer);
  const duration = durationLabel(selectedOffer.duration_weeks, t);
  const classes = ["billing-package-card", active && "billing-package-card--active", eligible && "billing-package-card--eligible", packageCode === "complete" && "billing-package-card--featured", packageCode === "complete_care" && "billing-package-card--premium"].filter(Boolean).join(" ");

  return (
    <article className={classes} data-testid={`billing-package-${packageCode}`}>
      <div className="billing-package-card__topline">
        <span className="billing-package-card__icon"><AppIcon name={packageIcons[packageCode]} /></span>
        <div className="billing-package-card__badges">
          {active && <span className="billing-badge billing-badge--active">{t("billing.activeBadge")}</span>}
          {badge && <span className="billing-badge">{badge}</span>}
        </div>
      </div>
      <header className="billing-package-card__header"><h2>{name}</h2><p>{t(`${key}.subtitle`)}</p></header>
      <p className="billing-package-card__tagline">{t(`${key}.tagline`)}</p>
      <ul className="billing-feature-list">
        {(expanded ? features : features.slice(0, 4)).map((feature) => (
          <li className="billing-feature-row" key={feature}><span aria-hidden="true" className="billing-feature-row__check" /><span>{feature}</span></li>
        ))}
      </ul>
      {features.length > 4 && (
        <button aria-expanded={expanded} className="billing-feature-toggle" onClick={() => setExpanded((value) => !value)} type="button">
          {t(expanded ? "billing.showFewerFeatures" : "billing.showAllFeatures")}<span aria-hidden="true" className={expanded ? "billing-feature-toggle__chevron is-open" : "billing-feature-toggle__chevron"} />
        </button>
      )}

      <div className="billing-package-card__purchase">
        <div className="billing-duration-block">
          <span>{t("billing.chooseDuration")}</span>
          <div className="billing-duration-selector" role="radiogroup" aria-label={`${t("billing.chooseDuration")} — ${name}`}>
            {offers.map((offer) => {
              const label = durationLabel(offer.duration_weeks, t);
              const selected = offer.offer_code === selectedOffer.offer_code;
              return <button aria-checked={selected} aria-label={label} className={selected ? "is-selected" : ""} key={offer.offer_code} onClick={() => onSelectDuration(offer.duration_weeks)} role="radio" type="button">{label}</button>;
            })}
          </div>
        </div>
        {quota && (
          <p className="billing-quota-highlight"><AppIcon name="body" /><span>{t(quota.windowDays === 7 ? "billing.bodyAnalysisWeeklyQuota" : "billing.bodyAnalysisQuota", { limit: formatNumeric(quota.limit, english), total: formatNumeric(quota.estimatedTotal, english), windowDays: formatNumeric(quota.windowDays, english) })}</span></p>
        )}
        <div className="billing-package-card__price-row">
          <p className="billing-package-card__price">{selectedOffer.price_irr === null || selectedOffer.currency === null ? t("billing.offerUnavailable") : formatAmount(selectedOffer.price_irr, selectedOffer.currency, english)}</p>
          {!selectedOffer.is_available && <span className="billing-package-card__unavailable">{t("billing.offerUnavailable")}</span>}
        </div>
        <button aria-label={t("billing.buySelectedPackage", { duration, package: name })} className="billing-button billing-button--primary billing-package-card__cta" disabled={!selectedOffer.is_available} onClick={() => onBuy(selectedOffer)} type="button">{t("billing.buy")}</button>
      </div>
    </article>
  );
}

function CurrentPackageCard({ snapshot, english }: { readonly snapshot: EntitlementSnapshot; readonly english: boolean }) {
  const { t } = useTranslation();
  const now = Date.now();
  const matchingExpiry = snapshot.grants.filter((grant) => {
    const startsAt = Date.parse(grant.starts_at);
    const endsAt = grant.ends_at === null ? null : Date.parse(grant.ends_at);
    return grant.package_code === snapshot.primary_package && grant.revoked_at === null
      && startsAt <= now && (endsAt === null || endsAt > now);
  }).map((grant) => grant.ends_at).filter((value): value is string => value !== null).sort().at(-1);
  const expiry = snapshot.trial.active ? snapshot.trial.ends_at : matchingExpiry;
  const packageName = isBillingPackageCode(snapshot.primary_package)
    ? t(`billing.packageDetails.${packageTranslationKeys[snapshot.primary_package]}.name`)
    : t(`entitlements.packageLabels.${snapshot.primary_package}`, { defaultValue: snapshot.primary_package });
  return (
    <section className="billing-current-card" aria-label={t("billing.currentPlan")}>
      <span className="billing-current-card__mark"><AppIcon name="wallet" /></span>
      <div className="billing-current-card__copy"><span>{t("billing.currentPlan")}</span><strong>{packageName}</strong></div>
      <div className="billing-current-card__status">
        <div><span className="billing-badge billing-badge--active">{t("billing.activeBadge")}</span>{snapshot.trial.active && <span className="billing-badge billing-badge--trial">{t("billing.trialBadge")}</span>}</div>
        {expiry && <time dateTime={expiry}>{t(snapshot.trial.active ? "billing.trialExpiration" : "billing.accessEnds", { date: formatDate(expiry, english) })}</time>}
      </div>
    </section>
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

function formatNumeric(value: number, english: boolean) {
  return new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(value);
}

function formatDate(value: string, english: boolean) {
  return formatTehranDateForLocale(value, english ? "en" : "fa-IR");
}
