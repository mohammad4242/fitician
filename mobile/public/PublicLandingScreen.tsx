import { useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "../ui/components/Button";
import { RTL_CENTER_TEXT } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";

export function PublicLandingScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <StatusBar style="light" />
      <Image
        accessible={false}
        resizeMode="cover"
        source={require("../assets/landing/pic_land.jpg")}
        style={StyleSheet.absoluteFill}
        testID="public-entry-background"
      />
      <View
        style={[
          styles.actions,
          {
            paddingBottom: insets.bottom + fiticianTokens.spacing[5],
            paddingLeft: insets.left,
            paddingRight: insets.right,
          },
        ]}
        testID="public-entry-actions"
      >
        <Button
          label="شروع کنیم"
          onPress={() => router.push("/public-onboarding")}
          style={styles.start}
          testID="public-entry-start"
        />
        <Pressable
          accessibilityLabel="ورود"
          accessibilityRole="button"
          onPress={() => router.push("/auth/sign-in")}
          style={({ pressed }) => [styles.signIn, pressed && styles.pressed]}
          testID="public-entry-sign-in"
        >
          <Text style={styles.prompt}>
            حساب داری؟ <Text style={styles.signInText}>ورود</Text>
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    backgroundColor: "#000000",
    flex: 1,
    justifyContent: "flex-end",
  },
  actions: {
    alignItems: "center",
    gap: fiticianTokens.spacing[4],
  },
  start: {
    maxWidth: 480,
    minHeight: 60,
    paddingHorizontal: fiticianTokens.spacing[6],
    width: "86%",
  },
  signIn: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[5],
    maxWidth: "100%",
  },
  prompt: {
    ...RTL_CENTER_TEXT,
    color: fiticianTokens.colors.mist,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    lineHeight: 24,
  },
  signInText: {
    color: fiticianTokens.colors.aqua,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    textDecorationLine: "underline",
  },
  pressed: {
    opacity: 0.86,
  },
});
