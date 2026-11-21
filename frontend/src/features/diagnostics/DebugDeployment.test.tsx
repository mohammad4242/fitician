import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import type { components } from "@fitician/core";

import { request } from "../../shared/apiClient";
import { DeploymentReview, DeploymentRequest, ReleaseReplayRequest } from "./DebugDeployment";

vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
type Operation = components["schemas"]["OperationResponse"];
beforeEach(() => { vi.mocked(request).mockReset(); sessionStorage.clear(); });

it("requires explicit artifact review before authorization and retries with the same identity", async () => {
  const refresh = vi.fn();
  const operation = { id: "deploy", kind: "deploy", state: "awaiting_authorization", target_environment: "production-germany",
    result: { preview_sha256: "a".repeat(64), preview: { manifest_sha256: "b".repeat(64), manifest: { commit: "c".repeat(40), ci_run_id: 123, images: {} } } } } as unknown as Operation;
  vi.mocked(request).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(operation);
  render(<DeploymentReview operation={operation} issueId="issue" english onUpdated={refresh} />);
  const button = screen.getByRole("button", { name: "Authorize this artifact for this environment" });
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(button);
  await screen.findByRole("alert");
  fireEvent.click(button);
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  const calls = vi.mocked(request).mock.calls;
  expect(calls).toHaveLength(2);
  expect(calls[0][0]).toBe("/api/v1/admin/diagnostics/issues/issue/deployments/deploy/authorize");
  expect(calls[0][1]?.headers).toEqual(calls[1][1]?.headers);
  expect(JSON.parse(calls[0][1]?.body as string)).toEqual({ preview_sha256: "a".repeat(64) });
  expect(screen.getByText(/GitHub owner approval/)).toBeVisible();
});

it("requests a preview using only the selected occurrence's host observation", async () => {
  const publication = { id: "pr", occurrence_id: "selected", kind: "publish_pr", state: "succeeded" } as Operation;
  const observationDefaults = { run_id: "run", environment: "production", purpose: "server_observation" as const, cancel_requested: false, error_code: null, profile: null, snapshot_digest: null, created_at: "2026-11-14T00:00:00Z", updated_at: "2026-11-14T00:00:00Z" };
  const observations: Operation[] = [
    { id: "matching", occurrence_id: "selected", kind: "observe", state: "succeeded", target_environment: "production-germany", result: { observation: { complete: true } } },
    { id: "foreign", occurrence_id: "other", kind: "observe", state: "succeeded", target_environment: "production-iran", result: { observation: { complete: true } } },
  ].map(row => ({ ...observationDefaults, ...row, kind: "observe" as const, target_environment: row.target_environment as "production-iran" | "production-germany" }));
  vi.mocked(request).mockResolvedValue({});
  render(<DeploymentRequest publication={publication} observations={observations} issueId="issue" english onUpdated={() => {}} />);
  fireEvent.click(screen.getByText("Prepare deployment preview"));
  expect(screen.queryByRole("option", { name: /production-iran/ })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Recent target observation"), { target: { value: "matching" } });
  fireEvent.change(screen.getByLabelText("Successful release CI run ID"), { target: { value: "123" } });
  fireEvent.click(screen.getByRole("button", { name: "Check merged repair and release artifact" }));
  await waitFor(() => expect(request).toHaveBeenCalledOnce());
  const [path, options] = vi.mocked(request).mock.calls[0];
  expect(path.endsWith("/deployments")).toBe(true);
  expect(JSON.parse(options?.body as string)).toEqual({ publication_id: "pr", observation_id: "matching", ci_run_id: 123 });
});

it("replays a deployed regression using matching environment evidence and a stable request identity", async () => {
  const refresh = vi.fn();
  const deployment = { id: "deploy", kind: "deploy", state: "succeeded", occurrence_id: "selected",
    target_environment: "production-germany", result: { deployed: true } } as unknown as Operation;
  const observations = [
    { id: "same", kind: "observe", state: "succeeded", occurrence_id: "selected", target_environment: "production-germany", result: { observation: { complete: true } } },
    { id: "wrong-region", kind: "observe", state: "succeeded", occurrence_id: "selected", target_environment: "production-iran", result: { observation: { complete: true } } },
    { id: "wrong-occurrence", kind: "observe", state: "succeeded", occurrence_id: "other", target_environment: "production-germany", result: { observation: { complete: true } } },
  ] as unknown as Operation[];
  vi.mocked(request).mockRejectedValueOnce(new Error("disconnect")).mockResolvedValueOnce({});
  render(<ReleaseReplayRequest deployment={deployment} observations={observations} issueId="issue" english onUpdated={refresh} />);
  fireEvent.click(screen.getByText("Replay the deployed commit's regression tests"));
  expect(screen.getAllByRole("option")).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Matching fresh server evidence"), { target: { value: "same" } });
  fireEvent.click(screen.getByRole("button", { name: "Run isolated replay in GitHub Actions" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Run isolated replay in GitHub Actions" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  const calls = vi.mocked(request).mock.calls;
  expect(calls[0][0]).toBe("/api/v1/admin/diagnostics/issues/issue/deployments/deploy/replay");
  expect(calls[0][1]?.headers).toEqual(calls[1][1]?.headers);
  expect(JSON.parse(calls[0][1]?.body as string)).toEqual({ observation_id: "same" });
  expect(screen.getByText(/does not prove the production business outcome/)).toBeVisible();
});
