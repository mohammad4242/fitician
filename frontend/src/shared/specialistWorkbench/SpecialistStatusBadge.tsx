import type { SpecialistStatusContext, SpecialistStatusTone } from "./types";

import "./specialistWorkbench.css";

type SpecialistStatusBadgeProps = {
  readonly attention?: boolean;
  readonly className?: string;
  readonly context: SpecialistStatusContext;
  readonly fa: boolean;
  readonly status: string | null | undefined;
};

type StatusPresentation = {
  label: [string, string];
  tone: SpecialistStatusTone;
};

const sharedStatus: Record<string, Omit<StatusPresentation, "label"> & { label: [string, string] }> = {
  pending: { label: ["در انتظار بررسی", "Waiting for review"], tone: "warning" },
  claimed: { label: ["در حال بررسی", "In review"], tone: "review" },
  in_review: { label: ["در حال بررسی", "In review"], tone: "review" },
  approved: { label: ["تأییدشده", "Approved"], tone: "success" },
  awaiting_member_acceptance: { label: ["در انتظار تأیید کاربر", "Awaiting member approval"], tone: "warning" },
  active: { label: ["فعال", "Active"], tone: "success" },
  above_applicable_limit: { label: ["بالاتر از حد مجاز", "Above applicable limit"], tone: "danger" },
  above_preferred: { label: ["بالاتر از مقدار مطلوب", "Above preferred"], tone: "warning" },
  adequate: { label: ["کافی", "Adequate"], tone: "success" },
  below_preferred: { label: ["پایین‌تر از مقدار مطلوب", "Below preferred"], tone: "warning" },
  cancelled: { label: ["لغوشده", "Cancelled"], tone: "danger" },
  completed: { label: ["تکمیل‌شده", "Completed"], tone: "success" },
  data_incomplete: { label: ["داده ناقص", "Data incomplete"], tone: "warning" },
  discontinued: { label: ["قطع‌شده", "Discontinued"], tone: "danger" },
  fresh: { label: ["به‌روز", "Fresh"], tone: "success" },
  superseded: { label: ["نسخه جایگزین‌شده", "Superseded version"], tone: "neutral" },
  member_changes_requested: { label: ["درخواست اصلاح کاربر", "Member requested changes"], tone: "attention" },
  prescribed: { label: ["تجویزشده", "Prescribed"], tone: "review" },
  rejected: { label: ["ردشده", "Rejected"], tone: "danger" },
  requires_follow_up: { label: ["نیازمند پیگیری", "Needs follow-up"], tone: "attention" },
  reviewed: { label: ["بررسی‌شده", "Reviewed"], tone: "success" },
  uploaded: { label: ["بارگذاری‌شده", "Uploaded"], tone: "neutral" },
  within_budget: { label: ["در محدوده بودجه", "Within budget"], tone: "success" },
  over_budget: { label: ["بیشتر از بودجه", "Over budget"], tone: "danger" },
};

function getPresentation(status: string | null | undefined, context: SpecialistStatusContext): StatusPresentation {
  if (status === "rejected") {
    return context === "coach"
      ? { label: ["برگشت برای اصلاح", "Return for correction"], tone: "danger" }
      : { label: ["ردشده", "Rejected"], tone: "danger" };
  }
  return sharedStatus[status ?? ""] ?? {
    label: ["وضعیت پرونده", "Case status"],
    tone: "neutral",
  };
}

export function SpecialistStatusBadge({ attention = false, className, context, fa, status }: SpecialistStatusBadgeProps) {
  const presentation = getPresentation(status, context);
  const classes = [
    "specialist-status-badge",
    `specialist-status-badge--${presentation.tone}`,
    attention && "is-attention",
    className,
  ].filter(Boolean).join(" ");
  const label = presentation.label[fa ? 0 : 1];

  return (
    <span className={classes} data-tone={presentation.tone}>
      <span aria-hidden="true" className="specialist-status-badge__dot" />
      <span>{label}</span>
      {attention ? <small>{fa ? "نیازمند توجه" : "Needs attention"}</small> : null}
    </span>
  );
}
