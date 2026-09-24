import { StyleSheet, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { NutritionCatalogueSection } from "../../../nutrition/NutritionCatalogueSection";
import { AppIcon } from "../../../ui/components";
import { Screen } from "../../../ui/layout";
import { RouteGuard } from "../../../ui/navigation/RouteGuards";
import { fiticianTokens } from "../../../ui/tokens";

export default function MemberMealCatalogueRoute() {
  return (
    <RouteGuard kind="member" requiredCapability="nutrition">
      <View style={styles.root}>
        <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.nutritionBackdrop]}>
          <AppIcon color={fiticianTokens.colors.aqua} name="nutrition" size={240} style={styles.backdropIcon} />
        </View>
        <View pointerEvents="none" style={StyleSheet.absoluteFill}>
          <Svg height="100%" preserveAspectRatio="none" style={StyleSheet.absoluteFill} width="100%">
            <Defs>
              <LinearGradient id="meal-catalogue-veil" x1="0%" x2="100%" y1="0%" y2="47%">
                <Stop offset="0%" stopColor="#0a1f1e" stopOpacity={0.84} />
                <Stop offset="54%" stopColor="#0a1f1e" stopOpacity={0.48} />
                <Stop offset="100%" stopColor="#0a1f1e" stopOpacity={0.74} />
              </LinearGradient>
            </Defs>
            <Rect fill="url(#meal-catalogue-veil)" height="100%" width="100%" x="0" y="0" />
          </Svg>
        </View>
        <Screen
          contentContainerStyle={styles.transparentContent}
          contentWidth="reading"
          style={styles.transparentScreen}
        >
          <NutritionCatalogueSection initialMode="meals" />
        </Screen>
      </View>
    </RouteGuard>
  );
}

const styles = StyleSheet.create({
  root: {
    backgroundColor: "transparent",
    flex: 1,
  },
  nutritionBackdrop: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceRaised,
    justifyContent: "center",
  },
  backdropIcon: {
    opacity: 0.12,
  },
  transparentContent: {
    backgroundColor: "transparent",
    paddingBottom: 104,
  },
  transparentScreen: {
    backgroundColor: "transparent",
  },
});
