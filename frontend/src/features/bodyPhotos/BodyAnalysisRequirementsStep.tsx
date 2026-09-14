import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { getProfile, updateProfile } from "../profile/api";
import {
  validateBodyAnalysisMeasurements,
} from "../profile/profileValidation";
import {
  MeasurementFields,
} from "../profile/ProfileFormFields";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import type {
  MeasurementField,
  MeasurementFormValues,
  Profile,
  ProfilePatch,
} from "../profile/types";
import "./bodyPhotos.css";

type BodyAnalysisRequirementsStepProps = {
  onConfirmed: () => void;
  onCancel: () => void;
};

const circumferenceFields: MeasurementField[] = [
  "shoulder_circumference_cm",
  "waist_circumference_cm",
  "hip_circumference_cm",
];

export function BodyAnalysisRequirementsStep({
  onConfirmed,
  onCancel,
}: BodyAnalysisRequirementsStepProps) {
  const { t, i18n } = useTranslation();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [values, setValues] = useState<MeasurementFormValues | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [saveError, setSaveError] = useState<unknown | null>(null);

  useEffect(() => {
    let active = true;
    void getProfile()
      .then((loadedProfile) => {
        if (!active) return;
        if (loadedProfile === null) {
          setLoadError(new Error("Profile could not be loaded"));
          return;
        }
        const nextValues = measurementValuesFromProfile(loadedProfile);
        setProfile(loadedProfile);
        setValues(nextValues);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const validationErrors = useMemo(
    () => values === null ? {} : validateBodyAnalysisMeasurements(values),
    [values],
  );
  const canContinue = values !== null
    && Object.keys(validationErrors).length === 0
    && confirmed
    && !busy;
  const errorLocale = i18n.resolvedLanguage === "en" ? "en" : "fa";

  function changeMeasurement(field: MeasurementField, value: string) {
    setValues((current) => current === null ? current : { ...current, [field]: value });
    setConfirmed(false);
    setSaveError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (profile === null || values === null || !confirmed || busy) return;
    const nextErrors = validateBodyAnalysisMeasurements(values);
    if (Object.keys(nextErrors).length > 0) return;

    setBusy(true);
    setSaveError(null);
    try {
      const patch = measurementPatch(values, profile);
      if (Object.keys(patch).length > 0) {
        await updateProfile(patch);
      }
      onConfirmed();
    } catch (error: unknown) {
      setSaveError(error);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="body-photo-wizard body-analysis-requirements" aria-labelledby="body-analysis-requirements-title">
        <p role="status">{t("bodyPhotos.measurements.loading")}</p>
      </section>
    );
  }

  if (loadError !== null || values === null) {
    return (
      <section className="body-photo-wizard body-analysis-requirements" aria-labelledby="body-analysis-requirements-title">
        <p className="eyebrow eyebrow--accent">{t("bodyPhotos.measurements.eyebrow")}</p>
        <h1 id="body-analysis-requirements-title" className="fitician-display">
          {t("bodyPhotos.measurements.title")}
        </h1>
        {loadError !== null && (
          <AppErrorNotice audience="member" context="body_analysis" error={loadError} locale={errorLocale} />
        )}
        <button className="secondary-button" type="button" onClick={onCancel}>
          {t("bodyPhotos.measurements.back")}
        </button>
      </section>
    );
  }

  return (
    <section className="body-photo-wizard body-analysis-requirements" aria-labelledby="body-analysis-requirements-title">
      <header className="body-analysis-requirements__header">
        <div className="body-analysis-requirements__heading">
          <p className="eyebrow eyebrow--accent">{t("bodyPhotos.measurements.eyebrow")}</p>
          <h1 id="body-analysis-requirements-title" className="fitician-display">
            {t("bodyPhotos.measurements.title")}
          </h1>
          <p>{t("bodyPhotos.measurements.body")}</p>
        </div>
        <div
          className="body-analysis-requirements__status"
          data-state={confirmed ? "confirmed" : "pending"}
          role="status"
          aria-live="polite"
        >
          <span className="body-analysis-requirements__status-mark" aria-hidden="true">
            {confirmed ? "✓" : "01"}
          </span>
          <span className="body-analysis-requirements__status-copy">
            <strong>
              {t(`bodyPhotos.measurements.status.${confirmed ? "confirmed" : "pending"}`)}
            </strong>
            <small>
              {t(`bodyPhotos.measurements.status.${confirmed ? "confirmedHint" : "pendingHint"}`)}
            </small>
          </span>
        </div>
      </header>
      <form className="body-analysis-requirements__form" onSubmit={(event) => void submit(event)}>
        <fieldset className="profile-fieldset body-analysis-measurement-panel" disabled={busy}>
          <legend>{t("bodyPhotos.measurements.fieldsLegend")}</legend>
          <div className="body-analysis-measurement-panel__rail" aria-hidden="true" />
          <section
            className="body-analysis-requirements__group body-analysis-requirements__group--essential"
            aria-labelledby="body-analysis-essential-title"
          >
            <header className="body-analysis-requirements__group-header">
              <span className="body-analysis-requirements__group-step" aria-hidden="true">01</span>
              <div>
                <h2 id="body-analysis-essential-title">
                  {t("bodyPhotos.measurements.essentialTitle")}
                </h2>
                <p>{t("bodyPhotos.measurements.essentialBody")}</p>
              </div>
            </header>
            <MeasurementFields
              values={values}
              errors={validationErrors}
              onChange={changeMeasurement}
              showCircumferences={false}
              showUnits
              idPrefix="body-analysis"
            />
          </section>
          <section
            className="body-analysis-requirements__group body-analysis-requirements__group--proportions"
            aria-labelledby="body-analysis-proportions-title"
          >
            <header className="body-analysis-requirements__group-header">
              <span className="body-analysis-requirements__group-step" aria-hidden="true">02</span>
              <div>
                <h2 id="body-analysis-proportions-title">
                  {t("bodyPhotos.measurements.proportionsTitle")}
                </h2>
                <p>{t("bodyPhotos.measurements.proportionsBody")}</p>
              </div>
            </header>
            <MeasurementFields
              values={values}
              errors={validationErrors}
              onChange={changeMeasurement}
              showPrimaryMeasurements={false}
              requiredCircumferences
              showUnits
              idPrefix="body-analysis"
            />
          </section>
        </fieldset>
        <div className="body-analysis-requirements__note">
          <span className="body-analysis-requirements__note-mark" aria-hidden="true">i</span>
          <p className="body-photo-muted">{t("bodyPhotos.measurements.snapshotNote")}</p>
        </div>
        <label className="body-photo-consent body-analysis-requirements__consent">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            disabled={busy}
          />
          <span>{t("bodyPhotos.measurements.confirmLabel")}</span>
        </label>
        {saveError !== null && (
          <AppErrorNotice audience="member" context="body_analysis" error={saveError} locale={errorLocale} />
        )}
        <div className="body-analysis-requirements__actions">
          <button className="secondary-button" type="button" onClick={onCancel} disabled={busy}>
            {t("bodyPhotos.measurements.back")}
          </button>
          <button className="primary-button" type="submit" disabled={!canContinue}>
            {busy ? t("bodyPhotos.measurements.saving") : t("bodyPhotos.measurements.continue")}
          </button>
        </div>
      </form>
    </section>
  );
}

function measurementValuesFromProfile(profile: Profile): MeasurementFormValues {
  return {
    height_cm: String(profile.height_cm),
    current_weight_kg: String(profile.current_weight_kg),
    shoulder_circumference_cm: profile.shoulder_circumference_cm === null
      ? ""
      : String(profile.shoulder_circumference_cm),
    waist_circumference_cm: profile.waist_circumference_cm === null
      ? ""
      : String(profile.waist_circumference_cm),
    hip_circumference_cm: profile.hip_circumference_cm === null
      ? ""
      : String(profile.hip_circumference_cm),
  };
}

function measurementPatch(
  values: MeasurementFormValues,
  profile: Profile,
): ProfilePatch {
  const patch: ProfilePatch = {};
  const height = Number(values.height_cm.trim());
  const weight = Number(values.current_weight_kg.trim());
  if (height !== profile.height_cm) patch.height_cm = height;
  if (weight !== profile.current_weight_kg) patch.current_weight_kg = weight;

  for (const field of circumferenceFields) {
    const value = Number(values[field].trim());
    if (value !== profile[field]) patch[field] = value;
  }
  return patch;
}
