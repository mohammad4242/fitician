import { describe, expect, it } from "vitest";
import { createGenerationRequestKeys } from "./generationRequests";

describe("generation request keys", () => {
  it("retains ambiguous outcomes, separates workflows, and resets definitive outcomes", () => {
    let serial = 0;
    const keys = createGenerationRequestKeys(() => `request-${++serial}`);
    const workout = "/api/v1/workout-plans/generate";
    const nutrition = "/api/v1/nutrition/plans";
    const read = (path: string) => keys.headers(path, "POST", new Headers()).get("Idempotency-Key");
    expect(read(workout)).toBe("request-1");
    keys.completed(workout, 503);
    expect(read(workout)).toBe("request-1");
    expect(read(nutrition)).toBe("request-2");
    keys.completed(workout, 201);
    expect(read(workout)).toBe("request-3");
    keys.completed(workout, 409);
    expect(read(workout)).toBe("request-4");
    keys.clear();
    expect(read(nutrition)).toBe("request-5");
    expect(read("/api/v1/auth/login")).toBeNull();
    expect(keys.headers(workout, "POST", new Headers({ "Idempotency-Key": "explicit" })).get("Idempotency-Key")).toBe("explicit");
  });
});
