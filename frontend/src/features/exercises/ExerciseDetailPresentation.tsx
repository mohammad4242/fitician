import { useTranslation } from "react-i18next";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { ExerciseMediaCarousel } from "./ExerciseMediaCarousel";
import { buildExerciseMediaItems } from "./exerciseMediaItems";
import { ExerciseLink } from "./ExerciseCatalog";
import type { ExerciseDetail, ExerciseMediaAsset } from "./types";

export type ExercisePresentationDetail = Pick<ExerciseDetail,
  "slug" | "name_fa" | "name_en" | "content_type" | "body_region" | "primary_muscle"
  | "muscle_focus" | "secondary_muscles" | "equipment" | "difficulty" | "labels"
  | "instructions_fa" | "instructions_en" | "safety_notes_fa" | "safety_notes_en"
  | "media_path" | "media_type" | "media_attribution"
> & { media_assets?: Omit<ExerciseMediaAsset, "media_source_url" | "media_license">[] };
export function ReadyExerciseDetail({
  exercise,
  catalogPath,
  isEnglish,
  mediaPresentation,
  mediaSwitching,
  mediaSwitchError,
  mediaSwitchUnavailable,
  onMediaPresentationChange,
  publicMode = false,
}: {
  exercise: ExercisePresentationDetail;
  catalogPath: string;
  isEnglish: boolean;
  mediaPresentation: "male" | "female";
  mediaSwitching: boolean;
  mediaSwitchError: unknown | null;
  mediaSwitchUnavailable: boolean;
  onMediaPresentationChange?: (presentation: "male" | "female") => void;
  publicMode?: boolean;
}) {
  const { t } = useTranslation();
  const name = isEnglish ? exercise.name_en : exercise.name_fa;
  const secondaryName = isEnglish ? exercise.name_fa : exercise.name_en;
  const instructions = isEnglish ? exercise.instructions_en : exercise.instructions_fa;
  const safetyNotes = isEnglish ? exercise.safety_notes_en : exercise.safety_notes_fa;
  const secondaryMuscles = exercise.secondary_muscles.map((value) =>
    t(`catalog.muscle.${value}`),
  );
  const labels = exercise.labels ?? [];
  const equipmentNames = exercise.equipment.map((value) =>
    t(`catalog.equipment.${value}`),
  );
  const mediaItems = buildExerciseMediaItems(exercise);

  return (
    <>
      <nav className="catalog-breadcrumb" aria-label={t("exerciseDetail.breadcrumbLabel")}>
        <ExerciseLink publicMode={publicMode} to={catalogPath}>{t("catalog.title")}</ExerciseLink>
        <span aria-hidden="true">←</span>
        <span>{exercise.body_region === null ? t("catalog.needsReview") : t(`catalog.bodyRegion.${exercise.body_region}`)}</span>
        {exercise.primary_muscle !== null && (
          <>
            <span aria-hidden="true">←</span>
            <span>{t(`catalog.muscle.${exercise.primary_muscle}`)}</span>
          </>
        )}
        {exercise.muscle_focus !== null && (
          <>
            <span aria-hidden="true">←</span>
            <span>{t(`catalog.muscleFocus.${exercise.muscle_focus}`)}</span>
          </>
        )}
        <span aria-hidden="true">←</span>
        <span aria-current="page">{name}</span>
      </nav>

      <article className="exercise-detail-sheet">
        <div className="exercise-detail-media">
          <ExerciseMediaCarousel
            items={mediaItems}
            name={name}
          />
          {onMediaPresentationChange && <div
            className="exercise-media-presentation-toggle"
            role="group"
            aria-label={t("exerciseDetail.mediaPresentationLabel")}
          >
            <button
              type="button"
              aria-label={t("exerciseDetail.maleVideo")}
              aria-pressed={mediaPresentation === "male"}
              disabled={mediaSwitching}
              onClick={() => onMediaPresentationChange("male")}
            >♂️</button>
            <button
              type="button"
              aria-label={t("exerciseDetail.femaleVideo")}
              aria-pressed={mediaPresentation === "female"}
              disabled={mediaSwitching}
              onClick={() => onMediaPresentationChange("female")}
            >♀️</button>
          </div>}
          {mediaSwitchError !== null && (
            <AppErrorNotice
              audience="member"
              context="workout"
              error={mediaSwitchError}
              locale={isEnglish ? "en" : "fa"}
            />
          )}
          {mediaSwitchUnavailable && (
            <p className="exercise-media-presentation-error" role="alert">
              {t("exerciseDetail.mediaSwitchError")}
            </p>
          )}
        </div>

        <details open={publicMode || undefined} className="exercise-detail-accordion exercise-detail-overview">
          <summary className="exercise-detail-section-heading">
            <span aria-hidden="true">i</span>
            <h2 className="fitician-display">{t("exerciseDetail.eyebrow")}</h2>
          </summary>
          <div className="exercise-detail-heading">
            <h1 className="fitician-display" dir={isEnglish ? "ltr" : "rtl"}>{name}</h1>
            <p className="exercise-detail-heading__secondary" dir={isEnglish ? "rtl" : "ltr"}>
              {secondaryName}
            </p>
            <dl className="exercise-detail-facts">
              <div>
                <dt>{t("exerciseDetail.bodyRegion")}</dt>
                <dd>{exercise.body_region === null ? t("catalog.needsReview") : t(`catalog.bodyRegion.${exercise.body_region}`)}</dd>
              </div>
              <div>
                <dt>{t("catalog.primaryMuscleLabel")}</dt>
                <dd>{exercise.primary_muscle === null ? t("catalog.needsReview") : t(`catalog.muscle.${exercise.primary_muscle}`)}</dd>
              </div>
              {exercise.muscle_focus !== null && (
                <div>
                  <dt>{t("catalog.muscleFocusLabel")}</dt>
                  <dd>{t(`catalog.muscleFocus.${exercise.muscle_focus}`)}</dd>
                </div>
              )}
              {labels.length > 0 && (
                <div>
                  <dt>{t("exerciseDetail.labels")}</dt>
                  <dd>{labels.map((label) => t(`catalog.label.${label}`)).join(t("catalog.listSeparator"))}</dd>
                </div>
              )}
              <div>
                <dt>{t("exerciseDetail.secondaryMuscles")}</dt>
                <dd>
                  {secondaryMuscles.length > 0
                    ? secondaryMuscles.join(t("catalog.listSeparator"))
                    : t("exerciseDetail.none")}
                </dd>
              </div>
              <div>
                <dt>{t("catalog.equipmentLabel")}</dt>
                <dd>{equipmentNames.join(t("catalog.listSeparator"))}</dd>
              </div>
              <div>
                <dt>{t("catalog.difficultyLabel")}</dt>
                <dd>{t(`catalog.difficulty.${exercise.difficulty}`)}</dd>
              </div>
            </dl>
          </div>
        </details>

        <details open={publicMode || undefined} className="exercise-detail-accordion exercise-instructions">
          <summary className="exercise-detail-section-heading">
            <span aria-hidden="true">✓</span>
            <h2 id="instructions-heading" className="fitician-display">{t("exerciseDetail.instructionsTitle")}</h2>
          </summary>
          <ol>
            {instructions.map((instruction) => (
              <li key={instruction}>{instruction}</li>
            ))}
          </ol>
        </details>

        <details open={publicMode || undefined} className="exercise-detail-accordion exercise-safety">
          <summary className="exercise-detail-section-heading">
            <span aria-hidden="true">!</span>
            <h2 id="safety-heading" className="fitician-display">{t("exerciseDetail.safetyTitle")}</h2>
          </summary>
          <ul>
            {safetyNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </details>

        <ExerciseLink publicMode={publicMode} className="exercise-detail-back" to={catalogPath}>
          {t("exerciseDetail.backToCatalog")}
          <span aria-hidden="true">←</span>
        </ExerciseLink>
      </article>
    </>
  );
}

