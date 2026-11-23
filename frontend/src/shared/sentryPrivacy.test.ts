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

it("keeps bundle Debug-ID lookup coordinates without exporting origin or query values", () => {
  const result = sanitizeSentryEvent({ exception: { values: [{ type: "Error", stacktrace: { frames: [{ filename: "https://app.example/assets/main.js?token=secret", lineno: 3, colno: 8 }] } }] }, debug_meta: { images: [{ type: "sourcemap", code_file: "https://app.example/assets/main.js?token=secret", debug_id: "abc-123" }] } });
  expect(result.debug_meta.images[0].code_file).toBe("assets/main.js");
  expect((result.exception.values[0].stacktrace.frames[0] as Record<string, unknown>).abs_path).toBe("assets/main.js");
  expect(JSON.stringify(result)).not.toContain("secret");
});
