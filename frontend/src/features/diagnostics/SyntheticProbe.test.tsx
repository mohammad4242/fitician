import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { request } from "../../shared/apiClient";
import { SyntheticProbe } from "./SyntheticProbe";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); sessionStorage.clear(); });

it("hides the capture action when the host policy disables it", async () => {
  vi.mocked(request).mockResolvedValue({ enabled: false } as never);
  render(<SyntheticProbe english onCaptured={() => {}} />);
  await waitFor(() => expect(request).toHaveBeenCalled());
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("opens the exact occurrence without claiming external ingestion and retains retry identity", async () => {
  const captured = vi.fn();
  vi.mocked(request).mockImplementation(async (_path, options) => options?.method === "POST"
    ? { issue_id: "issue", event_id: "occurrence", delivery: "unconfirmed" } as never
    : { enabled: true } as never);
  render(<SyntheticProbe english onCaptured={captured} />);
  fireEvent.click(await screen.findByRole("button", { name: "Record a controlled test error" }));
  await waitFor(() => expect(captured).toHaveBeenCalledWith("issue", "occurrence"));
  expect(request).toHaveBeenCalledWith("/api/v1/admin/diagnostics/synthetic-probe",
    expect.objectContaining({ method: "POST", headers: { "Idempotency-Key": expect.any(String) } }));
  expect(await screen.findByRole("status")).toHaveTextContent("Local occurrence recorded; Sentry ingestion remains unconfirmed.");
});
