import {
  formatIsoDate,
  formatPersianDate,
  formatPersianDateWithWeekday,
  reviewQueueWeekLabel,
  type RecencyQueueGroup,
} from "@fitician/core";

import "./reviewQueueGroupHeader.css";

type ReviewQueueGroupHeaderProps = {
  readonly count: number;
  readonly fa: boolean;
  readonly group: RecencyQueueGroup<unknown>;
  readonly headingId: string;
};

export function ReviewQueueGroupHeader({ count, fa, group, headingId }: ReviewQueueGroupHeaderProps) {
  const title = group.kind === "day"
    ? fa ? "امروز" : "Today"
    : reviewQueueWeekLabel(group.weekOffset, fa ? "fa" : "en");
  const dateRange = group.kind === "day"
    ? fa ? formatPersianDateWithWeekday(group.date) : formatIsoDate(group.date, "en-US")
    : fa
      ? `${formatPersianDate(group.startDate)} تا ${formatPersianDate(group.endDate)}`
      : `${formatIsoDate(group.startDate, "en-US")} – ${formatIsoDate(group.endDate, "en-US")}`;

  return (
    <header
      className="review-queue-group-header"
      data-queue-group-header="true"
      data-week-offset={group.kind === "week" ? group.weekOffset : undefined}
    >
      <div className="review-queue-group-header__copy">
        <h3 id={headingId}>{title}</h3>
        <p>{dateRange}</p>
      </div>
      <span className="review-queue-group-header__count">{count.toLocaleString(fa ? "fa-IR" : "en-US")}</span>
    </header>
  );
}
