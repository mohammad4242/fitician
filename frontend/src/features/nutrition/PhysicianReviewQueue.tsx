import { useMemo, useState } from "react";

import { formatTehranDateTime, formatTehranDateTimeForLocale } from "@fitician/core";

import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import {
  SpecialistCaseList,
  SpecialistStatusBadge,
} from "../../shared/specialistWorkbench";
import type { SpecialistSortOption } from "../../shared/specialistWorkbench";
import type { PhysicianQueueView, PhysicianReviewQueueItem } from "./api";

type PhysicianReviewQueueProps = {
  readonly busy: boolean;
  readonly fa: boolean;
  readonly items: readonly PhysicianReviewQueueItem[];
  readonly loading: boolean;
  readonly onOpenReview: (item: PhysicianReviewQueueItem) => void;
  readonly selectedReviewId?: string;
  readonly view: PhysicianQueueView;
};

export function PhysicianReviewQueue({
  busy,
  fa,
  items,
  loading,
  onOpenReview,
  selectedReviewId,
  view,
}: PhysicianReviewQueueProps) {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"priority" | "oldest" | "newest">("priority");
  const sortOptions: SpecialistSortOption[] = [
    { label: fa ? "اولویت" : "Priority", value: "priority" },
    { label: fa ? "قدیمی‌ترین" : "Oldest", value: "oldest" },
    { label: fa ? "جدیدترین" : "Newest", value: "newest" },
  ];
  const visibleItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase(fa ? "fa-IR" : "en-US");
    return items
      .filter((item) => (item.member_display_name ?? "").toLocaleLowerCase(fa ? "fa-IR" : "en-US").includes(query))
      .sort((left, right) => compareItems(left, right, sort));
  }, [fa, items, search, sort]);

  return (
    <div className="physician-review-queue-view" data-testid="physician-review-queue">
      <header className="physician-review-queue-view__header">
        <div>
          <p className="physician-review-queue-view__eyebrow">{fa ? "صف کاری" : "Work queue"}</p>
          <h2>{queueTitle(view, fa)}</h2>
        </div>
        <span>{formatCount(items.length, fa)} {fa ? "پرونده" : "cases"}</span>
      </header>
      <SpecialistCaseList
        emptyDescription={fa ? "با تغییر جست‌وجو یا انتخاب بخش دیگر ادامه بده." : "Try another search or choose a different section."}
        emptyTitle={fa ? "پرونده‌ای در این صف نیست" : "This queue is clear"}
        fa={fa}
        items={visibleItems}
        loading={loading}
        loadingLabel={fa ? "در حال دریافت پرونده‌ها…" : "Loading cases…"}
        onSearchChange={setSearch}
        onSortChange={(value) => setSort(value as typeof sort)}
        renderItem={(item) => (
          <PhysicianQueueRow
            busy={busy}
            fa={fa}
            item={item}
            key={item.review_id}
            onOpen={() => onOpenReview(item)}
            selected={selectedReviewId === item.review_id}
          />
        )}
        searchLabel={fa ? "جست‌وجوی نام کاربر" : "Search member"}
        searchPlaceholder={fa ? "نام کاربر" : "Member name"}
        searchValue={search}
        sortLabel={fa ? "مرتب‌سازی" : "Sort cases"}
        sortOptions={sortOptions}
        sortValue={sort}
      />
    </div>
  );
}

function PhysicianQueueRow({
  busy,
  fa,
  item,
  onOpen,
  selected,
}: {
  readonly busy: boolean;
  readonly fa: boolean;
  readonly item: PhysicianReviewQueueItem;
  readonly onOpen: () => void;
  readonly selected: boolean;
}) {
  const name = item.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");
  const actionLabel = item.status === "pending"
    ? fa ? "شروع بررسی" : "Claim and view revision"
    : fa ? "مشاهده پرونده" : "View revision";

  return (
    <li className={`physician-review-queue-row${selected ? " is-selected" : ""}${item.overdue ? " is-overdue" : ""}`} data-testid="physician-review-case-row">
      <ProfilePhotoAvatar label={name} size="sm" url={item.member_profile_photo_url} />
      <div className="physician-review-queue-row__member">
        <strong>{name}</strong>
        <span>{fa ? "نسخه تغذیه" : "Nutrition plan"}</span>
      </div>
      <div className="physician-review-queue-row__time">
        <small>{fa ? "ارسال‌شده" : "Submitted"}</small>
        <span>{formatTimestamp(item.requested_at, fa)}</span>
      </div>
      <div className="physician-review-queue-row__priority">
        <span>{fa ? `اولویت ${item.priority}` : `Priority ${item.priority}`}</span>
        {item.overdue ? <small>{fa ? "گذشته از موعد" : "Overdue"}</small> : null}
      </div>
      <SpecialistStatusBadge attention={item.overdue} context="physician" fa={fa} status={item.status} />
      <button disabled={busy} onClick={onOpen} type="button">{actionLabel}</button>
    </li>
  );
}

function compareItems(left: PhysicianReviewQueueItem, right: PhysicianReviewQueueItem, sort: "priority" | "oldest" | "newest") {
  if (sort === "priority") {
    return Number(right.overdue) - Number(left.overdue)
      || right.priority - left.priority
      || Date.parse(left.requested_at) - Date.parse(right.requested_at);
  }
  const difference = Date.parse(left.requested_at) - Date.parse(right.requested_at);
  return sort === "oldest" ? difference : -difference;
}

function queueTitle(view: PhysicianQueueView, fa: boolean) {
  if (view === "claimed") return fa ? "پرونده‌های من" : "My cases";
  if (view === "approved") return fa ? "تاریخچه بررسی" : "Review history";
  return fa ? "صف بررسی" : "Review queue";
}

function formatCount(value: number, fa: boolean) {
  return value.toLocaleString(fa ? "fa-IR" : "en-US");
}

function formatTimestamp(value: string, fa: boolean) {
  return fa ? formatTehranDateTime(value) : formatTehranDateTimeForLocale(value, "en-US");
}
