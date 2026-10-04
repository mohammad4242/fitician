import { useThemeTokens } from "../ui/theme/ThemeProvider";
import { useLocalSearchParams } from "expo-router";
import { Text } from "react-native";
import { ConversationPanel } from "../communication/ConversationPanel";
import { RouteGuard } from "../ui/navigation/RouteGuards";
import { Screen } from "../ui/layout";
export default function ConversationRoute() {
  const tokens = useThemeTokens();
  const { kind, reviewId } = useLocalSearchParams<{ kind: string; reviewId: string }>();
  return <RouteGuard kind="account"><Screen>{(kind === "workout" || kind === "nutrition") && typeof reviewId === "string" ? <ConversationPanel initiallyOpen kind={kind} reviewId={reviewId} /> : <Text style={{ color: tokens.colors.ink }}>گفت‌وگو پیدا نشد.</Text>}</Screen></RouteGuard>;
}
