import { describe, expect, it } from "vitest";
import { diagnosticsRelease } from "./diagnosticsRelease";

describe("exact mobile diagnostic release", () => {
  it("identifies the immutable commit separately from the native build number", () => {
    expect(diagnosticsRelease("a".repeat(40), "19")).toEqual({ commit: "a".repeat(40), release: `fitician-mobile@${"a".repeat(40)}`, dist: "19" });
  });
  it("does not label a native version code or unknown source tree as a Git commit", () => {
    expect(diagnosticsRelease("19", "19")).toEqual({ dist: "19" });
    expect(diagnosticsRelease(undefined, "private@example.invalid")).toEqual({});
  });
});
