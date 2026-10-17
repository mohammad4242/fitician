import { expect, it } from "vitest";
import { safeClientException } from "./clientException";

it("extracts only a known type and bundle location, excluding URLs and private messages", () => {
  const error = new TypeError("private form values");
  error.stack = "TypeError: private form values\n at render (https://fitician.fit/assets/WorkoutPage-AbCd1234.js:1:321)";
  expect(safeClientException(error)).toEqual({exception_type: "TypeError", source_location: "WorkoutPage-AbCd1234.js:1:321"});
  error.stack = "TypeError: private form values\n at private (/home/member/medical-history.tsx:1:3)";
  expect(safeClientException(error)).toEqual({exception_type: "TypeError"});
});

it("captures native line/column and rejects unknown error names and raw rejections", () => {
  const error = new Error("private native data");
  error.name = "private-value";
  error.stack = "Error: private native data\n at anonymous (address at index.android.bundle:1:123456)";
  expect(safeClientException(error)).toEqual({exception_type: "Error", source_location: "index.android.bundle:1:123456"});
  expect(safeClientException("private rejection")).toEqual({});
  const malicious = new Error("private");
  Object.defineProperty(malicious, "stack", { get() { throw new Error("getter failed"); } });
  expect(safeClientException(malicious)).toEqual({});
});
