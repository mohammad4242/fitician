import { type ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  useWindowDimensions,
  type StyleProp,
  type ViewStyle,
  type ScrollViewProps,
} from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
  type Edges,
} from "react-native-safe-area-context";

import { getResponsiveLayout } from "../layoutMetrics";
import { RTL_LAYOUT } from "../rtl";
import { fiticianTokens } from "../tokens";
import { KeyboardFocusScrollView } from "./KeyboardFocusScrollView";

export type ScreenContentWidth = "content" | "full" | "reading";

export interface ScreenProps {
  readonly children: ReactNode;
  readonly contentContainerStyle?: StyleProp<ViewStyle>;
  readonly contentWidth?: ScreenContentWidth;
  readonly edges?: Edges;
  readonly keyboardAware?: boolean;
  readonly keyboardFocusAware?: boolean;
  readonly keyboardDismissMode?: ScrollViewProps["keyboardDismissMode"];
  readonly keyboardVerticalOffset?: number;
  readonly scroll?: boolean;
  readonly style?: StyleProp<ViewStyle>;
}

export function Screen({
  children,
  contentContainerStyle,
  contentWidth = "content",
  edges = ["top", "bottom"],
  keyboardAware = true,
  keyboardFocusAware = false,
  keyboardDismissMode = "on-drag",
  keyboardVerticalOffset,
  scroll = true,
  style,
}: ScreenProps) {
  const { height, width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const responsive = getResponsiveLayout(width, height);
  const maxWidth = contentWidth === "full"
    ? undefined
    : contentWidth === "reading"
      ? responsive.readingMaxWidth
      : responsive.contentMaxWidth;
  const contentStyle = [
    styles.content,
    RTL_LAYOUT,
    {
      maxWidth,
      paddingHorizontal: responsive.horizontalPadding,
    },
    contentContainerStyle,
  ];
  const scrollProps = {
    contentContainerStyle: [styles.scrollContent, contentStyle],
    keyboardDismissMode,
    keyboardShouldPersistTaps: "handled" as const,
    showsVerticalScrollIndicator: false,
    style: RTL_LAYOUT,
  };
  const body = scroll && keyboardAware && keyboardFocusAware ? (
    <KeyboardFocusScrollView
      {...scrollProps}
      keyboardOffset={(keyboardVerticalOffset ?? insets.top) + fiticianTokens.spacing[4]}
    >
      {children}
    </KeyboardFocusScrollView>
  ) : scroll ? (
    <ScrollView
      {...scrollProps}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={contentStyle}>{children}</View>
  );

  return (
    <SafeAreaView edges={edges} style={[styles.safeArea, RTL_LAYOUT, style]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        enabled={keyboardAware}
        keyboardVerticalOffset={keyboardVerticalOffset ?? insets.top}
        style={[styles.keyboard, RTL_LAYOUT]}
      >
        {body}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    alignItems: "stretch",
    alignSelf: "center",
    flexGrow: 1,
    width: "100%",
  },
  keyboard: {
    flex: 1,
  },
  safeArea: {
    backgroundColor: fiticianTokens.colors.canvas,
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
});
