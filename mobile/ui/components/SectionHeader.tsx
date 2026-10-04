import { useThemeStyles } from "../theme/ThemeProvider";
import type { FiticianTokens } from "../tokens";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { RTL_LAYOUT, RTL_TEXT } from "../rtl";

export interface SectionHeaderProps {
  readonly actionLabel?: string;
  readonly onAction?: () => void;
  readonly title: string;
  readonly eyebrow?: string;
}

export function SectionHeader({ actionLabel, eyebrow, onAction, title }: SectionHeaderProps) {
  const styles = useThemeStyles(createStyles);

  return (
    <View style={[styles.container, RTL_LAYOUT]}>
      <View style={styles.copy}>
        {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
      </View>
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.action}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const createStyles = (fiticianTokens: FiticianTokens) => (StyleSheet.create({
  action: {
    alignItems: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    minWidth: fiticianTokens.layout.minimumTouchTarget,
    justifyContent: "center",
    paddingHorizontal: fiticianTokens.spacing[2],
  },
  actionText: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.accentInk,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  container: {
    alignItems: "center",
    flexDirection: "row",
    gap: fiticianTokens.spacing[2],
    justifyContent: "space-between",
  },
  copy: {
    alignItems: "stretch",
    flex: 1,
    gap: fiticianTokens.spacing[1],
    minWidth: 0,
  },
  eyebrow: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.accentInk,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  title: {
    ...RTL_TEXT,
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h2,
    lineHeight: 32,
  },
}));
