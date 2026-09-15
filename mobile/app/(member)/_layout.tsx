import { Stack } from "expo-router";

import { EntitlementErrorNotice } from "../../entitlements/EntitlementErrorNotice";
import { RouteGuard } from "../../ui/navigation/RouteGuards";

export default function MemberLayout() {
  return (
    <RouteGuard kind="member">
      <>
        <EntitlementErrorNotice />
        <Stack screenOptions={{ headerShown: false }} />
      </>
    </RouteGuard>
  );
}
