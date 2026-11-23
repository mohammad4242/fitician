import { expect, it, vi } from "vitest";

import { createSentryCompatibleAdapter, type SentryClientLike } from "./sentryAdapter";

it("maps the provider-neutral adapter to Sentry capture calls", () => {
  const client = {
    captureException: vi.fn(),
    captureMessage: vi.fn(),
  } satisfies SentryClientLike;
  const adapter = createSentryCompatibleAdapter(client);
  const context = { correlation_id: "corr-1", operation: "request" };
  const error = new Error("safe");

  adapter.captureMessage("native_request_completed", "info", context);
  adapter.captureException(error, context);

  expect(client.captureMessage).toHaveBeenCalledWith(
    "native_request_completed",
    { extra: context, level: "info" },
  );
  expect(client.captureException).toHaveBeenCalledWith(error, { extra: context });
});


it("excludes expected HTTP rejections without replacing operational error stacks", () => {
  const client = { captureException: vi.fn(), captureMessage: vi.fn() };
  const adapter = createSentryCompatibleAdapter(client);
  const error = new Error("original failure");
  adapter.captureException(error, {http_status: 403});
  expect(client.captureException).not.toHaveBeenCalled();
  adapter.captureException(error, {http_status: 503});
  expect(client.captureException.mock.calls[0][0]).toBe(error);
});
