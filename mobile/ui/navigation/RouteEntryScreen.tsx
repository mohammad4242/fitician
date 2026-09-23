import { StyleSheet, Text, View } from "react-native";
import { type ReactNode } from "react";

import { BrandMark, Card } from "../components";
import { Screen } from "../layout";
import { fiticianTokens } from "../tokens";

export interface RouteEntryScreenProps {
  readonly children?: ReactNode;
  readonly description: string;
  readonly title: string;
}

export function RouteEntryScreen({ children, description, title }: RouteEntryScreenProps) {
  return (
    <Screen contentContainerStyle={styles.screen} contentWidth="reading" scroll={false}>
      <View style={styles.content}>
        <View style={styles.brandRow}>
          <BrandMark accessibilityLabel="فیتیشن" label="فیتیشن" testID="route-entry-brand-mark" />
        </View>
        <Card variant="hero" style={styles.hero}>
          <Text accessibilityRole="header" style={styles.title}>{title}</Text>
          <Text style={styles.description}>{description}</Text>
          {children}
        </Card>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  brandRow: {
    alignItems: "center",
    flexDirection: "row",
  },
  content: {
    gap: fiticianTokens.spacing[3],
    maxWidth: fiticianTokens.layout.readingMaxWidth,
    width: "100%",
  },
  description: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    lineHeight: 28,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  hero: {
    gap: fiticianTokens.spacing[4],
    padding: fiticianTokens.spacing[5],
  },
  screen: {
    justifyContent: "center",
  },
  title: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h1,
    lineHeight: 40,
    textAlign: "auto",
    writingDirection: "rtl",
  },
});
