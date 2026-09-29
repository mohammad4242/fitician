import { NotificationsScreen } from "../communication/NotificationsScreen";
import { RouteGuard } from "../ui/navigation/RouteGuards";
export default function NotificationsRoute() {
  return <RouteGuard kind="account"><NotificationsScreen /></RouteGuard>;
}
