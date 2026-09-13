import { useEffect, useState, type FormEvent } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  adminAccessPackageCodes,
  getCampaigns,
  getUserAccess,
  grantUserAccess,
  redeemUserCampaign,
  revokeUserAccess,
  type AccessTermWeeks,
  type AdminAccessCampaign,
  type AdminGrant,
  type AdminUserAccess,
} from "./adminAccessApi";

type Action = "grant" | "campaign" | "revoke" | null;

type GrantForm = {
  package_code: AdminGrant["package_code"];
  term_weeks: string;
  starts_at: string;
  ends_at: string;
  reason: string;
  client_idempotency_key: string;
};

const initialGrantForm: GrantForm = {
  package_code: "complete",
  term_weeks: "8",
  starts_at: "",
  ends_at: "",
  reason: "",
  client_idempotency_key: "",
};

export function AdminUserAccessDetailPage() {
  const { i18n, t } = useTranslation();
  const { userId } = useParams<{ userId: string }>();
  const memberId = userId ?? "";
  const [access, setAccess] = useState<AdminUserAccess | null>(null);
  const [campaigns, setCampaigns] = useState<AdminAccessCampaign[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [action, setAction] = useState<Action>(null);
  const [selectedGrant, setSelectedGrant] = useState<AdminGrant | null>(null);
  const [grantForm, setGrantForm] = useState<GrantForm>(initialGrantForm);
  const [campaignId, setCampaignId] = useState("");
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState(false);
  const [saving, setSaving] = useState(false);
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    let active = true;
    setState("loading");
    if (memberId === "") {
      setState("error");
      return () => { active = false; };
    }
    void getUserAccess(memberId)
      .then((result) => {
        if (!active) return;
        setAccess(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [memberId]);

  function openGrant() {
    setSelectedGrant(null);
    setGrantForm({
      ...initialGrantForm,
      client_idempotency_key: makeClientIdempotencyKey(),
    });
    setReason("");
    setFormError(false);
    setAction("grant");
  }

  function openCampaign() {
    setSelectedGrant(null);
    setCampaignId("");
    setReason("");
    setFormError(false);
    setAction("campaign");
    void getCampaigns().then(setCampaigns).catch(() => setFormError(true));
  }

  function openRevoke(grant: AdminGrant) {
    setSelectedGrant(grant);
    setReason("");
    setFormError(false);
    setAction("revoke");
  }

  function closeAction() {
    setAction(null);
    setSelectedGrant(null);
    setFormError(false);
  }

  async function refresh() {
    const result = await getUserAccess(memberId);
    setAccess(result);
  }

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(false);
    if (action === "grant") {
      if (grantForm.ends_at === "" || grantForm.reason.trim() === "" || grantForm.client_idempotency_key.trim() === "") {
        setFormError(true);
        return;
      }
      setSaving(true);
      try {
        await grantUserAccess(memberId, {
          package_code: grantForm.package_code,
          term_weeks: toTermWeeks(grantForm.term_weeks),
          starts_at: toIsoDateTime(grantForm.starts_at),
          ends_at: toIsoDateTime(grantForm.ends_at) as string,
          reason: grantForm.reason.trim(),
          client_idempotency_key: grantForm.client_idempotency_key.trim(),
        });
        await refresh();
        closeAction();
      } catch {
        setFormError(true);
      } finally {
        setSaving(false);
      }
      return;
    }
    if (action === "campaign") {
      if (campaignId === "" || reason.trim() === "") {
        setFormError(true);
        return;
      }
      setSaving(true);
      try {
        await redeemUserCampaign(memberId, campaignId, reason.trim());
        await refresh();
        closeAction();
      } catch {
        setFormError(true);
      } finally {
        setSaving(false);
      }
      return;
    }
    if (action === "revoke" && selectedGrant !== null) {
      if (reason.trim() === "") {
        setFormError(true);
        return;
      }
      setSaving(true);
      try {
        await revokeUserAccess(selectedGrant.id, reason.trim());
        await refresh();
        closeAction();
      } catch {
        setFormError(true);
      } finally {
        setSaving(false);
      }
    }
  }

  if (state === "loading") return <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>;
  if (state === "error" || access === null) return <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.userNotFound")}</p>;

  return (
    <main className="access-admin-page fitician-page">
      <div className="access-admin-page__container">
        <Link className="access-admin-back-link" to="/admin/billing/users">{t("adminAccess.backToUsers")}</Link>
        <header className="access-user-detail__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.user")}</p>
            <h1>{access.member.display_name ?? access.member.email ?? access.member.phone_number ?? access.member.user_id}</h1>
            <p>{access.member.email ?? access.member.phone_number ?? access.member.user_id}</p>
          </div>
          <div className="access-user-detail__actions">
            <button className="access-admin-button access-admin-button--primary" onClick={openGrant} type="button">{t("adminAccess.grantAccess")}</button>
            <button className="access-admin-button access-admin-button--quiet" onClick={openCampaign} type="button">{t("adminAccess.applyCampaign")}</button>
          </div>
        </header>

        <section className="access-detail-summary" aria-labelledby="access-detail-summary-title">
          <h2 id="access-detail-summary-title">{t("adminAccess.entitlementSnapshot")}</h2>
          <div className="access-detail-summary__grid">
            <div><span>{t("adminAccess.currentPackage")}</span><strong>{t(`entitlements.packageLabels.${access.entitlement_snapshot.primary_package}`, { defaultValue: access.entitlement_snapshot.primary_package })}</strong></div>
            <div><span>{t("adminAccess.activePackages")}</span><strong>{access.entitlement_snapshot.active_packages.map((code) => t(`entitlements.packageLabels.${code}`, { defaultValue: code })).join("، ") || "—"}</strong></div>
            <div><span>{t("adminAccess.trialState")}</span><strong>{access.entitlement_snapshot.trial_active ? t("entitlements.trialActive") : t("adminAccess.inactive")}</strong></div>
            <div><span>{t("adminAccess.accessEnd")}</span><strong>{access.member.paid_access_end === null ? "—" : formatDate(access.member.paid_access_end, english)}</strong></div>
          </div>
          <p className="access-detail-summary__entitlements">{access.entitlement_snapshot.granted_entitlements.join(" · ") || "—"}</p>
        </section>

        <section className="access-grants-section" aria-labelledby="access-grants-title">
          <header className="access-detail-section-heading"><div><p className="eyebrow eyebrow--accent">{t("adminAccess.allGrants")}</p><h2 id="access-grants-title">{t("adminAccess.allGrants")}</h2></div><span>{access.grants.length}</span></header>
          <div className="access-grant-list">
            {access.grants.map((grant) => (
              <article className="access-grant-card" data-testid={`access-grant-${grant.id}`} key={grant.id}>
                <header>
                  <div><span className="access-admin-code">{grant.id}</span><h3>{t(`entitlements.packageLabels.${grant.package_code}`, { defaultValue: grant.package_code })}</h3></div>
                  <span className="access-grant-card__status">{grant.status.toUpperCase()}</span>
                </header>
                <dl>
                  <div><dt>{t("adminAccess.accessSource")}</dt><dd>{sourceLabel(grant.source, t)}</dd></div>
                  <div><dt>{t("adminAccess.trainingTerm")}</dt><dd>{grant.term_weeks === null ? "—" : `${grant.term_weeks} ${t("adminAccess.weeks")}`}</dd></div>
                  <div><dt>{t("adminAccess.start")}</dt><dd>{formatDate(grant.starts_at, english)}</dd></div>
                  <div><dt>{t("adminAccess.end")}</dt><dd>{grant.ends_at === null ? "—" : formatDate(grant.ends_at, english)}</dd></div>
                  {grant.revoked_at !== null && <div><dt>{t("adminAccess.revokedAt")}</dt><dd>{formatDate(grant.revoked_at, english)}</dd></div>}
                </dl>
                {grant.revoked_at === null && (
                  <button className="access-admin-button access-admin-button--quiet" onClick={() => openRevoke(grant)} type="button">{t("adminAccess.revokeAccess")}</button>
                )}
              </article>
            ))}
          </div>
        </section>

        {action !== null && (
          <section className="access-admin-form-card access-action-form" aria-label={actionLabel(action, t)}>
            <header>
              <div><p className="eyebrow eyebrow--accent">{t("adminAccess.reason")}</p><h2>{actionLabel(action, t)}</h2></div>
              <button className="access-admin-button access-admin-button--quiet" onClick={closeAction} type="button">{t("adminAccess.cancel")}</button>
            </header>
            <form onSubmit={(event) => void submitAction(event)}>
              {action === "grant" && (
                <div className="access-admin-form-grid">
                  <label>{t("adminAccess.package")}<select onChange={(event) => { const value = event.currentTarget.value as GrantForm["package_code"]; setGrantForm((current) => ({ ...current, package_code: value })); }} value={grantForm.package_code}>{adminAccessPackageCodes.map((code) => <option key={code} value={code}>{t(`entitlements.packageLabels.${code}`, { defaultValue: code })}</option>)}</select></label>
                  <label>{t("adminAccess.trainingTerm")}<select onChange={(event) => { const value = event.currentTarget.value; setGrantForm((current) => ({ ...current, term_weeks: value })); }} value={grantForm.term_weeks}><option value="">—</option><option value="4">{t("billing.fourWeeks")}</option><option value="6">{t("billing.sixWeeks")}</option><option value="8">{t("billing.eightWeeks")}</option></select></label>
                  <label>{t("adminAccess.start")}<input onChange={(event) => { const value = event.currentTarget.value; setGrantForm((current) => ({ ...current, starts_at: value })); }} type="datetime-local" value={grantForm.starts_at} /></label>
                  <label>{t("adminAccess.end")}<input required onChange={(event) => { const value = event.currentTarget.value; setGrantForm((current) => ({ ...current, ends_at: value })); }} type="datetime-local" value={grantForm.ends_at} /></label>
                  <label>{t("adminAccess.reason")}<textarea required onChange={(event) => { const value = event.currentTarget.value; setGrantForm((current) => ({ ...current, reason: value })); }} value={grantForm.reason} /></label>
                </div>
              )}
              {action === "campaign" && (
                <div className="access-admin-form-grid">
                  <label>{t("adminAccess.selectCampaign")}<select required aria-label={t("adminAccess.selectCampaign")} onChange={(event) => setCampaignId(event.currentTarget.value)} value={campaignId}><option value="">—</option>{campaigns.filter((campaign) => campaign.kind === "manual_promotion" && campaign.is_active).map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></label>
                  <label>{t("adminAccess.redeemReason")}<textarea required aria-label={t("adminAccess.redeemReason")} onChange={(event) => setReason(event.currentTarget.value)} value={reason} /></label>
                </div>
              )}
              {action === "revoke" && selectedGrant !== null && (
                <div className="access-revoke-form">
                  {selectedGrant.source === "subscription" && <p className="access-campaign-card__warning">{t("adminAccess.paidRevokeWarning")}</p>}
                  <p>{t("adminAccess.noUnrevoke")}</p>
                  <label>{t("adminAccess.revokeReason")}<textarea required aria-label={t("adminAccess.revokeReason")} onChange={(event) => setReason(event.currentTarget.value)} value={reason} /></label>
                </div>
              )}
              {formError && <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.saveError")}</p>}
              <button className="access-admin-button access-admin-button--primary" disabled={saving} type="submit">{action === "revoke" ? t("adminAccess.confirmRevoke") : t("adminAccess.saveChanges")}</button>
            </form>
          </section>
        )}
      </div>
    </main>
  );
}

function formatDate(value: string, english: boolean): string {
  return new Intl.DateTimeFormat(english ? "en" : "fa-IR", { dateStyle: "medium" }).format(new Date(value));
}

function toIsoDateTime(value: string): string | null {
  return value === "" ? null : new Date(value).toISOString();
}

function toTermWeeks(value: string): AccessTermWeeks | null {
  if (value === "4" || value === "6" || value === "8") return Number(value) as AccessTermWeeks;
  return null;
}

function makeClientIdempotencyKey(): string {
  const browserCrypto = globalThis.crypto;
  if (typeof browserCrypto?.randomUUID === "function") {
    return browserCrypto.randomUUID();
  }
  if (typeof browserCrypto?.getRandomValues === "function") {
    const values = browserCrypto.getRandomValues(new Uint32Array(4));
    return `admin-grant-${Array.from(values, (value) => value.toString(16)).join("-")}`;
  }
  return `admin-grant-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function sourceLabel(source: AdminGrant["source"], t: TFunction): string {
  const labels: Record<AdminGrant["source"], string> = {
    subscription: t("adminAccess.sourceSubscription"),
    admin: t("adminAccess.sourceAdmin"),
    promotion: t("adminAccess.sourcePromotion"),
    launch_trial: t("adminAccess.sourceLaunchTrial"),
    manual: t("adminAccess.sourceManual"),
  };
  return labels[source];
}

function actionLabel(action: Exclude<Action, null>, t: (key: string) => string): string {
  if (action === "grant") return t("adminAccess.grantAccess");
  if (action === "campaign") return t("adminAccess.applyCampaign");
  return t("adminAccess.revokeAccess");
}
