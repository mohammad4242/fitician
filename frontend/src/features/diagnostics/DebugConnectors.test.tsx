import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../../shared/apiClient";
import { DebugConnectors } from "./DebugConnectors";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
beforeEach(() => vi.mocked(request).mockReset());
it("shows never connected honestly and scopes revocation to the selected connector", async () => {
  vi.mocked(request).mockResolvedValueOnce([{ id: "connector-1", name: "Laptop", environment: "staging", revoked: false, last_seen: null, capabilities: {} }]).mockResolvedValueOnce({ revoked: true }).mockResolvedValue([]);
  render(<DebugConnectors english />);
  await screen.findByText("Never connected");
  fireEvent.click(screen.getByRole("button", { name: "Revoke connector" }));
  await waitFor(() => expect(request).toHaveBeenCalledWith("/api/v1/admin/diagnostics/connectors/connector-1/revoke", { method: "POST" }));
});
it("downloads the once-returned credential without displaying it or using browser storage", async () => {
  const secret = "private-enrollment-fixture";
  vi.mocked(request).mockResolvedValueOnce([]).mockResolvedValueOnce({ id: "connector-1", token: secret, environment: "staging", repository: "mohammad4242/fitician" }).mockResolvedValue([]);
  URL.createObjectURL = vi.fn(() => "blob:private-config");
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  render(<DebugConnectors english />);
  fireEvent.click(screen.getByRole("button", { name: "Enroll and download private configuration" }));
  await waitFor(() => expect(click).toHaveBeenCalled());
  expect(document.body.textContent).not.toContain(secret);
  expect(JSON.stringify(localStorage)).not.toContain(secret);
  expect(JSON.stringify(sessionStorage)).not.toContain(secret);
  click.mockRestore();
});
