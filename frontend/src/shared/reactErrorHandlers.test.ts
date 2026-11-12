import { afterEach, expect, it, vi } from "vitest";
import { rootErrorHandlers } from "./reactErrorHandlers";
import { captureReactError } from "./sentry";
vi.mock("./sentry", () => ({ captureReactError: vi.fn() }));
afterEach(() => vi.restoreAllMocks());
it("keeps the original uncaught error and component context while logging no sensitive text", () => {
  const log = vi.spyOn(console, "error").mockImplementation(() => {});
  const error = new Error("private medical fixture");
  const componentStack = "\n at BodyForm (/private/secret:42)";
  rootErrorHandlers.onUncaughtError(error, { componentStack });
  expect(captureReactError).toHaveBeenCalledWith(error, componentStack, "uncaught");
  expect(JSON.stringify(log.mock.calls)).not.toContain("medical");
  expect(JSON.stringify(log.mock.calls)).not.toContain("/private/");
});
