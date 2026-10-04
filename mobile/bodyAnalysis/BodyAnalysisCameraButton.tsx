import { useThemeTokens, useThemeStyles } from "../ui/theme/ThemeProvider";
import type { FiticianTokens } from "../ui/tokens";
import { Pressable, StyleSheet, Text } from "react-native";

import { AppIcon } from "../ui/components";

export function BodyAnalysisCameraButton({
  disabled = false,
  label,
  onPress,
}: {
  readonly disabled?: boolean;
  readonly label: string;
  readonly onPress: () => void;
}) {
  const fiticianTokens = useThemeTokens();
  const styles = useThemeStyles(createStyles);

  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.button, disabled && styles.disabled, pressed && !disabled && styles.pressed]}
    >
      <Text style={styles.label}>{label}</Text>
      <AppIcon color={fiticianTokens.colors.onAccent} name="camera" size={20} />
    </Pressable>
  );
}

const createStyles = (fiticianTokens: FiticianTokens) => (StyleSheet.create({
  button: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.aqua,
    borderColor: fiticianTokens.colors.aqua,
    borderRadius: fiticianTokens.radii.pill,
    borderWidth: 1,
    flexDirection: "row",
    gap: fiticianTokens.spacing[2],
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[4],
    paddingVertical: fiticianTokens.spacing[3],
    shadowColor: fiticianTokens.colors.aqua,
    shadowOpacity: 0.24,
    shadowRadius: 12,
  },
  disabled: {
    opacity: 0.48,
  },
  label: {
    color: fiticianTokens.colors.onAccent,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    lineHeight: 24,
    textAlign: "center",
    writingDirection: "rtl",
  },
  pressed: {
    opacity: 0.86,
    transform: [{ scale: fiticianTokens.motion.pressedScale }],
  },
}));
