import type { JsonObject } from "../transport";

export type ErrorAudience = "member" | "admin" | "coach" | "physician";
export type ErrorAudienceInput = ErrorAudience | "doctor";

export type ErrorContext =
  | "auth"
  | "profile"
  | "workout"
  | "workout_generation"
  | "nutrition"
  | "body_analysis"
  | "body_photo"
  | "billing"
  | "access"
  | "specialist_review"
  | "generic";

export type ErrorLocale = "fa" | "en";
export type ErrorNetworkState = "offline" | "online" | "unknown";
export type ErrorSeverity = "error" | "warning" | "info" | "silent";

export interface ResolvedFieldError {
  readonly field: string | null;
  readonly code: string;
  readonly message: string;
}

export interface ResolvedAppError {
  readonly title: string;
  readonly message: string;
  readonly action: string | null;
  readonly severity: ErrorSeverity;
  readonly retryable: boolean;
  readonly code: string | null;
  readonly status: number | null;
  readonly requestId: string | null;
  readonly fieldErrors: readonly ResolvedFieldError[];
  readonly meta: JsonObject;
  readonly showTechnicalDetails: boolean;
}

export interface ResolveAppErrorOptions {
  readonly audience: ErrorAudienceInput;
  readonly context: ErrorContext;
  readonly locale: ErrorLocale;
  readonly networkState?: ErrorNetworkState;
}

export interface LocalizedErrorCopy {
  readonly fa: string;
  readonly en: string;
}

export interface ErrorCatalogEntry {
  readonly title: LocalizedErrorCopy;
  readonly message: LocalizedErrorCopy;
  readonly action?: LocalizedErrorCopy;
  readonly audiences?: Partial<Record<ErrorAudience, Partial<{
    readonly title: LocalizedErrorCopy;
    readonly message: LocalizedErrorCopy;
    readonly action: LocalizedErrorCopy;
  }>>>;
}
