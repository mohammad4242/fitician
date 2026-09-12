import type { QuotaStatus } from "@fitician/core/entitlements";

export type BodyAnalysisAccessState = "allowed" | "loading" | "missing" | "quota_exhausted";

export function resolveBodyAnalysisAccessState(
  loading: boolean,
  hasEntitlement: boolean,
  quota: QuotaStatus | null,
): BodyAnalysisAccessState {
  if (loading) return "loading";
  if (!hasEntitlement) return "missing";
  if (quota !== null && quota.remaining <= 0) return "quota_exhausted";
  return "allowed";
}

export function bodyAnalysisAccessMessage(
  state: BodyAnalysisAccessState,
  quota: QuotaStatus | null,
): string {
  if (state === "loading") return "در حال بررسی دسترسی تحلیل بدن هستیم.";
  if (state === "missing") return "برای شروع تحلیل بدن، دسترسی فعال لازم است.";
  if (state === "quota_exhausted") {
    const resetAt = quota === null ? null : formatResetAt(quota.reset_at);
    return resetAt === null
      ? "سهم هفتگی تحلیل بدن مصرف شده است."
      : `سهم هفتگی تحلیل بدن مصرف شده است؛ دسترسی بعدی از ${resetAt} ممکن است.`;
  }
  return "";
}

function formatResetAt(value: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
