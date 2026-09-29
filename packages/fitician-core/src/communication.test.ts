import { expect, it } from "vitest";
import { createCommunicationApi, createMessageRequestId } from "./communication";
import type { TransportRequest } from "./transport";
it("uses the same request id across retries and resolves program-scoped conversations", async () => {
  const requests: TransportRequest[] = [];
  const api = createCommunicationApi(async <T>(request: TransportRequest) => { requests.push(request); return { available: true, messages: [] } as T; });
  const id = createMessageRequestId();
  expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  await api.conversation("workout", { planId: "plan" });
  await api.send("workout", "review", "Question", id);
  await api.send("workout", "review", "Question", id);
  expect(requests[0]!.path).toBe("/api/v1/program-conversations/workout/by-plan/plan");
  expect(requests[1]!.body).toEqual(requests[2]!.body);
});
it("encodes inbox pagination and read acknowledgements", async () => {
  const requests: TransportRequest[] = [];
  const api = createCommunicationApi(async <T>(request: TransportRequest) => { requests.push(request); return {} as T; });
  await api.inbox("cursor");
  await api.readNotification("item");
  expect(requests[0]!.path).toContain("before=cursor");
  expect(requests[1]!.method).toBe("PUT");
});
