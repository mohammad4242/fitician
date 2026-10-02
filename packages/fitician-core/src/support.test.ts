import { expect, it, vi } from "vitest";
import { helpArticles, searchHelp, createSupportApi, mergeSupportMessages } from "./support.js";

it("searches shared titles, keywords and article content across Persian variants", () => {
  expect(searchHelp("fa", "ورود").some(a => a.id === "account-access")).toBe(true);
  expect(searchHelp("fa", "عكس").some(a => a.id === "body-analysis")).toBe(true);
  expect(searchHelp("en", "delete account").some(a => a.id === "privacy-deletion")).toBe(true);
  expect(searchHelp("en", "unfindableword")).toEqual([]);
  expect(searchHelp("fa", "")).toHaveLength(helpArticles.length);
  expect(new Set(helpArticles.map(a => a.id)).size).toBe(helpArticles.length);
});
it("uses dedicated ticket endpoints and preserves request identity", async () => {
  const request = vi.fn(async (_input: import("./transport.js").TransportRequest) => ({ id: "ticket" }));
  const api = createSupportApi(request as never);
  await api.create({ category: "account", subject: "Help", description: "Login", request_id: "request" });
  await api.reply("ticket/1", "Reply", "same-id");
  await api.reply("ticket/1", "Reply", "same-id");
  expect(request.mock.calls[1]).toEqual(request.mock.calls[2]);
  expect(request.mock.calls[1][0]).toMatchObject({ path: "/api/v1/support/tickets/ticket%2F1/messages", body: { request_id: "same-id" } });
});
it("merges paginated support messages without duplicates in chronological order", () => {
  const a = { id: "a", body: "one", created_at: "2026-10-01T10:00:00Z", sender_id: "user", sender_role: "member" as const };
  const b = { ...a, id: "b", created_at: "2026-10-02T10:00:00Z" };
  expect(mergeSupportMessages([b], [a, b]).map(m => m.id)).toEqual(["a", "b"]);
});
