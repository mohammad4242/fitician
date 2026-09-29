import type { components } from "./generated/api.js";
import type { TransportRequest } from "./transport.js";
export type Conversation = components["schemas"]["ConversationResponse"];
export type ProgramMessage = components["schemas"]["MessageResponse"];
export type NotificationInbox = components["schemas"]["NotificationInboxPage"];
export type PersonalNotificationSettings = components["schemas"]["NotificationPreferencesResponse"];
type NotificationUpdateWire = components["schemas"]["NotificationPreferencesUpdateRequest"];
type NewPreferenceFlags = "messages" | "training_reminders" | "nutrition_reminders" | "return_reminders";
export type PersonalNotificationInput = Omit<NotificationUpdateWire, NewPreferenceFlags> & Partial<Pick<NotificationUpdateWire, NewPreferenceFlags>>;
export type ConversationKind = "workout" | "nutrition";
export type CommunicationRequest = <T>(input: TransportRequest) => Promise<T>;
export function createMessageRequestId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, value => {
    const random = Math.floor(Math.random() * 16);
    return (value === "x" ? random : (random & 3) | 8).toString(16);
  });
}
export function createCommunicationApi(request: CommunicationRequest) {
  const path = (kind: ConversationKind, id: string) => `/api/v1/program-conversations/${kind}/${encodeURIComponent(id)}`;
  return {
    conversation: async (kind: ConversationKind, target: { reviewId?: string; planId?: string }, before?: string) => { const response = await request<Conversation>({ method: "GET", path: `${target.reviewId ? path(kind, target.reviewId) : `/api/v1/program-conversations/${kind}/by-plan/${encodeURIComponent(target.planId ?? "")}`}${before ? `?before=${encodeURIComponent(before)}` : ""}` });
      if (!response || !Array.isArray(response.messages) || typeof response.available !== "boolean") throw new Error("Invalid conversation response");
      return response;
    },
    send: (kind: ConversationKind, reviewId: string, body: string, requestId: string) => request<ProgramMessage>({ method: "POST", path: path(kind, reviewId), body: { body, request_id: requestId } }),
    readConversation: (kind: ConversationKind, reviewId: string, messageId: string) => request<void>({ method: "PUT", path: `${path(kind, reviewId)}/read`, body: { message_id: messageId } }),
    inbox: (before?: string) => request<NotificationInbox>({ method: "GET", path: `/api/v1/notifications/inbox${before ? `?before=${encodeURIComponent(before)}` : ""}` }),
    readNotification: (id: string) => request<void>({ method: "PUT", path: `/api/v1/notifications/inbox/${encodeURIComponent(id)}/read` }),
    preferences: () => request<PersonalNotificationSettings>({ method: "GET", path: "/api/v1/notifications/preferences" }),
    savePreferences: (input: PersonalNotificationInput) => request<PersonalNotificationSettings>({ method: "PUT", path: "/api/v1/notifications/preferences", body: { ...input } }),
  };
}
