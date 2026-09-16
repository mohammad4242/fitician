import { Children, isValidElement, type ReactNode } from "react";

import { formatTehranDateTime, formatTehranDateTimeForLocale } from "@fitician/core";

import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import {
  SpecialistStatusBadge,
  SpecialistStatsGrid,
} from "../../shared/specialistWorkbench";
import type { SpecialistSection, SpecialistStat } from "../../shared/specialistWorkbench";
import type { WorkoutReviewQueueItem } from "./types";

type CoachDashboardProps = {
  readonly approved: readonly WorkoutReviewQueueItem[];
  readonly fa: boolean;
  readonly mine: readonly WorkoutReviewQueueItem[];
  readonly onOpenCase: (item: WorkoutReviewQueueItem, sourceView: "pending" | "mine" | "approved") => void;
  readonly onSectionChange: (section: SpecialistSection) => void;
  readonly pending: readonly WorkoutReviewQueueItem[];
};

export function CoachDashboard({
  approved,
  fa,
  mine,
  onOpenCase,
  onSectionChange,
  pending,
}: CoachDashboardProps) {
  const activeMine = mine.filter((item) => item.status === "claimed" || item.status === "member_changes_requested");
  const actionItems = [...activeMine, ...pending]
    .filter((item, index, items) => items.findIndex((candidate) => candidate.id === item.id) === index)
    .sort((left, right) => {
      const leftPriority = activeMine.some((item) => item.id === left.id) ? 0 : 1;
      const rightPriority = activeMine.some((item) => item.id === right.id) ? 0 : 1;
      return leftPriority - rightPriority || Date.parse(left.created_at) - Date.parse(right.created_at);
    })
    .slice(0, 7);
  const recentApproved = [...approved]
    .sort((left, right) => Date.parse(right.approved_at ?? right.created_at) - Date.parse(left.approved_at ?? left.created_at))
    .slice(0, 5);
  const approvedToday = approved.filter((item) => item.approved_at && isTodayInTehran(item.approved_at)).length;
  const oldestPending = [...pending].sort((left, right) => Date.parse(left.created_at) - Date.parse(right.created_at))[0];

  const stats: SpecialistStat[] = [
    { label: fa ? "در انتظار بررسی" : "Waiting for review", value: formatCount(pending.length, fa), tone: "warning" },
    { label: fa ? "در حال بررسی من" : "In my review", value: formatCount(activeMine.length, fa), tone: "review" },
    { label: fa ? "تأییدشده امروز" : "Approved today", value: formatCount(approvedToday, fa), tone: "success" },
    {
      label: fa ? "قدیمی‌ترین پرونده در انتظار" : "Oldest waiting case",
      value: oldestPending ? formatTimestamp(oldestPending.created_at, fa) : fa ? "—" : "—",
      hint: fa ? "بر اساس زمان ارسال" : "Based on submitted time",
      tone: "neutral",
    },
  ];

  return (
    <div className="coach-dashboard" data-testid="coach-dashboard">
      <SpecialistStatsGrid stats={stats} />

      <DashboardSection
        actionLabel={fa ? "مشاهده صف بررسی" : "View review queue"}
        empty={fa ? "در حال حاضر پرونده‌ای نیازمند اقدام نیست." : "No cases need action right now."}
        onViewAll={() => onSectionChange("queue")}
        title={fa ? "نیاز به اقدام" : "Needs action"}
      >
        <ul className="coach-dashboard__case-list">
          {actionItems.map((item) => (
            <DashboardCaseRow fa={fa} item={item} key={item.id} onOpen={() => onOpenCase(item, item.status === "pending" ? "pending" : "mine")} />
          ))}
        </ul>
      </DashboardSection>

      <DashboardSection
        actionLabel={fa ? "مشاهده تاریخچه" : "View history"}
        empty={fa ? "هنوز پرونده تأییدشده‌ای ثبت نشده است." : "No approved cases yet."}
        onViewAll={() => onSectionChange("history")}
        title={fa ? "فعالیت اخیر" : "Recent activity"}
      >
        <ul className="coach-dashboard__case-list">
          {recentApproved.map((item) => (
            <DashboardCaseRow fa={fa} item={item} key={item.id} onOpen={() => onOpenCase(item, "approved")} />
          ))}
        </ul>
      </DashboardSection>
    </div>
  );
}

function DashboardSection({
  actionLabel,
  children,
  empty,
  onViewAll,
  title,
}: {
  readonly actionLabel: string;
      readonly children: ReactNode;
  readonly empty: string;
  readonly onViewAll: () => void;
  readonly title: string;
}) {
  const hasItems = Children.count(children) > 0 && Children.toArray(children).some((child) => {
    return isValidElement<{ children?: ReactNode }>(child) && Children.count(child.props.children) > 0;
  });

  return (
    <section className="coach-dashboard__section">
      <div className="coach-dashboard__section-heading">
        <h2>{title}</h2>
        <button type="button" onClick={onViewAll}>{actionLabel}</button>
      </div>
      {hasItems ? children : <p className="coach-dashboard__empty">{empty}</p>}
    </section>
  );
}

function DashboardCaseRow({
  fa,
  item,
  onOpen,
}: {
  readonly fa: boolean;
  readonly item: WorkoutReviewQueueItem;
  readonly onOpen: () => void;
}) {
  const name = item.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");
  return (
    <li className="coach-dashboard__case" data-testid="coach-dashboard-case">
      <ProfilePhotoAvatar label={name} size="sm" url={item.member_profile_photo_url} />
      <div>
        <strong>{name}</strong>
        <span>{humanize(item.fitness_goal, fa)} · {humanize(item.experience_level, fa)}</span>
      </div>
      <SpecialistStatusBadge context="coach" fa={fa} status={item.status} />
      <button type="button" onClick={onOpen}>{item.status === "pending" ? fa ? "شروع بازبینی" : "Start review" : fa ? "مشاهده پرونده" : "Open case"}</button>
    </li>
  );
}

function formatCount(value: number, fa: boolean) {
  return value.toLocaleString(fa ? "fa-IR" : "en-US");
}

function formatTimestamp(value: string, fa: boolean) {
  return fa ? formatTehranDateTime(value) : formatTehranDateTimeForLocale(value, "en-US");
}

function isTodayInTehran(value: string) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Tehran",
    year: "numeric",
  });
  return formatter.format(new Date(value)) === formatter.format(new Date());
}

function humanize(value: string | null, fa: boolean) {
  if (!value) return fa ? "ثبت نشده" : "Not provided";
  const labels: Record<string, [string, string]> = {
    build_muscle: ["عضله‌سازی", "Build muscle"],
    lose_weight: ["کاهش وزن", "Lose weight"],
    beginner: ["مبتدی", "Beginner"],
    intermediate: ["متوسط", "Intermediate"],
    advanced: ["پیشرفته", "Advanced"],
  };
  return labels[value]?.[fa ? 0 : 1] ?? value.replaceAll("_", " ");
}
