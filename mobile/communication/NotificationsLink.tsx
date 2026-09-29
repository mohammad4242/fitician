import { useRouter, type Href } from "expo-router";
import { Button } from "../ui/components";
import { languageForDirection } from "../ui/rtl";
export function NotificationsLink() {
  const router = useRouter();
  return <Button variant="ghost" label={languageForDirection() === "en" ? "Notifications and reminders" : "اعلان‌ها و یادآوری‌ها"} onPress={() => router.push("/notifications" as Href)} />;
}
