import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatTehranDateTimeForLocale } from "@fitician/core/iran-calendar";

import { PersianDateTimePicker } from "../../shared/PersianDateTimePicker";
import { ApiError } from "../../shared/apiClient";
import { AppErrorNotice } from "../../shared/AppErrorNotice";

import {
  activateCampaign,
  adminAccessPackageCodes,
  createCampaign,
  deactivateCampaign,
  getCampaigns,
  type AccessCampaignKind,
  type AccessTermWeeks,
  type AdminAccessCampaign,
  type AdminAccessCampaignInput,
  type AdminAccessCampaignUpdate,
  updateCampaign,
} from "./adminAccessApi";

type CampaignFormState = {
  code: string;
  name: string;
  description: string;
  kind: AccessCampaignKind;
  package_code: AdminAccessCampaign["package_code"];
  duration_days: string;
  term_weeks: string;
  available_from: string | null;
  available_until: string | null;
  is_active: boolean;
  max_total_redemptions: string;
  public_badge_fa: string;
  public_badge_en: string;
  public_title_fa: string;
  public_title_en: string;
  public_message_fa: string;
  public_message_en: string;
  public_cta_fa: string;
  public_cta_en: string;
  show_on_landing: boolean;
  show_on_register: boolean;
};

type CampaignFormField =
  | "code"
  | "name"
  | "duration_days"
  | "term_weeks"
  | "max_total_redemptions"
  | "availability"
  | "marketing";

type CampaignFormErrorCode =
  | "codeRequired"
  | "codeFormat"
  | "nameRequired"
  | "durationRequired"
  | "durationRange"
  | "durationTermMinimum"
  | "maxRedemptionsPositive"
  | "trainingTermRequired"
  | "termInvalid"
  | "availabilityOrder"
  | "publicCopyRequired";

type CampaignFormErrors = Partial<Record<CampaignFormField, CampaignFormErrorCode>>;

const campaignCodePattern = /^[a-z0-9][a-z0-9_.-]*$/;
const validTermValues = new Set(["4", "6", "8"]);
const trainingTermPackageCodes = new Set<AdminAccessCampaign["package_code"]>([
  "training",
  "training_coach",
  "complete",
  "complete_care",
]);
const humanReviewPackageCodes = new Set<AdminAccessCampaign["package_code"]>([
  "training_coach",
  "nutrition_physician",
  "complete_care",
]);

const initialForm: CampaignFormState = {
  code: "",
  name: "",
  description: "",
  kind: "manual_promotion",
  package_code: "complete",
  duration_days: "56",
  term_weeks: "8",
  available_from: null,
  available_until: null,
  is_active: false,
  max_total_redemptions: "",
  public_badge_fa: "",
  public_badge_en: "",
  public_title_fa: "",
  public_title_en: "",
  public_message_fa: "",
  public_message_en: "",
  public_cta_fa: "",
  public_cta_en: "",
  show_on_landing: false,
  show_on_register: false,
};

export function AdminAccessCampaignsPage() {
  const { i18n, t } = useTranslation();
  const [campaigns, setCampaigns] = useState<AdminAccessCampaign[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [editing, setEditing] = useState<AdminAccessCampaign | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CampaignFormState>(initialForm);
  const [saving, setSaving] = useState(false);
  const [working, setWorking] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<CampaignFormErrors>({});
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [actionError, setActionError] = useState<unknown | null>(null);

  useEffect(() => {
    let active = true;
    void getCampaigns()
      .then((result) => {
        if (!active) return;
        setCampaigns(result);
        setLoadError(null);
        setState("ready");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setLoadError(cause);
        setState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  const editingSemanticsLocked = editing !== null && editing.redemption_count > 0;
  const english = i18n.resolvedLanguage === "en";
  const availablePackages = useMemo(() => {
    if (adminAccessPackageCodes.some((code) => code === form.package_code)) return adminAccessPackageCodes;
    return [form.package_code, ...adminAccessPackageCodes];
  }, [form.package_code]);
  const publicCampaign = form.kind === "signup_bonus";

  function openCreate() {
    setEditing(null);
    setForm(initialForm);
    setFormErrors({});
    setActionError(null);
    setShowForm(true);
  }

  function openEdit(campaign: AdminAccessCampaign) {
    setEditing(campaign);
    setForm({
      code: campaign.code,
      name: campaign.name,
      description: campaign.description ?? "",
      kind: campaign.kind,
      package_code: campaign.package_code,
      duration_days: String(campaign.duration_days),
      term_weeks: campaign.term_weeks === null ? "" : String(campaign.term_weeks),
      available_from: campaign.available_from,
      available_until: campaign.available_until,
      is_active: campaign.is_active,
      max_total_redemptions: campaign.max_total_redemptions === null
        ? ""
        : String(campaign.max_total_redemptions),
      public_badge_fa: campaign.public_badge_fa ?? "",
      public_badge_en: campaign.public_badge_en ?? "",
      public_title_fa: campaign.public_title_fa ?? "",
      public_title_en: campaign.public_title_en ?? "",
      public_message_fa: campaign.public_message_fa ?? "",
      public_message_en: campaign.public_message_en ?? "",
      public_cta_fa: campaign.public_cta_fa ?? "",
      public_cta_en: campaign.public_cta_en ?? "",
      show_on_landing: campaign.show_on_landing,
      show_on_register: campaign.show_on_register,
    });
    setFormErrors({});
    setActionError(null);
    setShowForm(true);
  }

  async function save() {
    const nextErrors = validateCampaignForm(form);
    setFormErrors(nextErrors);
    setActionError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      if (editing === null) {
        const created = await createCampaign(toCreateInput(form));
        setCampaigns((current) => [created, ...current]);
      } else {
        const updated = await updateCampaign(editing.id, toUpdateInput(form, editing));
        setCampaigns((current) => current.map((item) => item.id === updated.id ? updated : item));
      }
      setShowForm(false);
    } catch (error) {
      setFormErrors(apiCampaignFormErrors(error));
      setActionError(error);
    } finally {
      setSaving(false);
    }
  }

  async function toggle(campaign: AdminAccessCampaign) {
    setActionError(null);
    setWorking(campaign.id);
    try {
      const result = campaign.is_active
        ? await deactivateCampaign(campaign.id)
        : await activateCampaign(campaign.id);
      setCampaigns((current) => current.map((item) => item.id === result.id ? result : item));
    } catch (error) {
      setActionError(error);
    } finally {
      setWorking(null);
    }
  }

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.campaign")}</p>
            <h1>{t("adminAccess.campaignsTrials")}</h1>
            <p>{t("adminAccess.campaignsDescription")}</p>
          </div>
          <button className="access-admin-button access-admin-button--primary access-admin-button--create" onClick={openCreate} type="button">
            <span aria-hidden="true" className="access-admin-button__icon">+</span>
            {t("adminAccess.createCampaign")}
          </button>
        </header>

        {state === "loading" && <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>}
        {state === "error" && <AppErrorNotice audience="admin" context="access" error={loadError} locale={english ? "en" : "fa"} onRetry={() => window.location.reload()} />}
        {actionError !== null && <AppErrorNotice audience="admin" context="access" error={actionError} locale={english ? "en" : "fa"} />}

        {state === "ready" && campaigns.length === 0 && <p className="access-admin-status">{t("adminAccess.noCampaigns")}</p>}
        {state === "ready" && campaigns.length > 0 && (
          <div className="access-campaign-list">
            {campaigns.map((campaign) => (
              <article className="access-campaign-card" data-testid={`access-campaign-${campaign.code}`} key={campaign.id}>
                <header>
                  <div>
                    <span className="access-admin-code">{campaign.code}</span>
                    <h2>{campaign.name}</h2>
                    <p>{campaign.kind === "signup_bonus" ? t("adminAccess.signupBonus") : t("adminAccess.manualPromotion")}</p>
                  </div>
                  <span className={`access-admin-state ${campaign.is_active ? "is-active" : "is-inactive"}`}>
                    {campaign.is_active ? t("adminAccess.active") : t("adminAccess.inactive")}
                  </span>
                </header>
                <p className="access-campaign-card__help">
                  {campaign.kind === "signup_bonus" ? t("adminAccess.signupHelp") : t("adminAccess.manualHelp")}
                </p>
                <dl className="access-campaign-card__facts">
                  <div><dt>{t("adminAccess.package")}</dt><dd>{t(`entitlements.packageLabels.${campaign.package_code}`, { defaultValue: campaign.package_code })}</dd></div>
                  <div><dt>{t("adminAccess.benefitDuration")}</dt><dd>{campaign.duration_days}</dd></div>
                  <div><dt>{t("adminAccess.trainingTerm")}</dt><dd>{campaign.term_weeks === null ? "—" : `${campaign.term_weeks} ${t("adminAccess.weeks")}`}</dd></div>
                  <div><dt>{t("adminAccess.campaignStart")}</dt><dd>{campaign.available_from === null ? "—" : formatDate(campaign.available_from, english)}</dd></div>
                  <div><dt>{t("adminAccess.campaignEnd")}</dt><dd>{campaign.available_until === null ? "—" : formatDate(campaign.available_until, english)}</dd></div>
                  <div><dt>{t("adminAccess.redemptions")}</dt><dd>{campaign.redemption_count}{campaign.max_total_redemptions === null ? "" : ` / ${campaign.max_total_redemptions}`}</dd></div>
                </dl>
                {campaign.redemption_count > 0 && <p className="access-campaign-card__warning">{t("adminAccess.immutableAfterRedemption")}</p>}
                <footer>
                  <button className="access-admin-button access-admin-button--quiet" onClick={() => openEdit(campaign)} type="button">
                    {t("adminAccess.editCampaign")}
                  </button>
                  <button
                    className="access-admin-button access-admin-button--quiet"
                    disabled={working === campaign.id}
                    onClick={() => void toggle(campaign)}
                    type="button"
                  >
                    {campaign.is_active ? t("adminAccess.deactivate") : t("adminAccess.activate")}
                  </button>
                </footer>
              </article>
            ))}
          </div>
        )}

        {showForm && (
          <section aria-label={editing === null ? t("adminAccess.createCampaign") : t("adminAccess.editCampaign")} className="access-admin-form-card">
            <header>
              <div>
                <p className="eyebrow eyebrow--accent">{t("adminAccess.campaign")}</p>
                <h2>{editing === null ? t("adminAccess.createCampaign") : t("adminAccess.editCampaign")}</h2>
              </div>
              <button className="access-admin-button access-admin-button--quiet" onClick={() => setShowForm(false)} type="button">{t("adminAccess.cancel")}</button>
            </header>

            <div className="access-campaign-form-section">
              <h3>{t("adminAccess.sections.identity")}</h3>
              <div className="access-admin-form-grid">
                <label>
                  {t("adminAccess.code")}
                  <input
                    aria-describedby={hasFieldError("code") ? fieldErrorId("code") : undefined}
                    aria-invalid={hasFieldError("code")}
                    disabled={editing !== null}
                    onChange={(event) => setField("code", event.currentTarget.value)}
                    value={form.code}
                  />
                  {renderFieldError("code")}
                </label>
                <label>
                  {t("adminAccess.campaignName")}
                  <input
                    aria-describedby={hasFieldError("name") ? fieldErrorId("name") : undefined}
                    aria-invalid={hasFieldError("name")}
                    onChange={(event) => setField("name", event.currentTarget.value)}
                    value={form.name}
                  />
                  {renderFieldError("name")}
                </label>
                <label className="access-admin-form-card__description">
                  {t("adminAccess.description")}
                  <textarea onChange={(event) => setField("description", event.currentTarget.value)} value={form.description} />
                </label>
              </div>
            </div>

            <div className="access-campaign-form-section">
              <h3>{t("adminAccess.sections.type")}</h3>
              <div className="access-admin-form-grid">
                <label>
                  {t("adminAccess.kind")}
                  <select disabled={editingSemanticsLocked} onChange={(event) => setCampaignKind(event.currentTarget.value as AccessCampaignKind)} value={form.kind}>
                    <option value="signup_bonus">{t("adminAccess.signupBonus")}</option>
                    <option value="manual_promotion">{t("adminAccess.manualPromotion")}</option>
                  </select>
                </label>
              </div>
            </div>

            <div className="access-campaign-form-section">
              <h3>{t("adminAccess.sections.benefit")}</h3>
              <div className="access-admin-form-grid">
                <label>
                  {t("adminAccess.package")}
                  <select disabled={editingSemanticsLocked} onChange={(event) => setField("package_code", event.currentTarget.value as CampaignFormState["package_code"])} value={form.package_code}>
                    {availablePackages.map((packageCode) => <option key={packageCode} value={packageCode}>{t(`entitlements.packageLabels.${packageCode}`, { defaultValue: packageCode })}</option>)}
                  </select>
                </label>
                <label>
                  {t("adminAccess.benefitDuration")}
                  <input
                    aria-describedby={hasFieldError("duration_days") ? fieldErrorId("duration_days") : undefined}
                    aria-invalid={hasFieldError("duration_days")}
                    disabled={editingSemanticsLocked}
                    min="1"
                    onChange={(event) => setField("duration_days", event.currentTarget.value)}
                    type="number"
                    value={form.duration_days}
                  />
                  {renderFieldError("duration_days")}
                </label>
                <label>
                  {t("adminAccess.trainingTerm")}
                  <select
                    aria-describedby={hasFieldError("term_weeks") ? fieldErrorId("term_weeks") : undefined}
                    aria-invalid={hasFieldError("term_weeks")}
                    disabled={editingSemanticsLocked}
                    onChange={(event) => setField("term_weeks", event.currentTarget.value)}
                    value={form.term_weeks}
                  >
                    <option value="">—</option>
                    <option value="4">{t("billing.fourWeeks")}</option>
                    <option value="6">{t("billing.sixWeeks")}</option>
                    <option value="8">{t("billing.eightWeeks")}</option>
                  </select>
                  {renderFieldError("term_weeks")}
                </label>
              </div>
              {humanReviewPackageCodes.has(form.package_code) && <p className="access-campaign-human-warning">{t("adminAccess.humanReviewWarning")}</p>}
            </div>

            <div className="access-campaign-form-section">
              <h3>{t("adminAccess.sections.eligibility")}</h3>
              <div className="access-admin-form-grid">
                <div>
                  <PersianDateTimePicker
                    ariaLabel={t("adminAccess.campaignStart")}
                    label={t("adminAccess.campaignStart")}
                    onChange={(value) => setField("available_from", value)}
                    value={form.available_from}
                  />
                </div>
                <div>
                  <PersianDateTimePicker
                    ariaLabel={t("adminAccess.campaignEnd")}
                    label={t("adminAccess.campaignEnd")}
                    onChange={(value) => setField("available_until", value)}
                    value={form.available_until}
                  />
                </div>
                <label>
                  {t("adminAccess.maximumRedemptions")}
                  <input
                    aria-describedby={hasFieldError("max_total_redemptions") ? fieldErrorId("max_total_redemptions") : undefined}
                    aria-invalid={hasFieldError("max_total_redemptions")}
                    min="1"
                    onChange={(event) => setField("max_total_redemptions", event.currentTarget.value)}
                    type="number"
                    value={form.max_total_redemptions}
                  />
                  {renderFieldError("max_total_redemptions")}
                </label>
                {editing === null && (
                  <label className="access-admin-checkbox">
                    <input checked={form.is_active} onChange={(event) => setField("is_active", event.currentTarget.checked)} type="checkbox" />
                    {t("adminAccess.active")}
                  </label>
                )}
              </div>
              {renderFieldError("availability")}
            </div>

            {publicCampaign ? (
              <div className="access-campaign-form-section">
                <h3>{t("adminAccess.sections.publicAdvertising")}</h3>
                <div className="access-campaign-visibility-controls">
                  <label className="access-admin-checkbox">
                    <input checked={form.show_on_landing} onChange={(event) => setField("show_on_landing", event.currentTarget.checked)} type="checkbox" />
                    {t("adminAccess.showOnLanding")}
                  </label>
                  <label className="access-admin-checkbox">
                    <input checked={form.show_on_register} onChange={(event) => setField("show_on_register", event.currentTarget.checked)} type="checkbox" />
                    {t("adminAccess.showOnRegister")}
                  </label>
                </div>
                <div className="access-campaign-marketing-grid">
                  <label>
                    {t("adminAccess.badgeFa")}
                    <input onChange={(event) => setField("public_badge_fa", event.currentTarget.value)} value={form.public_badge_fa} />
                  </label>
                  <label>
                    {t("adminAccess.badgeEn")}
                    <input dir="ltr" onChange={(event) => setField("public_badge_en", event.currentTarget.value)} value={form.public_badge_en} />
                  </label>
                  <label>
                    {t("adminAccess.titleFa")}
                    <input onChange={(event) => setField("public_title_fa", event.currentTarget.value)} value={form.public_title_fa} />
                  </label>
                  <label>
                    {t("adminAccess.titleEn")}
                    <input dir="ltr" onChange={(event) => setField("public_title_en", event.currentTarget.value)} value={form.public_title_en} />
                  </label>
                  <label>
                    {t("adminAccess.messageFa")}
                    <textarea onChange={(event) => setField("public_message_fa", event.currentTarget.value)} value={form.public_message_fa} />
                  </label>
                  <label>
                    {t("adminAccess.messageEn")}
                    <textarea dir="ltr" onChange={(event) => setField("public_message_en", event.currentTarget.value)} value={form.public_message_en} />
                  </label>
                  <label>
                    {t("adminAccess.ctaFa")}
                    <input onChange={(event) => setField("public_cta_fa", event.currentTarget.value)} value={form.public_cta_fa} />
                  </label>
                  <label>
                    {t("adminAccess.ctaEn")}
                    <input dir="ltr" onChange={(event) => setField("public_cta_en", event.currentTarget.value)} value={form.public_cta_en} />
                  </label>
                </div>
                {renderFieldError("marketing")}
              </div>
            ) : (
              <p className="access-campaign-private-note">{t("adminAccess.manualPrivateNote")}</p>
            )}

            {publicCampaign && (
              <div className="access-campaign-form-section">
                <h3>{t("adminAccess.sections.preview")}</h3>
                <div className="access-campaign-preview-grid">
                  <CampaignPreview direction="rtl" badge={form.public_badge_fa} title={form.public_title_fa} message={form.public_message_fa} cta={form.public_cta_fa} language={t("adminAccess.previewFa")} benefit={benefitLabel(form, t)} />
                  <CampaignPreview direction="ltr" badge={form.public_badge_en} title={form.public_title_en} message={form.public_message_en} cta={form.public_cta_en} language={t("adminAccess.previewEn")} benefit={benefitLabel(form, t)} />
                </div>
              </div>
            )}

            <p className="access-campaign-card__help">
              {publicCampaign ? t("adminAccess.signupHelp") : t("adminAccess.manualHelp")}
            </p>
            <button className="access-admin-button access-admin-button--primary" disabled={saving} onClick={() => void save()} type="button">
              {saving ? t("billing.saving") : t("adminAccess.saveChanges")}
            </button>
          </section>
        )}
      </div>
    </main>
  );

  function setField<K extends keyof CampaignFormState>(key: K, value: CampaignFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    const errorField: CampaignFormField = key === "available_from" || key === "available_until"
      ? "availability"
      : key === "public_badge_fa" || key === "public_badge_en" || key === "public_title_fa"
        || key === "public_title_en" || key === "public_message_fa" || key === "public_message_en"
        || key === "public_cta_fa" || key === "public_cta_en" || key === "show_on_landing"
        || key === "show_on_register"
        ? "marketing"
        : key as CampaignFormField;
    setFormErrors((current) => {
      if (!(errorField in current)) return current;
      const next = { ...current };
      delete next[errorField];
      return next;
    });
    setActionError(null);
  }

  function setCampaignKind(kind: AccessCampaignKind) {
    setForm((current) => ({
      ...current,
      kind,
      show_on_landing: kind === "signup_bonus" ? current.show_on_landing : false,
      show_on_register: kind === "signup_bonus" ? current.show_on_register : false,
    }));
    setFormErrors({});
    setActionError(null);
  }

  function hasFieldError(field: CampaignFormField): boolean {
    return formErrors[field] !== undefined;
  }

  function fieldErrorId(field: CampaignFormField): string {
    return `access-campaign-${field}-error`;
  }

  function renderFieldError(field: CampaignFormField) {
    const errorCode = formErrors[field];
    if (errorCode === undefined) return null;
    return (
      <span className="access-admin-field-error" id={fieldErrorId(field)}>
        {t(`adminAccess.validation.${errorCode}`)}
      </span>
    );
  }
}

function CampaignPreview({
  direction,
  badge,
  title,
  message,
  cta,
  language,
  benefit,
}: {
  direction: "rtl" | "ltr";
  badge: string;
  title: string;
  message: string;
  cta: string;
  language: string;
  benefit: string;
}) {
  return (
    <article className="access-campaign-preview" data-testid={`campaign-preview-${direction}`} dir={direction}>
      <span className="access-campaign-preview__language">{language}</span>
      {badge.trim() !== "" && <span className="access-campaign-preview__badge">{badge}</span>}
      <h4>{title || "—"}</h4>
      <p>{message || "—"}</p>
      <small>{benefit}</small>
      {cta.trim() !== "" && <span className="access-campaign-preview__cta">{cta}</span>}
    </article>
  );
}

function toCreateInput(form: CampaignFormState): AdminAccessCampaignInput {
  return {
    code: form.code.trim(),
    name: form.name.trim(),
    description: optionalText(form.description),
    kind: form.kind,
    package_code: form.package_code,
    duration_days: Number(form.duration_days),
    term_weeks: toTermWeeks(form.term_weeks),
    available_from: form.available_from,
    available_until: form.available_until,
    is_active: form.is_active,
    max_total_redemptions: form.max_total_redemptions === "" ? null : Number(form.max_total_redemptions),
    public_badge_fa: optionalText(form.public_badge_fa),
    public_badge_en: optionalText(form.public_badge_en),
    public_title_fa: optionalText(form.public_title_fa),
    public_title_en: optionalText(form.public_title_en),
    public_message_fa: optionalText(form.public_message_fa),
    public_message_en: optionalText(form.public_message_en),
    public_cta_fa: optionalText(form.public_cta_fa),
    public_cta_en: optionalText(form.public_cta_en),
    show_on_landing: form.kind === "signup_bonus" && form.show_on_landing,
    show_on_register: form.kind === "signup_bonus" && form.show_on_register,
  };
}

function toUpdateInput(form: CampaignFormState, previous: AdminAccessCampaign): AdminAccessCampaignUpdate {
  const input: AdminAccessCampaignUpdate = {
    name: form.name.trim(),
    description: optionalText(form.description),
    available_from: form.available_from,
    available_until: form.available_until,
    max_total_redemptions: form.max_total_redemptions === "" ? null : Number(form.max_total_redemptions),
    public_badge_fa: optionalText(form.public_badge_fa),
    public_badge_en: optionalText(form.public_badge_en),
    public_title_fa: optionalText(form.public_title_fa),
    public_title_en: optionalText(form.public_title_en),
    public_message_fa: optionalText(form.public_message_fa),
    public_message_en: optionalText(form.public_message_en),
    public_cta_fa: optionalText(form.public_cta_fa),
    public_cta_en: optionalText(form.public_cta_en),
    show_on_landing: form.kind === "signup_bonus" && form.show_on_landing,
    show_on_register: form.kind === "signup_bonus" && form.show_on_register,
  };
  if (previous.redemption_count === 0) {
    return {
      ...input,
      kind: form.kind,
      package_code: form.package_code,
      duration_days: Number(form.duration_days),
      term_weeks: toTermWeeks(form.term_weeks),
    };
  }
  return input;
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized === "" ? null : normalized;
}

function toTermWeeks(value: string): AccessTermWeeks | null {
  if (value === "4" || value === "6" || value === "8") return Number(value) as AccessTermWeeks;
  return null;
}

function formatDate(value: string, english: boolean): string {
  return formatTehranDateTimeForLocale(value, english ? "en" : "fa-IR");
}

function benefitLabel(form: CampaignFormState, t: (key: string, options?: Record<string, unknown>) => string): string {
  const term = toTermWeeks(form.term_weeks);
  return term === null
    ? `${form.duration_days} ${t("adminAccess.days")}`
    : `${term} ${t("adminAccess.weeks")} · ${form.duration_days} ${t("adminAccess.days")}`;
}

function validateCampaignForm(form: CampaignFormState): CampaignFormErrors {
  const errors: CampaignFormErrors = {};
  const code = form.code.trim();
  const name = form.name.trim();
  const duration = Number(form.duration_days);
  const maxRedemptions = form.max_total_redemptions === ""
    ? null
    : Number(form.max_total_redemptions);
  const term = toTermWeeks(form.term_weeks);

  if (code === "") errors.code = "codeRequired";
  else if (!campaignCodePattern.test(code)) errors.code = "codeFormat";
  if (name === "") errors.name = "nameRequired";
  if (form.duration_days.trim() === "" || !Number.isInteger(duration)) {
    errors.duration_days = "durationRequired";
  } else if (duration < 1 || duration > 3650) {
    errors.duration_days = "durationRange";
  }
  if (
    maxRedemptions !== null
    && (!Number.isInteger(maxRedemptions) || maxRedemptions < 1)
  ) {
    errors.max_total_redemptions = "maxRedemptionsPositive";
  }
  if (trainingTermPackageCodes.has(form.package_code) && term === null) {
    errors.term_weeks = "trainingTermRequired";
  } else if (trainingTermPackageCodes.has(form.package_code) && term !== null && Number.isInteger(duration) && duration < term * 7) {
    errors.duration_days = "durationTermMinimum";
  } else if (form.term_weeks !== "" && !validTermValues.has(form.term_weeks)) {
    errors.term_weeks = "termInvalid";
  }
  if (
    form.available_from !== null
    && form.available_until !== null
    && new Date(form.available_until).getTime() < new Date(form.available_from).getTime()
  ) {
    errors.availability = "availabilityOrder";
  }
  if (
    form.kind === "signup_bonus"
    && (form.show_on_landing || form.show_on_register)
    && [
      form.public_title_fa,
      form.public_title_en,
      form.public_message_fa,
      form.public_message_en,
      form.public_cta_fa,
      form.public_cta_en,
    ].some((value) => value.trim() === "")
  ) {
    errors.marketing = "publicCopyRequired";
  }
  return errors;
}

function apiCampaignFormErrors(error: unknown): CampaignFormErrors {
  if (!(error instanceof ApiError) || error.details === null) return {};
  const errors: CampaignFormErrors = {};
  for (const detail of error.details) {
    const field = detail.loc?.at(-1);
    if (field === "code") errors.code = "codeFormat";
    else if (field === "name") errors.name = "nameRequired";
    else if (field === "duration_days") errors.duration_days = "durationRange";
    else if (field === "term_weeks") errors.term_weeks = "termInvalid";
    else if (field === "max_total_redemptions") errors.max_total_redemptions = "maxRedemptionsPositive";
    else if (field === "available_until" || field === "available_from") errors.availability = "availabilityOrder";
    else if (typeof field === "string" && (field.startsWith("public_") || field.startsWith("show_on_"))) errors.marketing = "publicCopyRequired";
  }
  return errors;
}
