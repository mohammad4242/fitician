import { describe, expect, it } from "vitest";

import {
  reviewDisclosureDefaultExpanded,
  reviewDisclosureKeys,
} from "./review-disclosures.js";

describe("review disclosure contract", () => {
  it("keeps every detailed specialist section closed by default", () => {
    expect(Object.values(reviewDisclosureKeys).every((key) => !reviewDisclosureDefaultExpanded(key))).toBe(true);
  });
});
