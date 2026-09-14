import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError, formatTehranDateTimeForLocale } from "@fitician/core";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import {
  getBodyPhotoComparison,
  getBodyPhotoAnalysis,
  getBodyPhotoSession,
  retryBodyPhotoAnalysis,
  startBodyPhotoAnalysis,
} from "./api";
import { BodyAnalysisResult } from "./BodyAnalysisResult";
import { ProgressComparison } from "./ProgressComparison";
import type { BodyAnalysis, BodyPhotoSession } from "./types";
import "./bodyPhotos.css";

const activeAnalysisStates = new Set(["queued", "validating", "analyzing"]);

export function BodyAnalysisResultPage() {
  const { t, i18n } = useTranslation();
  const { sessionId } = useParams();
  const [session, setSession] = useState<BodyPhotoSession | null>(null);
  const [analysis, setAnalysis] = useState<BodyAnalysis | null>(null);
  const [comparison, setComparison] = useState<Awaited<ReturnType<typeof getBodyPhotoComparison>>>(null);
  const [comparisonError, setComparisonError] = useState<unknown | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [analysisActionError, setAnalysisActionError] = useState<unknown | null>(null);
  const [pollError, setPollError] = useState<unknown | null>(null);

  const load = useCallback(async () => {
    if (sessionId === undefined) {
      setLoadError(new Error("Body analysis session id is missing"));
      setLoading(false);
      return;
    }
    setLoadError(null);
    setComparisonError(null);
    setAnalysisActionError(null);
    setPollError(null);
    try {
      const [loadedSession, loadedAnalysis, loadedComparisonResult] = await Promise.all([
        getBodyPhotoSession(sessionId),
        getBodyPhotoAnalysis(sessionId),
        getBodyPhotoComparison(sessionId)
          .then((value) => ({ value, error: null as unknown | null }))
          .catch((error: unknown) => ({
            value: null,
            error: isMissingComparison(error) ? null : error,
          })),
      ]);
      setSession(loadedSession);
      let effectiveAnalysis = loadedAnalysis;
      if (effectiveAnalysis === null && loadedSession.state === "queued") {
        try {
          effectiveAnalysis = await startBodyPhotoAnalysis(sessionId);
          setAnalysisActionError(null);
        } catch (cause: unknown) {
          setAnalysisActionError(cause);
        }
      }
      setAnalysis(effectiveAnalysis);
      setComparison(loadedComparisonResult.value);
      setComparisonError(loadedComparisonResult.error);
    } catch (cause: unknown) {
      setLoadError(cause);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (sessionId === undefined || analysis === null || !activeAnalysisStates.has(analysis.status)) {
      return;
    }
    const timer = window.setTimeout(() => {
      void getBodyPhotoAnalysis(sessionId)
        .then((next) => {
          setPollError(null);
          if (next !== null) {
            setAnalysis(next);
            if (next.normalized_result !== null) {
              void getBodyPhotoComparison(sessionId)
                .then(setComparison)
                .catch((cause: unknown) => {
                  if (!isMissingComparison(cause)) setComparisonError(cause);
                });
            }
          }
        })
        .catch((cause: unknown) => setPollError(cause));
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [analysis, sessionId]);

  async function retry() {
    if (sessionId === undefined || actionBusy) return;
    setActionBusy(true);
    try {
      const next = analysis?.status === "failed"
        ? await retryBodyPhotoAnalysis(sessionId)
        : await startBodyPhotoAnalysis(sessionId);
      setAnalysis(next);
      setAnalysisActionError(null);
      if (next.normalized_result !== null) {
        void getBodyPhotoComparison(sessionId)
          .then((value) => {
            setComparison(value);
            setComparisonError(null);
          })
          .catch((cause: unknown) => {
            if (!isMissingComparison(cause)) setComparisonError(cause);
          });
      }
    } catch (cause: unknown) {
      setAnalysisActionError(cause);
    } finally {
      setActionBusy(false);
    }
  }

  if (loading) {
    return <main className="body-analysis-page fitician-page"><p role="status">{t("bodyPhotos.results.loading")}</p></main>;
  }
  if (loadError !== null || session === null) {
    return (
      <main className="body-analysis-page fitician-page">
        <AppErrorNotice
          audience="member"
          context="body_analysis"
          error={loadError ?? new Error("Body analysis session is unavailable")}
          locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        />
        <button className="secondary-button" type="button" onClick={() => {
          setLoading(true);
          void load();
        }}>{t("common.retry")}</button>
      </main>
    );
  }

  const locale = i18n.resolvedLanguage === "en" ? "en" : "fa-IR";
  const sessionDate = formatTehranDateTimeForLocale(session.created_at, locale);
  const failedAnalysisMessage = analysis?.error_code === null || analysis?.error_code === undefined
    ? analysis?.safe_error_message ?? t("bodyPhotos.results.failedSafe")
    : t(`bodyPhotos.results.providerErrors.${analysis.error_code}`, {
      defaultValue: analysis.safe_error_message ?? t("bodyPhotos.results.failedSafe"),
    });

  return (
    <main className="body-analysis-page fitician-page">
      <header className="body-analysis-page__header">
        <p className="eyebrow eyebrow--accent">{t("bodyPhotos.eyebrow")}</p>
        <h1 className="fitician-display">{t("bodyPhotos.results.title")}</h1>
        <p>{t("bodyPhotos.results.sessionDate", { date: sessionDate })}</p>
      </header>

      {pollError !== null && (
        <AppErrorNotice
          audience="member"
          context="body_analysis"
          error={pollError}
          locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        />
      )}
      {comparisonError !== null && (
        <AppErrorNotice
          audience="member"
          context="body_analysis"
          error={comparisonError}
          locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        />
      )}

      {analysis === null && analysisActionError === null && (
        <p role="status">{t("bodyPhotos.results.notStarted")}</p>
      )}
      {analysisActionError !== null && analysis?.status !== "failed" && (
        <section className="body-analysis-status body-analysis-status--failed">
          <div>
            <strong>{t("bodyPhotos.results.analysisStatus.failed")}</strong>
            <p>{t("bodyPhotos.results.failedSafe")}</p>
            <AppErrorNotice
              audience="member"
              context="body_analysis"
              error={analysisActionError}
              locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
            />
          </div>
          <button className="secondary-button" type="button" disabled={actionBusy} onClick={() => void retry()}>
            {t("bodyPhotos.results.retry")}
          </button>
        </section>
      )}
      {analysis !== null && activeAnalysisStates.has(analysis.status) && (
        <section className="body-analysis-status" role="status">
          <span className="body-analysis-spinner" aria-hidden="true" />
          <div>
            <strong>{t(`bodyPhotos.results.analysisStatus.${analysis.status}`)}</strong>
            <p>{t("bodyPhotos.results.processingHelp")}</p>
          </div>
        </section>
      )}
      {analysis?.status === "failed" && (
        <section className="body-analysis-status body-analysis-status--failed" role="alert">
          <div>
            <strong>{t("bodyPhotos.results.analysisStatus.failed")}</strong>
            <p>{failedAnalysisMessage}</p>
            {analysis.photo_validation?.issues.map((issue) => (
              <div className="body-analysis-status__issue" key={issue.view}>
                <p>
                  <strong>{t(`bodyPhotos.views.${issue.view}`)}: </strong>
                  {issue.reasons.map((reason) => t(`bodyPhotos.results.photoValidation.${reason}`)).join(" · ")}
                </p>
                <Link
                  className="body-photo-link-button"
                  to={`/body-progress/new?sessionId=${session.id}&view=${issue.view}`}
                >
                  {t("bodyPhotos.results.editPhoto", {
                    view: t(`bodyPhotos.views.${issue.view}`),
                  })}
                </Link>
              </div>
            ))}
          </div>
          <button className="secondary-button" type="button" disabled={actionBusy} onClick={() => void retry()}>
            {t("bodyPhotos.results.retry")}
          </button>
        </section>
      )}

      {analysis !== null && <BodyAnalysisResult analysis={analysis} />}
      {comparison !== null && <ProgressComparison comparison={comparison} />}
      <details className="body-analysis-photo-details">
        <summary>{t("bodyPhotos.results.photosLabel")}</summary>
        <section className="body-analysis-photos" aria-label={t("bodyPhotos.results.photosLabel")}>
          {session.photos.map((photo) => <figure key={photo.id}><img src={photo.content_url} alt={t("bodyPhotos.results.photoAlt", { view: t(`bodyPhotos.views.${photo.view}`) })} /><figcaption>{t(`bodyPhotos.views.${photo.view}`)}</figcaption></figure>)}
        </section>
      </details>
      {analysis?.normalized_result !== null && analysis?.normalized_result !== undefined && (
        <Link className="primary-button body-analysis-plan-link" to="/workout-plan">
          {t("bodyPhotos.results.viewWorkoutPlan")}
        </Link>
      )}
    </main>
  );
}

function isMissingComparison(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
