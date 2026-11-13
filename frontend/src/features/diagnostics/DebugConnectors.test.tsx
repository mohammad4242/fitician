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

it("retains the explicitly selected offline server while a laptop is online", async () => {
  const change = vi.fn();
  vi.mocked(request).mockResolvedValue([
    { id: "germany", name: "Germany", environment: "production", revoked: false, last_seen: null, capabilities: {} },
    { id: "laptop", name: "Laptop", environment: "production", revoked: false, last_seen: new Date().toISOString(), capabilities: {} },
  ]);
  render(<DebugConnectors english showExecutionTarget selectedTarget="germany" onSelectTarget={change} />);
  await screen.findByRole("option", { name: /Germany/ });
  expect(screen.getByRole("combobox", { name: "Tool execution target" })).toHaveValue("germany");
  expect(change).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("combobox", { name: "Tool execution target" }), { target: { value: "laptop" } });
  expect(change).toHaveBeenCalledWith("laptop");
});

it("keeps an unavailable saved target visible instead of clearing it", async () => {
  vi.mocked(request).mockResolvedValue([]);
  render(<DebugConnectors english showExecutionTarget selectedTarget="missing-target" onSelectTarget={vi.fn()} />);
  expect(await screen.findByRole("option", { name: "Selected target unavailable" })).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Tool execution target" })).toHaveValue("missing-target");
});

it("enrolls the Germany runtime separately from the optional laptop", async () => {
  vi.mocked(request).mockResolvedValueOnce([]).mockResolvedValueOnce({ id: "connector-1", token: "private-fixture", environment: "production", repository: "mohammad4242/fitician" }).mockResolvedValue([]);
  URL.createObjectURL = vi.fn(() => "blob:private-config");
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  render(<DebugConnectors english />);
  expect(screen.getByRole("combobox", { name: "New connector location" })).toHaveValue("server");
  fireEvent.click(screen.getByRole("button", { name: "Enroll and download private configuration" }));
  await waitFor(() => expect(request).toHaveBeenCalledWith("/api/v1/admin/diagnostics/connectors", { method: "POST", body: JSON.stringify({ name: "Germany debug runtime" }) }));
  click.mockRestore();
});
