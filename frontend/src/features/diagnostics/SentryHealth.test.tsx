import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { request } from "../../shared/apiClient";
import { SentryHealth } from "./SentryHealth";
import { explainIssueCode } from "./issueExplanation";

vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
afterEach(() => vi.clearAllMocks());

it("shows stale native discovery and exhausted exact-event deliveries separately", async () => {
  vi.mocked(request).mockResolvedValue({ external_states: { exhausted: 3 }, native_discovery: [{
    project: "mobile", environment: "test", state: "stale", last_error_code: "rate_limited",
    last_success_at: null, watermark: null, imported_count: 2,
  }] });
  render(<SentryHealth english />);
  expect(await screen.findByText("rate_limited")).toBeInTheDocument();
  expect(screen.getByText(/exhausted: 3/)).toBeInTheDocument();
  expect(screen.getByText(/stale/)).toBeInTheDocument();
});

it("does not turn a failed health request into a healthy status", async () => {
  vi.mocked(request).mockRejectedValue(new Error("offline"));
  render(<SentryHealth english={false} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("دریافت وضعیت Sentry انجام نشد");
});

it("describes native termination without claiming a verified cause", () => {
  const explanation = explainIssueCode("NATIVE_CRASH", false);
  expect(explanation.what).toContain("بومی");
  expect(explanation.cause).toBeNull();
  expect(explanation.expected).toBe(false);
});
