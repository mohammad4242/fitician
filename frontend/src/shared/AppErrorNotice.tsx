import type {
  ErrorAudienceInput,
  ErrorContext,
  ErrorLocale,
  ErrorNetworkState,
} from "@fitician/core";

import { resolveWebAppError } from "./appError";

export interface AppErrorNoticeProps {
  readonly audience: ErrorAudienceInput;
  readonly context: ErrorContext;
  readonly error: unknown;
  readonly locale?: ErrorLocale;
  readonly networkState?: ErrorNetworkState;
  readonly onRetry?: () => void;
}

function technicalValue(value: string | number | null): string {
  return value === null ? "—" : String(value);
}

export function AppErrorNotice({
  audience,
  context,
  error,
  locale = "fa",
  networkState,
  onRetry,
}: AppErrorNoticeProps) {
  if (error === null || error === undefined) return null;
  const resolved = resolveWebAppError(error, { audience, context, locale, networkState });
  if (resolved.severity === "silent") return null;

  return (
    <div
      aria-live="assertive"
      className={`app-error-notice app-error-notice--${resolved.severity}`}
      data-error-code={resolved.code ?? "UNKNOWN_ERROR"}
      role="alert"
    >
      <strong>{resolved.title}</strong>
      <p>{resolved.message}</p>
      {resolved.fieldErrors.length > 0 ? (
        <ul>
          {resolved.fieldErrors.map((fieldError, index) => (
            <li key={`${fieldError.field ?? "field"}-${index}`}>{fieldError.message}</li>
          ))}
        </ul>
      ) : null}
      {resolved.action ? <p>{resolved.action}</p> : null}
      {onRetry && resolved.retryable ? (
        <button onClick={onRetry} type="button">
          {locale === "en" ? "Try again" : "دوباره تلاش کنید"}
        </button>
      ) : null}
      {resolved.showTechnicalDetails ? (
        <dl data-testid="app-error-technical-details">
          <div><dt>کد خطا</dt><dd>{technicalValue(resolved.code)}</dd></div>
          <div><dt>HTTP</dt><dd>{technicalValue(resolved.status)}</dd></div>
          <div><dt>شناسه پیگیری</dt><dd>{technicalValue(resolved.requestId)}</dd></div>
          <div><dt>قابل تلاش مجدد</dt><dd>{resolved.retryable ? "بله" : "خیر"}</dd></div>
          {Object.entries(resolved.meta).map(([key, value]) => (
            <div key={key}><dt>{key}</dt><dd>{JSON.stringify(value)}</dd></div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}
