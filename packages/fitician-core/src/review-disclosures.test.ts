import { describe, expect, it } from "vitest";

import {
  reviewDisclosureDefaultExpanded,
  reviewDisclosureKeys,
} from "./review-disclosures.js";

describe("review disclosure contract", () => {
  it("defines a closed disclosure for coach exercise details", () => {
    expect(reviewDisclosureKeys.coachWorkoutExercise).toBe("coach-workout-exercise");
    expect(reviewDisclosureDefaultExpanded(reviewDisclosureKeys.coachWorkoutExercise)).toBe(false);
  });

  it("keeps every detailed specialist section closed by default", () => {
    expect(Object.values(reviewDisclosureKeys).every((key) => !reviewDisclosureDefaultExpanded(key))).toBe(true);
  });
});
