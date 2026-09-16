import { useMemo, useState } from "react";

import { formatTehranDateTime, formatTehranDateTimeForLocale } from "@fitician/core";

import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import {
  SpecialistCaseList,
  SpecialistStatusBadge,
} from "../../shared/specialistWorkbench";
import type { SpecialistSortOption } from "../../shared/specialistWorkbench";
import type { WorkoutReviewQueueItem, WorkoutReviewQueueView } from "./types";

type CoachReviewQueueProps = {
  readonly busy: boolean;
  readonly fa: boolean;
  readonly items: readonly WorkoutReviewQueueItem[];
  readonly loading: boolean;
  readonly onOpenReview: (item: WorkoutReviewQueueItem) => void;
  readonly view: WorkoutReviewQueueView;
};

export function CoachReviewQueue({ busy, fa, items, loading, onOpenReview, view }: CoachReviewQueueProps) {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const sortOptions: SpecialistSortOption[] = [
    { label: fa ? "جدیدترین" : "Newest", value: "newest" },
    { label: fa ? "قدیمی‌ترین" : "Oldest", value: "oldest" },
  ];
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase(fa ? "fa-IR" : "en-US");
    return [...items]
      .filter((item) => (item.member_display_name ?? "").toLocaleLowerCase(fa ? "fa-IR" : "en-US").includes(query))
      .sort((left, right) => {
        const leftDate = Date.parse(view === "approved" ? left.approved_at ?? left.created_at : left.created_at);
        const rightDate = Date.parse(view === "approved" ? right.approved_at ?? right.created_at : right.created_at);
        return sort === "newest" ? rightDate - leftDate : leftDate - rightDate;
      });
  }, [fa, items, search, sort, view]);

  return (
    <div className="coach-review-queue-panel" data-testid="coach-review-queue">
      <div className="coach-review-queue-panel__heading">
        <div>
          <p className="coach-review-queue-panel__eyebrow">{fa ? "تمرکز روی پرونده‌های قابل اقدام" : "Focus on actionable cases"}</p>
          <h2>{queueHeading(view, fa)}</h2>
        </div>
        <span className="coach-review-queue-panel__count">{formatCount(items.length, fa)}</span>
      </div>
      <SpecialistCaseList
        emptyDescription={fa ? "با تغییر جست‌وجو یا بازگشت در زمان دیگری دوباره بررسی کن." : "Adjust the search or check again later."}
        emptyTitle={emptyTitle(view, fa)}
        fa={fa}
        items={filteredItems}
        loading={loading}
        loadingLabel={fa ? "در حال دریافت پرونده‌ها…" : "Loading cases…"}
        onSearchChange={setSearch}
        onSortChange={(value) => setSort(value as "newest" | "oldest")}
        renderItem={(item) => <CoachCaseRow busy={busy} fa={fa} item={item} key={item.id} onOpen={() => onOpenReview(item)} view={view} />}
        searchLabel={fa ? "جست‌وجوی نام کاربر" : "Search member name"}
        searchPlaceholder={fa ? "مثلاً محمد" : "e.g. Mohammad"}
        searchValue={search}
        sortLabel={fa ? "مرتب‌سازی" : "Sort"}
        sortOptions={sortOptions}
        sortValue={sort}
      />
    </div>
  );
}

function CoachCaseRow({
  busy,
  fa,
  item,
  onOpen,
  view,
}: {
  readonly busy: boolean;
  readonly fa: boolean;
  readonly item: WorkoutReviewQueueItem;
  readonly onOpen: () => void;
  readonly view: WorkoutReviewQueueView;
}) {
  const name = item.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");
  const timestamp = view === "approved" ? item.approved_at ?? item.created_at : item.created_at;
  return (
    <li aria-label={name} className="coach-review-queue-row" data-case-id={item.id} data-testid="coach-review-case-row">
      <ProfilePhotoAvatar label={name} size="sm" url={item.member_profile_photo_url} />
      <div className="coach-review-queue-row__member">
        <strong>{name}</strong>
        <span>{humanize(item.fitness_goal, fa)} · {humanize(item.experience_level, fa)}</span>
      </div>
      <time dateTime={timestamp}>{formatTimestamp(timestamp, fa, view)}</time>
      <SpecialistStatusBadge context="coach" fa={fa} status={item.status} />
      <button disabled={busy} onClick={onOpen} type="button">
        {item.status === "pending" ? fa ? "شروع بازبینی" : "Start review" : fa ? "مشاهده پرونده" : "Open case"}
      </button>
    </li>
  );
}

function queueHeading(view: WorkoutReviewQueueView, fa: boolean) {
  if (view === "pending") return fa ? "صف بررسی" : "Review queue";
  if (view === "mine") return fa ? "پرونده‌های من" : "My cases";
  return fa ? "تاریخچه تأییدها" : "Approval history";
}

function emptyTitle(view: WorkoutReviewQueueView, fa: boolean) {
  if (view === "pending") return fa ? "صف بررسی خالی است" : "Review queue is clear";
  if (view === "mine") return fa ? "پرونده‌ای در دست بررسی نیست" : "No cases are in your review";
  return fa ? "تاریخچه‌ای برای نمایش نیست" : "No history to show";
}

function formatCount(value: number, fa: boolean) {
  return value.toLocaleString(fa ? "fa-IR" : "en-US");
}

function formatTimestamp(value: string, fa: boolean, view: WorkoutReviewQueueView) {
  const prefix = view === "approved" ? (fa ? "تأییدشده: " : "Approved: ") : (fa ? "ارسال‌شده: " : "Sent: ");
  return `${prefix}${fa ? formatTehranDateTime(value) : formatTehranDateTimeForLocale(value, "en-US")}`;
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

