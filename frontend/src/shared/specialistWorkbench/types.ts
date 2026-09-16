import type { ReactNode } from "react";

export type SpecialistRole = "coach" | "physician";
export type SpecialistSection = "dashboard" | "queue" | "mine" | "history";
export type SpecialistStatusContext = SpecialistRole;
export type SpecialistStatusTone = "neutral" | "attention" | "review" | "success" | "warning" | "danger";

export type SpecialistNavCount = Partial<Record<SpecialistSection, number>>;

export type SpecialistStat = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: SpecialistStatusTone;
};

export type SpecialistSortOption = {
  label: string;
  value: string;
};

export type SpecialistCaseHeaderMeta = {
  label: string;
  value: ReactNode;
};
