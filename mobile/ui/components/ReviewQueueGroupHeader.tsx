import {
  formatPersianDate,
  reviewQueueWeekLabel,
  type RecencyQueueGroup,
} from "@fitician/core";
import type { ReactNode } from "react";
import { StyleSheet } from "react-native";

import { fiticianTokens } from "../tokens";
import { DisclosureCard } from "./DisclosureCard";

export type ReviewQueueGroupHeaderProps = {
  readonly children: ReactNode;
  readonly group: RecencyQueueGroup<unknown>;
};

export function ReviewQueueGroupHeader({ children, group }: ReviewQueueGroupHeaderProps) {
  const title = group.kind === "day" ? "امروز" : reviewQueueWeekLabel(group.weekOffset, "fa");
  const dateRange = group.kind === "day"
    ? formatPersianDate(group.date)
    : `${formatPersianDate(group.startDate)} تا ${formatPersianDate(group.endDate)}`;

  return (
    <DisclosureCard defaultExpanded={false} direction="rtl" summary={dateRange} title={title} style={styles.container}>
      {children}
    </DisclosureCard>
  );
}

const styles = StyleSheet.create({
  container: {
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.medium,
    borderRightColor: fiticianTokens.colors.aqua,
    borderRightWidth: 4,
    borderWidth: 1,
    backgroundColor: fiticianTokens.colors.surfaceTranslucent,
    width: "100%",
  },
});
