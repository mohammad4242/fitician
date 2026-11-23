import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NotificationDeliveries } from "./NotificationDeliveries";
import { request } from "../../shared/apiClient";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
afterEach(() => vi.clearAllMocks());
it("distinguishes provider acceptance from delivery without exposing a recipient", async () => {
  vi.mocked(request).mockResolvedValue({ items: [{ id: "delivery", issue_id: "issue", state: "accepted", occurrence_total: 5, provider_message_id: "12345", error_code: null, attempts: [] }], configuration: { enabled: true, recipient_configured: true, provider_configured: true, cooldown_seconds: 3600, min_interval_seconds: 30, max_per_hour: 20 }, next_offset: null } as never);
  render(<NotificationDeliveries english issueId="issue" />);
  expect(await screen.findByText("Accepted; delivery unconfirmed")).toBeInTheDocument();
  expect(request).toHaveBeenCalledWith(expect.stringContaining("issue_id=issue"));
  expect(screen.queryByText("Delivered by provider")).not.toBeInTheDocument();
});
