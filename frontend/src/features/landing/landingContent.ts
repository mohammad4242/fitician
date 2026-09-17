import heroFallback from "../../assets/landing/hero-strength-fallback.jpg";
import planFallback from "../../assets/landing/plan-focus-fallback.jpg";
import progressFallback from "../../assets/landing/progress-drive-fallback.jpg";
import { publicMediaUrl } from "../../shared/publicMedia";

export type LandingScene = {
  id: "strength" | "plan" | "progress";
  eyebrow: string;
  title: string;
  body: string;
  videoSrc: string;
  fallbackSrc: string;
  preload: "metadata" | "none";
};

export const landingScenes = [
  {
    id: "strength",
    eyebrow: "فیتیشن، مسیر شخصی تو",
    title: "از امروز، قوی‌تر.",
    body: "برنامه‌ای روشن برای شروعی که واقعاً ادامه پیدا می‌کند.",
    videoSrc: publicMediaUrl("public/landing/videos/hero-strength.mp4"),
    fallbackSrc: heroFallback,
    preload: "metadata",
  },
  {
    id: "plan",
    eyebrow: "تمرین، متناسب با تو",
    title: "بدون حدس، با برنامه.",
    body: "هر جلسه با هدف، زمان و سطح آمادگی تو هماهنگ می‌شود.",
    videoSrc: publicMediaUrl("public/landing/videos/plan-focus.mp4"),
    fallbackSrc: planFallback,
    preload: "none",
  },
  {
    id: "progress",
    eyebrow: "پیشرفت قابل دیدن",
    title: "هر تکرار، نزدیک‌تر.",
    body: "روندت را ببین، تمرینت را ادامه بده و نسخهٔ قوی‌تر خودت را بساز.",
    videoSrc: publicMediaUrl("public/landing/videos/progress-drive.mp4"),
    fallbackSrc: progressFallback,
    preload: "none",
  },
] as const satisfies readonly LandingScene[];
