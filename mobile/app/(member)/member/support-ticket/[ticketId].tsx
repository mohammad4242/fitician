import { useLocalSearchParams } from "expo-router";
import { SupportScreen } from "../../../../support/SupportScreen";
import { RouteGuard } from "../../../../ui/navigation/RouteGuards";
export default function SupportTicketRoute() { const {ticketId}=useLocalSearchParams<{ticketId:string}>();return <RouteGuard kind="account"><SupportScreen key={ticketId} mode="detail" ticketId={ticketId} /></RouteGuard>; }
