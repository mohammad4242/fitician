import { useRef } from "react";
import {
  progressTabs,
  progressTabLabel,
  type ProgressOverview,
  type ProgressTab,
} from "@fitician/core";
export function ProgressTabs({
  data,
  selected,
  language,
  onSelect,
}: {
  data: ProgressOverview | null;
  selected: ProgressTab;
  language: "fa" | "en";
  onSelect: (tab: ProgressTab) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const tabs = progressTabs(data);
  return (
    <div
      ref={ref}
      role="tablist"
      aria-label={language === "fa" ? "بخش‌های پیشرفت" : "Progress categories"}
      className="progress-tabs"
    >
      {tabs.map(({ id, disabled }, index) => (
        <button
          key={id}
          role="tab"
          id={`progress-tab-${id}`}
          aria-controls={`progress-panel-${id}`}
          aria-selected={selected === id}
          disabled={disabled}
          tabIndex={selected === id ? 0 : -1}
          onClick={() => onSelect(id)}
          onKeyDown={(e) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key))
              return;
            e.preventDefault();
            const step =
              (e.key === "ArrowRight" ? 1 : -1) * (language === "fa" ? -1 : 1);
            let next =
              e.key === "Home"
                ? 0
                : e.key === "End"
                  ? tabs.length - 1
                  : (index + step + tabs.length) % tabs.length;
            while (tabs[next].disabled)
              next = (next + step + tabs.length) % tabs.length;
            onSelect(tabs[next].id);
            const button =
              ref.current?.querySelectorAll<HTMLButtonElement>("button")[next];
            button?.focus();
            button?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
          }}
        >
          {progressTabLabel(id, language)}
        </button>
      ))}
    </div>
  );
}
