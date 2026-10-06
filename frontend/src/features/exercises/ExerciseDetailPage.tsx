import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router-dom";

import heroStrengthFallback from "../../assets/landing/hero-strength-fallback.jpg";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { MemberHeaderMedia } from "../../shared/MemberHeaderMedia";
import { getExercise } from "./api";
import { ReadyExerciseDetail } from "./ExerciseDetailPresentation";
import type { ExerciseDetail } from "./types";
import "./exercises.css";

type DetailState = "loading" | "ready" | "not-found" | "error";

export function ExerciseDetailPage() {
  const { i18n, t } = useTranslation();
  const { slug } = useParams();
  const location = useLocation();
  const [exercise, setExercise] = useState<ExerciseDetail | null>(null);
  const [state, setState] = useState<DetailState>("loading");
  const [retry, setRetry] = useState(0);
  const [mediaPresentation, setMediaPresentation] = useState<"male" | "female">("male");
  const [mediaSwitching, setMediaSwitching] = useState(false);
  const [loadError, setLoadError] = useState<unknown | null>(null);
  const [mediaSwitchError, setMediaSwitchError] = useState<unknown | null>(null);
  const [mediaSwitchUnavailable, setMediaSwitchUnavailable] = useState(false);
  const isEnglish = i18n.resolvedLanguage === "en";
  const catalogPath = `/exercises${location.search}`;

  useEffect(() => {
    if (slug === undefined) {
      setState("not-found");
      return;
    }

    let active = true;
    setState("loading");
    setLoadError(null);
    void getExercise(slug)
      .then((response) => {
        if (!active) return;
        if (response === null) {
          setExercise(null);
          setState("not-found");
          return;
        }
        setExercise(response);
        setMediaPresentation(resolveMediaPresentation(response));
        setMediaSwitchError(null);
        setMediaSwitchUnavailable(false);
        setState("ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(error);
        setState("error");
      });
    return () => {
      active = false;
    };
  }, [retry, slug]);

  async function changeMediaPresentation(presentation: "male" | "female") {
    if (slug === undefined || mediaSwitching || presentation === mediaPresentation) return;
    setMediaSwitching(true);
    setMediaSwitchError(null);
    setMediaSwitchUnavailable(false);
    try {
      const response = await getExercise(slug, presentation);
      if (response === null) {
        setMediaSwitchUnavailable(true);
        return;
      }
      setExercise(response);
      setMediaPresentation(resolveMediaPresentation(response));
    } catch (error: unknown) {
      setMediaSwitchError(error);
    } finally {
      setMediaSwitching(false);
    }
  }

  return (
    <div className="exercise-catalog-shell exercise-detail-shell">
      <MemberHeaderMedia imageSrc={heroStrengthFallback} className="member-page-background" />
      <main className="exercise-detail-main">
        {state === "loading" && (
          <DetailMessage role="status" message={t("exerciseDetail.loading")} />
        )}
        {state === "error" && (
          loadError !== null && (
            <AppErrorNotice
              audience="member"
              context="workout"
              error={loadError}
              locale={isEnglish ? "en" : "fa"}
              onRetry={() => setRetry((value) => value + 1)}
            />
          )
        )}
        {state === "not-found" && (
          <section className="exercise-detail-message" aria-labelledby="unknown-exercise">
            <span className="exercise-detail-message__mark" aria-hidden="true">?</span>
            <h1 id="unknown-exercise">{t("exerciseDetail.unknownTitle")}</h1>
            <p>{t("exerciseDetail.unknownBody")}</p>
            <Link className="exercise-detail-back" to={catalogPath}>
              {t("exerciseDetail.backToCatalog")}
            </Link>
          </section>
        )}
        {state === "ready" && exercise !== null && (
          <ReadyExerciseDetail
            exercise={exercise}
            catalogPath={catalogPath}
            isEnglish={isEnglish}
            mediaPresentation={mediaPresentation}
            mediaSwitching={mediaSwitching}
            mediaSwitchError={mediaSwitchError}
            mediaSwitchUnavailable={mediaSwitchUnavailable}
            onMediaPresentationChange={changeMediaPresentation}
          />
        )}
      </main>
    </div>
  );
}

function resolveMediaPresentation(exercise: ExerciseDetail): "male" | "female" {
  if (exercise.media_presentation === "female") return "female";
  if (exercise.media_presentation === "male") return "male";
  const presentation = exercise.media_assets?.[0]?.presentation;
  return presentation === "female" ? "female" : "male";
}

function DetailMessage({
  role,
  message,
  action,
  onAction,
}: {
  role: "status" | "alert";
  message: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="catalog-status exercise-detail-status" role={role}>
      <span className="catalog-status__mark" aria-hidden="true" />
      <p>{message}</p>
      {action !== undefined && onAction !== undefined && (
        <button className="retry-button" type="button" onClick={onAction}>
          {action}
        </button>
      )}
    </div>
  );
}
