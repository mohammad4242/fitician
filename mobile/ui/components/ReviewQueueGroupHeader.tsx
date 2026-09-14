import {
  formatPersianDate,
  reviewQueueWeekLabel,
  type RecencyQueueGroup,
} from "@fitician/core";
import { StyleSheet, Text, View } from "react-native";

import { RTL_LAYOUT, RTL_TEXT } from "../rtl";
import { fiticianTokens } from "../tokens";

export type ReviewQueueGroupHeaderProps = {
  readonly group: RecencyQueueGroup<unknown>;
};

export function ReviewQueueGroupHeader({ group }: ReviewQueueGroupHeaderProps) {
  const title = group.kind === "day" ? "امروز" : reviewQueueWeekLabel(group.weekOffset, "fa");
  const dateRange = group.kind === "day"
    ? formatPersianDate(group.date)
    : `${formatPersianDate(group.startDate)} تا ${formatPersianDate(group.endDate)}`;

  return (
    <View style={[styles.container, RTL_LAYOUT]}>
      <View style={styles.copy}>
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
        <Text style={styles.date}>{dateRange}</Text>
      </View>
    </View>
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
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
    width: "100%",
  },
  copy: {
    gap: fiticianTokens.spacing[1],
    minWidth: 0,
  },
  date: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    lineHeight: 20,
  },
  title: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    lineHeight: 24,
  },
});
