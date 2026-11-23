import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { IssueEvidence } from "./IssueEvidence";
vi.mock("../../shared/apiClient", () => ({ request: vi.fn().mockResolvedValue({
  missing: [], snapshot: null, external_issue_url: "https://fitician.sentry.io/issues/123/",
}) }));
it("links the selected occurrence to the observed Sentry issue even without a local stack", async () => {
  render(<IssueEvidence issueId="issue" events={[]} english occurrenceId="occurrence" onOccurrenceChange={() => {}} />);
  expect((await screen.findByRole("link", { name: "Open Sentry issue" })).getAttribute("href")).toBe("https://fitician.sentry.io/issues/123/");
});
