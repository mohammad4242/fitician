import { describe, expect, it } from "vitest";
import * as nutrition from "./nutrition";

describe("nutrition quantity basis", () => {
  it("distinguishes dry, cooked and unknown weights", () => {
    expect(nutrition).toHaveProperty("foodMeasurementBasisLabel");
    const label = (nutrition as unknown as {
      foodMeasurementBasisLabel: (basis: string | null, language?: string) => string;
    }).foodMeasurementBasisLabel;
    expect(label("dry")).toBe("وزن خشک");
    expect(label("cooked")).toBe("وزن پخته");
    expect(label(null)).toBe("مبنای وزن نامشخص");
    expect(label("raw", "en")).toBe("Raw weight");
  });
});
