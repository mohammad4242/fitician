import { expect, it } from "vitest";
import type { Conversation } from "./communication";

function messages(start: number, end: number) {
  return Array.from({ length: end - start + 1 }, (_, index) => ({
    id: String(start + index), body: String(start + index), sender_id: "member",
    created_at: new Date(Date.UTC(2026, 8, 30, 0, 0, start + index)).toISOString(),
  }));
}
const old: Conversation = { available: true, review_id: "r", viewer_id: "member",
  messages: messages(1, 50), unread_count: 0, older_cursor: null };

it("keeps an accessible cursor when latest history has a gap", async () => {
  const { mergeConversationLatest } = await import("./communication");
  const result = mergeConversationLatest(old, { ...old, messages: messages(101, 150), older_cursor: "101" });
  expect(result.older_cursor).toBe("101");
  expect(result.messages.map(m => m.id)).toEqual(messages(101, 150).map(m => m.id));
});

it("retains older contiguous messages and their cursor when pages overlap", async () => {
  const { mergeConversationLatest } = await import("./communication");
  const result = mergeConversationLatest(old, { ...old, messages: messages(26, 75), older_cursor: "26" });
  expect(result.older_cursor).toBeNull();
  expect(result.messages.map(m => m.id)).toEqual(messages(1, 75).map(m => m.id));
});
