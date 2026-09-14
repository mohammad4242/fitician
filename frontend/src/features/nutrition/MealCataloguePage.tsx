import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import foodAccent from "../../assets/landing/food.webp";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { MemberHeaderMedia } from "../../shared/MemberHeaderMedia";
import { MealThumbnail } from "../../shared/MealThumbnail";
import { deleteAdminMeal, uploadAdminMealImage } from "../admin/api";
import { useAuth } from "../auth/AuthContext";
import {
  getMealCatalogue,
  type MealCatalogueCategory,
  type MealCatalogueItem,
  type MealCatalogueResponse,
} from "./api";
import "./mealCatalogue.css";

const CATEGORIES: MealCatalogueCategory[] = [
  "breakfast",
  "lunch",
  "post_workout",
  "snack",
  "dinner",
];

export function MealCataloguePage() {
  const { i18n, t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.is_admin === true;

  const [selectedCategory, setSelectedCategory] = useState<MealCatalogueCategory | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<"published" | "draft" | "all">("published");
  const [data, setData] = useState<MealCatalogueResponse | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [retry, setRetry] = useState(0);

  const [imageMeal, setImageMeal] = useState<MealCatalogueItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MealCatalogueItem | null>(null);
  const [deletingMealId, setDeletingMealId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<unknown>(null);
  const deleteTriggerRef = useRef<HTMLButtonElement | null>(null);

  const english = i18n.resolvedLanguage === "en";
  const number = new Intl.NumberFormat(english ? "en" : "fa-IR", { maximumFractionDigits: 1 });

  useEffect(() => {
    let active = true;
    setState("loading");
    void getMealCatalogue(selectedCategory, isAdmin ? statusFilter : undefined)
      .then((response) => {
        if (!active) return;
        setData(response);
        setLoadError(null);
        setState("ready");
      })
      .catch((cause: unknown) => {
        if (active) {
          setLoadError(cause);
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [selectedCategory, statusFilter, isAdmin, retry]);

  function openDeleteDialog(meal: MealCatalogueItem, trigger: HTMLButtonElement) {
    deleteTriggerRef.current = trigger;
    setDeleteError(null);
    setDeleteTarget(meal);
  }

  function closeDeleteDialog() {
    if (deletingMealId !== null) return;
    setDeleteTarget(null);
    setDeleteError(null);
    deleteTriggerRef.current?.focus();
  }

  async function handleDelete() {
    if (deleteTarget === null) return;
    const meal = deleteTarget;
    setDeletingMealId(meal.id);
    setDeleteError(null);
    try {
      await deleteAdminMeal(meal.id);
      setData((current) =>
        current === null
          ? current
          : {
              ...current,
              items: current.items.filter((item) => item.id !== meal.id),
            },
      );
      setDeleteTarget(null);
    } catch (cause: unknown) {
      setDeleteError(cause);
    } finally {
      setDeletingMealId(null);
    }
  }

  return (
    <div className="meal-catalogue-shell" dir={english ? "ltr" : "rtl"}>
      <MemberHeaderMedia className="member-page-background" imageSrc={foodAccent} />
      <main className="meal-catalogue-page fitician-page">
        <header className="meal-catalogue-hero">
          <p className="eyebrow eyebrow--accent">{t("mealCatalogue.eyebrow")}</p>
          <h1 className="fitician-display">{t("mealCatalogue.title")}</h1>
          <p className="meal-catalogue-description">{t("mealCatalogue.intro")}</p>
        </header>

        <div className="meal-catalogue-filters">
          <div className="meal-catalogue-filter-row">
            <span className="meal-catalogue-filter-label">{t("mealCatalogue.categoryFilter")}:</span>
            <nav
              className="meal-catalogue-tabs"
              aria-label={t("mealCatalogue.categoryFilter")}
              role="tablist"
            >
              <button
                aria-selected={selectedCategory === undefined}
                className={`meal-catalogue-chip ${selectedCategory === undefined ? "is-active" : ""}`}
                onClick={() => setSelectedCategory(undefined)}
                role="tab"
                type="button"
              >
                {t("mealCatalogue.allCategories")}
              </button>
              {CATEGORIES.map((category) => (
                <button
                  aria-selected={selectedCategory === category}
                  className={`meal-catalogue-chip ${selectedCategory === category ? "is-active" : ""}`}
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  role="tab"
                  type="button"
                >
                  {t(`mealCatalogue.categories.${category}`)}
                </button>
              ))}
            </nav>
          </div>

          {isAdmin && (
            <div className="meal-catalogue-filter-row">
              <span className="meal-catalogue-filter-label">{t("mealCatalogue.statusFilter")}:</span>
              <nav
                className="meal-catalogue-tabs"
                aria-label={t("mealCatalogue.statusFilter")}
                role="tablist"
              >
                {(["published", "draft", "all"] as const).map((status) => (
                  <button
                    aria-selected={statusFilter === status}
                    className={`meal-catalogue-chip ${statusFilter === status ? "is-active" : ""}`}
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    role="tab"
                    type="button"
                  >
                    {t(`mealCatalogue.statusFilterOptions.${status}`)}
                  </button>
                ))}
              </nav>
            </div>
          )}
        </div>

        {isAdmin && state === "ready" && (
          <div className="meal-catalogue-admin-bar">
            <Link
              className="meal-catalogue-add-btn"
              to={`/admin/nutrition-meals/new?category=${selectedCategory ?? "breakfast"}`}
            >
              {t("mealCatalogue.add")}
            </Link>
          </div>
        )}

        {state === "loading" && (
          <p className="meal-catalogue-state" role="status">
            {t("mealCatalogue.loading")}
          </p>
        )}

        {state === "error" && (
          <div className="meal-catalogue-state meal-catalogue-state--error">
            <AppErrorNotice audience={isAdmin ? "admin" : "member"} context="nutrition" error={loadError} locale={english ? "en" : "fa"} />
            <button type="button" onClick={() => setRetry((value) => value + 1)}>
              {t("mealCatalogue.retry")}
            </button>
          </div>
        )}

        {state === "ready" && data?.items.length === 0 && (
          <p className="meal-catalogue-state meal-catalogue-state--empty">
            {t("mealCatalogue.empty")}
          </p>
        )}

        {state === "ready" && data !== null && data.items.length > 0 && (
          <section
            aria-label={t("mealCatalogue.title")}
            className="meal-catalogue-list"
            role="list"
          >
            {data.items.map((meal) => {
              const name = english ? meal.name_en : meal.name_fa;
              return (
                <article className="admin-meal-card" key={meal.id} role="listitem">
                  <details className="admin-meal-card__disclosure">
                    <summary className="admin-meal-card__summary">
                      <div className="admin-meal-card__identity">
                        <MealThumbnail
                          alt={name}
                          className="admin-meal-card__image"
                          fallbackLabel={t("mealCatalogue.imageFallback", { name })}
                          imageUrl={meal.image_url}
                        />
                        <div>
                          <p className="eyebrow">
                            {meal.code ? `${meal.code} · ` : ""}
                            {meal.category ? t(`mealCatalogue.categories.${meal.category}`) : ""}
                          </p>
                          <h2>{name}</h2>
                        </div>
                      </div>
                      {meal.verification_status && (
                        <span className={`admin-meal-status admin-meal-status--${meal.verification_status}`}>
                          {t(`mealCatalogue.status.${meal.verification_status}`)}
                        </span>
                      )}
                    </summary>
                    <div className="admin-meal-card__details">
                      <ul className="admin-meal-ingredients">
                        {(meal.items ?? []).map((item) => (
                          <li key={item.food_id}>
                            <div>
                              <strong>{english ? item.food_name_en : item.food_name_fa}</strong>
                              <small>
                                {item.functional_role
                                  ? t(`mealCatalogue.roles.${item.functional_role}`) || item.functional_role
                                  : t("mealCatalogue.roles.none")}
                              </small>
                            </div>
                            <span>
                              {t("mealCatalogue.bounds", {
                                min: number.format(item.min_grams),
                                max: number.format(item.max_grams),
                              })}
                            </span>
                            <span>{item.is_required ? t("mealCatalogue.required") : t("mealCatalogue.optional")}</span>
                          </li>
                        ))}
                      </ul>
                      <footer>
                        {isAdmin ? (
                          <>
                            <Link
                              aria-label={t("mealCatalogue.editAria", { name })}
                              to={`/admin/nutrition-meals/${meal.id}/edit`}
                            >
                              {t("mealCatalogue.edit")}
                            </Link>
                            <button
                              aria-label={t("mealCatalogue.imageActionAria", {
                                action: t(meal.image_url ? "mealCatalogue.replaceImage" : "mealCatalogue.uploadImage"),
                                name,
                              })}
                              type="button"
                              onClick={() => setImageMeal(meal)}
                            >
                              {t(meal.image_url ? "mealCatalogue.replaceImage" : "mealCatalogue.uploadImage")}
                            </button>
                            <button
                              className="admin-meal-delete-button"
                              aria-label={t("mealCatalogue.deleteAria", { name })}
                              type="button"
                              onClick={(e) => openDeleteDialog(meal, e.currentTarget)}
                            >
                              {t("mealCatalogue.delete")}
                            </button>
                          </>
                        ) : null}
                        <span>{t("mealCatalogue.referenceNote")}</span>
                      </footer>
                    </div>
                  </details>
                </article>
              );
            })}
          </section>
        )}
      </main>

      {imageMeal && (
        <MealImageDialog
          meal={imageMeal}
          onClose={() => setImageMeal(null)}
          onSaved={(imageUrl) => {
            setData((current) =>
              current === null
                ? current
                : {
                    ...current,
                    items: current.items.map((meal) =>
                      meal.id === imageMeal.id ? { ...meal, image_url: imageUrl } : meal,
                    ),
                  },
            );
            setImageMeal(null);
          }}
        />
      )}

      {deleteTarget !== null && (
        <div
          className="meal-delete-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeDeleteDialog();
          }}
        >
          <section
            aria-describedby="meal-delete-description"
            aria-label={t("mealCatalogue.deleteDialogLabel")}
            aria-modal="true"
            className="meal-delete-dialog"
            role="dialog"
          >
            <span className="meal-delete-dialog__rail" aria-hidden="true" />
            <header>
              <div>
                <p className="eyebrow">{t("mealCatalogue.deleteEyebrow")}</p>
                <h2>{t("mealCatalogue.deleteDialogTitle")}</h2>
              </div>
              <button
                aria-label={t("mealCatalogue.closeImage")}
                type="button"
                onClick={closeDeleteDialog}
              >
                ×
              </button>
            </header>
            <p id="meal-delete-description" className="meal-delete-dialog__description">
              {t("mealCatalogue.deleteDialogBody", {
                name: english ? deleteTarget.name_en : deleteTarget.name_fa,
              })}
            </p>
            <AppErrorNotice audience="admin" context="nutrition" error={deleteError} locale={english ? "en" : "fa"} />
            <footer>
              <button
                autoFocus
                className="meal-delete-dialog__cancel"
                type="button"
                disabled={deletingMealId !== null}
                onClick={closeDeleteDialog}
              >
                {t("mealCatalogue.deleteCancel")}
              </button>
              <button
                className="meal-delete-dialog__confirm"
                type="button"
                disabled={deletingMealId !== null}
                onClick={() => void handleDelete()}
              >
                {deletingMealId !== null ? t("mealCatalogue.deleteBusy") : t("mealCatalogue.deleteConfirm")}
              </button>
            </footer>
          </section>
        </div>
      )}
    </div>
  );
}

function MealImageDialog({
  meal,
  onClose,
  onSaved,
}: {
  meal: MealCatalogueItem;
  onClose: () => void;
  onSaved: (imageUrl: string) => void;
}) {
  const { i18n, t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const name = i18n.resolvedLanguage === "en" ? meal.name_en : meal.name_fa;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await uploadAdminMealImage(meal.id, file);
      onSaved(saved.image_url);
    } catch (cause: unknown) {
      setError(cause);
      setSaving(false);
    }
  }

  return (
    <div
      className="admin-meal-image-dialog"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section aria-label={t("mealCatalogue.imageDialog", { name })} role="dialog" aria-modal="true">
        <header>
          <h2>{t(meal.image_url ? "mealCatalogue.replaceImage" : "mealCatalogue.uploadImage")}</h2>
          <button aria-label={t("mealCatalogue.closeImage")} type="button" onClick={onClose}>
            ×
          </button>
        </header>
        <p>{t("mealCatalogue.imageHint")}</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>
            {t("mealCatalogue.imageInput")}
            <input
              accept="image/gif,image/jpeg,image/png,image/webp"
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          {file && <small>{file.name}</small>}
          <AppErrorNotice audience="admin" context="nutrition" error={error} locale={i18n.resolvedLanguage === "en" ? "en" : "fa"} />
          <button disabled={saving || !file} type="submit">
            {saving ? t("mealCatalogue.savingImage") : t("mealCatalogue.saveImage")}
          </button>
        </form>
      </section>
    </div>
  );
}
