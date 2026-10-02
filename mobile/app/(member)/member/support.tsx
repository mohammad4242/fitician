import { SupportScreen } from "../../../support/SupportScreen";
import { RouteGuard } from "../../../ui/navigation/RouteGuards";
export default function SupportRoute() { return <RouteGuard kind="account"><SupportScreen mode="home" /></RouteGuard>; }
