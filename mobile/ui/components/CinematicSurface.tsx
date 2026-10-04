import { useThemeStyles } from "../theme/ThemeProvider";
import type { FiticianTokens } from "../tokens";
import { type ReactNode } from "react";
import { StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from "react-native";

import { RTL_LAYOUT } from "../rtl";

export interface CinematicSurfaceProps extends Omit<ViewProps, "style"> {
  readonly accent?: boolean;
  readonly children: ReactNode;
  readonly style?: StyleProp<ViewStyle>;
  readonly variant?: "default" | "hero" | "quiet";
}

const createVariants = (fiticianTokens: FiticianTokens): Record<NonNullable<CinematicSurfaceProps["variant"]>, ViewStyle> => ({
  default: { backgroundColor: fiticianTokens.colors.surface },
  hero: { backgroundColor: fiticianTokens.colors.hero },
  quiet: { backgroundColor: fiticianTokens.colors.surfaceSubtle },
});

export function CinematicSurface({
  accent = false,
  children,
  style,
  variant = "default",
  ...viewProps
}: CinematicSurfaceProps) {
  const variants = useThemeStyles(createVariants);
  const styles = useThemeStyles(createStyles);

  return (
    <View {...viewProps} style={[styles.surface, RTL_LAYOUT, variants[variant], style]}>
      <View pointerEvents="none" style={styles.highlight} />
      <View pointerEvents="none" style={styles.ambient} />
      {accent ? <View pointerEvents="none" style={styles.signal} /> : null}
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const createStyles = (fiticianTokens: FiticianTokens) => (StyleSheet.create({
  ambient: {
    backgroundColor: fiticianTokens.colors.aquaAtmosphere,
    borderRadius: fiticianTokens.radii.pill,
    height: 160,
    opacity: 0.55,
    position: "absolute",
    right: -80,
    top: -92,
    width: 190,
  },
  content: {
    position: "relative",
    zIndex: 2,
  },
  highlight: {
    backgroundColor: fiticianTokens.colors.surfaceHighlight,
    height: 1,
    left: fiticianTokens.spacing[4],
    position: "absolute",
    right: fiticianTokens.spacing[4],
    top: 0,
  },
  signal: {
    backgroundColor: fiticianTokens.colors.aqua,
    borderRadius: fiticianTokens.radii.pill,
    height: 2,
    left: fiticianTokens.spacing[5],
    position: "absolute",
    top: 0,
    width: 52,
  },
  surface: {
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.extraLarge,
    borderWidth: 1,
    elevation: fiticianTokens.shadows.card.elevation,
    overflow: "hidden",
    shadowColor: fiticianTokens.shadows.card.color,
    shadowOffset: fiticianTokens.shadows.card.offset,
    shadowOpacity: fiticianTokens.shadows.card.opacity,
    shadowRadius: fiticianTokens.shadows.card.radius,
  },
}));
