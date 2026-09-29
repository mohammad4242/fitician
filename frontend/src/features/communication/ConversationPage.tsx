import { useParams } from "react-router-dom";
import { ConversationPanel } from "./ConversationPanel";
export function ConversationPage() {
  const { kind, reviewId } = useParams();
  if ((kind !== "workout" && kind !== "nutrition") || !reviewId) return <p>گفت‌وگو پیدا نشد.</p>;
  return <main><h1>گفت‌وگوی برنامه</h1><ConversationPanel initiallyOpen kind={kind} reviewId={reviewId} /></main>;
}
