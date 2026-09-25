import { AppIcon } from "../../shared/AppIcon";
import type { ProductMode } from "../profile/types";

export type OnboardingLanguage = "fa" | "en";

const modeCopy = {
  fa: {
    eyebrow: "شروع با مربی فیتیشن",
    title: "تو چه زمینه‌ای به کمک نیاز داری؟",
    training: "برنامه تمرینی",
    nutrition: "برنامه تغذیه",
    both: "تمرین و تغذیه",
    recommended: "پیشنهاد فیتیشن",
  },
  en: {
    eyebrow: "Start with your Fitician coach",
    title: "What would you like help with?",
    training: "Training plan",
    nutrition: "Nutrition plan",
    both: "Training and nutrition",
    recommended: "Fitician recommended",
  },
} as const;

export function ModeSelection({
  language,
  onChoose,
  disabled = false,
}: {
  language: OnboardingLanguage;
  onChoose: (mode: ProductMode) => void;
  disabled?: boolean;
}) {
  const text = modeCopy[language];
  const modes = [
    ["training", text.training, "dumbbell"],
    ["nutrition", text.nutrition, "nutrition"],
    ["both", text.both, "target"],
  ] as const;

  return (
    <section className="public-mode-selection">
      <p className="eyebrow eyebrow--accent">{text.eyebrow}</p>
      <h1 className="fitician-display">{text.title}</h1>
      <div className="product-mode-cards">
        {modes.map(([mode, title, icon]) => (
          <button
            key={mode}
            className={"product-mode-card mode-" + mode + (mode === "both" ? " is-recommended" : "")}
            type="button"
            aria-label={title}
            disabled={disabled}
            onClick={() => onChoose(mode)}
          >
            <span className="product-mode-card__icon" aria-hidden="true">
              <AppIcon name={icon} />
            </span>
            <span className="product-mode-card__content">
              <strong>{title}</strong>
              {mode === "both" && (
                <span className="product-mode-card__badge">{text.recommended}</span>
              )}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
