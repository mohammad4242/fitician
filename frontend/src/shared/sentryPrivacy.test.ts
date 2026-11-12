import { describe, expect, it } from "vitest";
import { sanitizeSentryEvent } from "./sentryPrivacy";

describe("Sentry export policy", () => {
  it("preserves source coordinates and removes user content from every automatic channel", () => {
    const clean = sanitizeSentryEvent({
      event_id: "abc", message: "secret", user: { email: "secret" },
      request: { data: "secret" }, contexts: { ai: { prompt: "secret" } },
      breadcrumbs: [{ message: "secret" }], spans: [{ description: "secret" }],
      exception: { values: [{ type: "TypeError", value: "secret", stacktrace: {
        frames: [{ filename: "/srv/src/App.tsx", function: "render", lineno: 12, vars: { x: "secret" } }],
      } }] },
    });
    expect(JSON.stringify(clean)).not.toContain("secret");
    expect(clean.exception.values[0].stacktrace.frames[0]).toEqual({
      filename: "src/App.tsx", function: "render", lineno: 12,
    });
  });
});

it("retains sanitized React component context", () => {
  const result = sanitizeSentryEvent({ contexts: { react: { componentStack: "\n at MemberPage (/srv/src/MemberPage.tsx:4)\n at Layout (/srv/src/Layout.tsx:8)" } } });
  expect(result.contexts.react).toEqual({ components: ["MemberPage", "Layout"] });
});
