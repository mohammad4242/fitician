import type { ReactNode } from "react";

import { formatTehranDateTime, formatTehranDateTimeForLocale } from "@fitician/core";

import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import {
  SpecialistStatusBadge,
  SpecialistStatsGrid,
} from "../../shared/specialistWorkbench";
import type { SpecialistSection, SpecialistStat } from "../../shared/specialistWorkbench";
import type { PhysicianReviewQueueItem } from "./api";

type PhysicianDashboardProps = {
  readonly approved: readonly PhysicianReviewQueueItem[];
  readonly claimed: readonly PhysicianReviewQueueItem[];
  readonly fa: boolean;
  readonly onOpenCase: (item: PhysicianReviewQueueItem, sourceView: "pending" | "claimed" | "approved") => void;
  readonly onSectionChange: (section: SpecialistSection) => void;
  readonly pending: readonly PhysicianReviewQueueItem[];
};

export function PhysicianDashboard({
  approved,
  claimed,
  fa,
  onOpenCase,
  onSectionChange,
  pending,
}: PhysicianDashboardProps) {
  const attentionItems = [...pending, ...claimed]
    .filter((item, index, items) => items.findIndex((candidate) => candidate.review_id === item.review_id) === index)
    .sort((left, right) => Number(right.overdue) - Number(left.overdue)
      || right.priority - left.priority
      || Date.parse(left.requested_at) - Date.parse(right.requested_at))
    .slice(0, 7);
  const recentApproved = [...approved]
    .sort((left, right) => Date.parse(right.reviewed_at ?? right.requested_at) - Date.parse(left.reviewed_at ?? left.requested_at))
    .slice(0, 5);
  const approvedToday = approved.filter((item) => item.reviewed_at && isTodayInTehran(item.reviewed_at)).length;
  const attentionCount = [...pending, ...claimed]
    .filter((item, index, items) => item.overdue && items.findIndex((candidate) => candidate.review_id === item.review_id) === index)
    .length;

  const stats: SpecialistStat[] = [
    { label: fa ? "در انتظار بررسی" : "Waiting for review", value: formatCount(pending.length, fa), tone: "warning" },
    { label: fa ? "در حال بررسی من" : "In my review", value: formatCount(claimed.length, fa), tone: "review" },
    { label: fa ? "نیازمند توجه" : "Needs attention", value: formatCount(attentionCount, fa), tone: attentionCount > 0 ? "danger" : "neutral" },
    { label: fa ? "تأییدشده امروز" : "Approved today", value: formatCount(approvedToday, fa), tone: "success" },
  ];

  return (
    <div className="physician-dashboard" data-testid="physician-dashboard">
      <SpecialistStatsGrid stats={stats} />

      <DashboardSection
        actionLabel={fa ? "مشاهده صف بررسی" : "View review queue"}
        empty={fa ? "در حال حاضر پرونده‌ای نیازمند اقدام نیست." : "No cases need action right now."}
        hasItems={attentionItems.length > 0}
        onViewAll={() => onSectionChange("queue")}
        title={fa ? "نیاز به اقدام" : "Needs action"}
      >
        <ul className="physician-dashboard__case-list">
          {attentionItems.map((item) => (
            <DashboardCaseRow
              fa={fa}
              item={item}
              key={item.review_id}
              onOpen={() => onOpenCase(item, item.status === "pending" ? "pending" : "claimed")}
            />
          ))}
        </ul>
      </DashboardSection>

      <DashboardSection
        actionLabel={fa ? "مشاهده تاریخچه" : "View history"}
        empty={fa ? "هنوز پرونده تأییدشده‌ای ثبت نشده است." : "No approved cases yet."}
        hasItems={recentApproved.length > 0}
        onViewAll={() => onSectionChange("history")}
        title={fa ? "فعالیت اخیر" : "Recent activity"}
      >
        <ul className="physician-dashboard__case-list">
          {recentApproved.map((item) => (
            <DashboardCaseRow fa={fa} item={item} key={item.review_id} onOpen={() => onOpenCase(item, "approved")} />
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
  hasItems,
  onViewAll,
  title,
}: {
  readonly actionLabel: string;
  readonly children: ReactNode;
  readonly empty: string;
  readonly hasItems: boolean;
  readonly onViewAll: () => void;
  readonly title: string;
}) {
  return (
    <section className="physician-dashboard__section">
      <div className="physician-dashboard__section-heading">
        <h2>{title}</h2>
        <button onClick={onViewAll} type="button">{actionLabel}</button>
      </div>
      {hasItems ? children : <p className="physician-dashboard__empty">{empty}</p>}
    </section>
  );
}

function DashboardCaseRow({
  fa,
  item,
  onOpen,
}: {
  readonly fa: boolean;
  readonly item: PhysicianReviewQueueItem;
  readonly onOpen: () => void;
}) {
  const name = item.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");
  const isPending = item.status === "pending";

  return (
    <li className="physician-dashboard__case" data-testid="physician-dashboard-case">
      <ProfilePhotoAvatar label={name} size="sm" url={item.member_profile_photo_url} />
      <div>
        <strong>{name}</strong>
        <span>{fa ? "نسخه تغذیه" : "Nutrition plan"} · {fa ? `اولویت ${item.priority}` : `Priority ${item.priority}`}</span>
      </div>
      <div className="physician-dashboard__case-status">
        <SpecialistStatusBadge attention={item.overdue} context="physician" fa={fa} status={item.status} />
        {item.overdue ? <small>{fa ? "گذشته از موعد" : "Overdue"}</small> : null}
      </div>
      <small>{formatTimestamp(item.requested_at, fa)}</small>
      <button onClick={onOpen} type="button">{isPending ? fa ? "شروع بررسی" : "Start review" : fa ? "مشاهده پرونده" : "Open case"}</button>
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
