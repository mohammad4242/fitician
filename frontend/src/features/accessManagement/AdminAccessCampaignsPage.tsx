import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatTehranDateTime } from "@fitician/core/iran-calendar";

import { PersianDateTimePicker } from "../../shared/PersianDateTimePicker";

import {
  activateCampaign,
  adminAccessPackageCodes,
  signupTrialPackageCodes,
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
};

const initialForm: CampaignFormState = {
  code: "",
  name: "",
  description: "",
  kind: "manual_promotion",
  package_code: "complete",
  duration_days: "30",
  term_weeks: "8",
  available_from: null,
  available_until: null,
  is_active: false,
  max_total_redemptions: "",
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

  useEffect(() => {
    let active = true;
    void getCampaigns()
      .then((result) => {
        if (!active) return;
        setCampaigns(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, []);

  const editingSemanticsLocked = editing !== null && editing.redemption_count > 0;
  const availablePackages = useMemo(
    () => form.kind === "signup_trial" ? signupTrialPackageCodes : adminAccessPackageCodes,
    [form.kind],
  );
  const english = i18n.resolvedLanguage === "en";

  function openCreate() {
    setEditing(null);
    setForm(initialForm);
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
    });
    setShowForm(true);
  }

  async function save() {
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
    } catch {
      setState("error");
    } finally {
      setSaving(false);
    }
  }

  async function toggle(campaign: AdminAccessCampaign) {
    setWorking(campaign.id);
    try {
      const result = campaign.is_active
        ? await deactivateCampaign(campaign.id)
        : await activateCampaign(campaign.id);
      setCampaigns((current) => current.map((item) => item.id === result.id ? result : item));
    } catch {
      setState("error");
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
        {state === "error" && <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.loadError")}</p>}

        {state === "ready" && campaigns.length === 0 && <p className="access-admin-status">{t("adminAccess.noCampaigns")}</p>}
        {state === "ready" && campaigns.length > 0 && (
          <div className="access-campaign-list">
            {campaigns.map((campaign) => (
              <article className="access-campaign-card" data-testid={`access-campaign-${campaign.code}`} key={campaign.id}>
                <header>
                  <div>
                    <span className="access-admin-code">{campaign.code}</span>
                    <h2>{campaign.name}</h2>
                    <p>{campaign.kind === "signup_trial" ? t("adminAccess.signupTrial") : t("adminAccess.manualPromotion")}</p>
                  </div>
                  <span className={`access-admin-state ${campaign.is_active ? "is-active" : "is-inactive"}`}>
                    {campaign.is_active ? t("adminAccess.active") : t("adminAccess.inactive")}
                  </span>
                </header>
                <p className="access-campaign-card__help">
                  {campaign.kind === "signup_trial" ? t("adminAccess.signupHelp") : t("adminAccess.manualHelp")}
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
            <div className="access-admin-form-grid">
              <label>
                {t("adminAccess.code")}
                <input disabled={editing !== null} onChange={(event) => setField("code", event.currentTarget.value)} value={form.code} />
              </label>
              <label>
                {t("adminAccess.campaignName")}
                <input onChange={(event) => setField("name", event.currentTarget.value)} value={form.name} />
              </label>
              <label>
                {t("adminAccess.kind")}
                <select disabled={editingSemanticsLocked} onChange={(event) => setCampaignKind(event.currentTarget.value as AccessCampaignKind)} value={form.kind}>
                  <option value="signup_trial">{t("adminAccess.signupTrial")}</option>
                  <option value="manual_promotion">{t("adminAccess.manualPromotion")}</option>
                </select>
              </label>
              <label>
                {t("adminAccess.package")}
                <select disabled={editingSemanticsLocked} onChange={(event) => setField("package_code", event.currentTarget.value as CampaignFormState["package_code"])} value={form.package_code}>
                  {availablePackages.map((packageCode) => <option key={packageCode} value={packageCode}>{t(`entitlements.packageLabels.${packageCode}`, { defaultValue: packageCode })}</option>)}
                </select>
              </label>
              <label>
                {t("adminAccess.benefitDuration")}
                <input disabled={editingSemanticsLocked} min="1" onChange={(event) => setField("duration_days", event.currentTarget.value)} type="number" value={form.duration_days} />
              </label>
              <label>
                {t("adminAccess.trainingTerm")}
                <select disabled={editingSemanticsLocked || form.kind === "signup_trial"} onChange={(event) => setField("term_weeks", event.currentTarget.value)} value={form.term_weeks}>
                  {form.kind !== "signup_trial" && <option value="">—</option>}
                  <option value="4">{t("billing.fourWeeks")}</option>
                  {form.kind !== "signup_trial" && <>
                    <option value="6">{t("billing.sixWeeks")}</option>
                    <option value="8">{t("billing.eightWeeks")}</option>
                  </>}
                </select>
              </label>
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
                <input min="1" onChange={(event) => setField("max_total_redemptions", event.currentTarget.value)} type="number" value={form.max_total_redemptions} />
              </label>
              {editing === null && (
                <label className="access-admin-checkbox">
                  <input checked={form.is_active} onChange={(event) => setField("is_active", event.currentTarget.checked)} type="checkbox" />
                  {t("adminAccess.active")}
                </label>
              )}
            </div>
            <label className="access-admin-form-card__description">
              {t("adminAccess.description")}
              <textarea onChange={(event) => setField("description", event.currentTarget.value)} value={form.description} />
            </label>
            <p className="access-campaign-card__help">
              {form.kind === "signup_trial" ? t("adminAccess.signupHelp") : t("adminAccess.manualHelp")}
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
    }

    function setCampaignKind(kind: AccessCampaignKind) {
      setForm((current) => ({
        ...current,
        kind,
        package_code: kind === "signup_trial"
          ? signupTrialPackageCodes[0] ?? "launch_trial"
          : current.package_code === "launch_trial"
            ? adminAccessPackageCodes[0] ?? "complete"
            : current.package_code,
        term_weeks: kind === "signup_trial" ? "4" : current.term_weeks,
      }));
    }
  }

function toCreateInput(form: CampaignFormState): AdminAccessCampaignInput {
  return {
    code: form.code.trim(),
    name: form.name.trim(),
    description: form.description.trim() === "" ? null : form.description.trim(),
    kind: form.kind,
    package_code: form.package_code,
    duration_days: Number(form.duration_days),
    term_weeks: toTermWeeks(form.term_weeks),
    available_from: form.available_from,
    available_until: form.available_until,
    is_active: form.is_active,
    max_total_redemptions: form.max_total_redemptions === "" ? null : Number(form.max_total_redemptions),
  };
}

function toUpdateInput(form: CampaignFormState, previous: AdminAccessCampaign): AdminAccessCampaignUpdate {
  const input: AdminAccessCampaignUpdate = {
    name: form.name.trim(),
    description: form.description.trim() === "" ? null : form.description.trim(),
    available_from: form.available_from,
    available_until: form.available_until,
    max_total_redemptions: form.max_total_redemptions === "" ? null : Number(form.max_total_redemptions),
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

function toTermWeeks(value: string): AccessTermWeeks | null {
  if (value === "4" || value === "6" || value === "8") return Number(value) as AccessTermWeeks;
  return null;
}

function formatDate(value: string, english: boolean): string {
  return english
    ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "Asia/Tehran" }).format(new Date(value))
    : formatTehranDateTime(value);
}
