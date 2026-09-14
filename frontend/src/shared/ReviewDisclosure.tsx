import type { ReactNode } from "react";

import {
  reviewDisclosureDefaultExpanded,
  type ReviewDisclosureKey,
} from "@fitician/core";

import "./reviewDisclosure.css";

type ReviewDisclosureProps = {
  readonly children: ReactNode;
  readonly className?: string;
  readonly section: ReviewDisclosureKey;
  readonly summary?: string;
  readonly title: string;
};

export function ReviewDisclosure({
  children,
  className,
  section,
  summary,
  title,
}: ReviewDisclosureProps) {
  const expanded = reviewDisclosureDefaultExpanded(section);
  const classes = ["review-disclosure", className].filter(Boolean).join(" ");

  return (
    <details className={classes} data-review-disclosure={section} open={expanded}>
      <summary>
        <span className="review-disclosure__copy">
          <span className="review-disclosure__title">{title}</span>
          {summary ? <span className="review-disclosure__summary">{summary}</span> : null}
        </span>
      </summary>
      <div className="review-disclosure__body">{children}</div>
    </details>
  );
}
