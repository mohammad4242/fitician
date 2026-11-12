import { expect, it } from "vitest";
import { explainIssueCode } from "./issueExplanation";

it("does not interpret missing completion as proven failure", () => {
  const explanation = explainIssueCode("WORKFLOW_OUTCOME_UNCONFIRMED", false);
  expect(explanation.what).toContain("ثبت نشده");
  expect(explanation.cause).toBeNull();
});
it("keeps expected product rules separate from operational failures", () => {
  expect(explainIssueCode("PROFILE_INCOMPLETE", false).expected).toBe(true);
  expect(explainIssueCode("UNHANDLED_EXCEPTION", false).expected).toBe(false);
});
it("does not infer root cause from a model identifier error", () => {
  expect(explainIssueCode("model_not_found", true).cause).toBeNull();
});
