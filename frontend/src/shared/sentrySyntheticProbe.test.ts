import { expect, it } from "vitest";
import { raiseSyntheticWebFailure } from "./sentrySyntheticProbe";

it("retains the original tracked source frame for release verification", () => {
  try { raiseSyntheticWebFailure(); } catch (error) {
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).stack).toContain("sentrySyntheticProbe.ts");
    return;
  }
  throw new Error("Probe did not fail");
});
