import { useThemeStyles } from "../theme/ThemeProvider";
import type { FiticianTokens } from "../tokens";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";


export interface BrandMarkProps {
  readonly accessibilityLabel?: string;
  readonly compact?: boolean;
  readonly label: string;
  readonly onPress?: () => void;
  readonly testID?: string;
}

export function BrandMark({ accessibilityLabel, compact = false, label, onPress, testID }: BrandMarkProps) {
  const styles = useThemeStyles(createStyles);

  const content = (
    <>
      <Image
        accessible={false}
        accessibilityIgnoresInvertColors
        source={require("../../assets/branding/fitician-brand.png")}
        resizeMode="contain"
        style={[styles.image, compact && styles.compactImage]}
        testID={testID ? `${testID}-image` : undefined}
      />
      <Text style={[styles.label, compact && styles.compactLabel]}>{label}</Text>
    </>
  );

  if (onPress !== undefined) {
    return (
      <Pressable
        accessibilityLabel={accessibilityLabel ?? label}
        accessibilityRole="link"
        onPress={onPress}
        style={styles.mark}
        testID={testID}
      >
        {content}
      </Pressable>
    );
  }

  return (
    <View accessible accessibilityLabel={accessibilityLabel ?? label} style={styles.mark} testID={testID}>
      {content}
    </View>
  );
}

const createStyles = (fiticianTokens: FiticianTokens) => (StyleSheet.create({
  compactImage: {
    height: 28,
    width: 28,
  },
  compactLabel: {
    fontSize: 16,
  },
  image: {
    height: 38,
    width: 38,
  },
  label: {
    color: fiticianTokens.colors.mist,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 22,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    writingDirection: "rtl",
  },
  mark: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    minWidth: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: 4,
  },
}));
