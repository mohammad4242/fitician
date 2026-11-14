import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";
import { request } from "../../shared/apiClient";
import { IssueFindings } from "./IssueFindings";

vi.mock("../../shared/apiClient", () => ({ request: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); sessionStorage.clear(); vi.unstubAllGlobals(); });
const hypothesis = {
  id: "finding-1", run_id: "run-1", classification: "hypothesis", text: "Boundary validation may be missing",
  occurrence_id: "occurrence-1", evidence_ids: ["evidence-1"], evidence_version: "a".repeat(64),
  model: "selected-model", stale: false, verification: null, can_verify: true,
  test_evidence: [{ id: "failed-test", passed: false, command: "test_bug.py" }, { id: "passed-test", passed: true, command: "test_bug.py" }],
};

it("separates a model hypothesis from a reviewed finding and shows evidence provenance", async () => {
  vi.mocked(request).mockResolvedValue({ findings: [hypothesis], next_offset: null } as never);
  render(<IssueFindings issueId="issue-1" occurrenceId="occurrence-1" english />);
  expect(await screen.findByText(hypothesis.text)).toBeInTheDocument();
  expect(screen.getByText("No reviewed finding for this evidence version.")).toBeInTheDocument();
  expect(screen.getByText("evidence-1")).toBeInTheDocument();
  expect(request).toHaveBeenCalledWith(expect.stringContaining("occurrence_id=occurrence-1"));
});

it("requires an explicit review of selected failure and success evidence", async () => {
  vi.stubGlobal("crypto", webcrypto);
  vi.mocked(request).mockImplementation(async (_path, options) => options?.method === "POST" ? { id: "review-1" } as never : { findings: [hypothesis], next_offset: null } as never);
  render(<IssueFindings issueId="issue-1" occurrenceId="occurrence-1" english />);
  await screen.findByText(hypothesis.text);
  fireEvent.click(screen.getByText("Review regression evidence"));
  fireEvent.change(screen.getByLabelText("Failing regression test"), { target: { value: "failed-test" } });
  fireEvent.change(screen.getByLabelText("Passing regression test"), { target: { value: "passed-test" } });
  fireEvent.change(screen.getByLabelText("What did you verify?"), { target: { value: "Reviewed the same scenario before and after the patch." } });
  fireEvent.click(screen.getByRole("button", { name: "Record reviewed finding" }));
  await waitFor(() => expect(request).toHaveBeenCalledWith(expect.stringContaining("/findings/finding-1/verify"), expect.objectContaining({
    method: "POST", headers: { "Idempotency-Key": expect.any(String) },
    body: JSON.stringify({ before_test_id: "failed-test", after_test_id: "passed-test", evidence_version: "a".repeat(64), note: "Reviewed the same scenario before and after the patch." }),
  })));
});

it("does not present a stale review as a current confirmed finding", async () => {
  vi.mocked(request).mockResolvedValue({ findings: [{ ...hypothesis, stale: true, can_verify: false, verification: { id: "review-1", note: "Previous review" } }], next_offset: null } as never);
  render(<IssueFindings issueId="issue-1" occurrenceId="occurrence-1" english={false} />);
  expect(await screen.findByText("شواهد تغییر کرده؛ بررسی قبلی نیاز به بازبینی دارد.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "ثبت یافتهٔ بررسی‌شده" })).not.toBeInTheDocument();
});
