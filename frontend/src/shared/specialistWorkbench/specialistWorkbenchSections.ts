import type { SpecialistSection } from "./types";

export const specialistSections: SpecialistSection[] = ["dashboard", "queue", "mine", "history"];

const labels: Record<SpecialistSection, [string, string]> = {
  dashboard: ["داشبورد", "Dashboard"],
  queue: ["صف بررسی", "Review queue"],
  mine: ["پرونده‌های من", "My cases"],
  history: ["تاریخچه", "History"],
};

export function specialistSectionLabel(section: SpecialistSection, fa: boolean): string {
  return labels[section][fa ? 0 : 1];
}
