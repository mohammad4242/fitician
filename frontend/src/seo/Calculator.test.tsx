import { it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Calculator } from "./Calculator";
import { calculateBmi, parseToolNumber } from "./calculators";
import { publicPayload, resolveSeo, sitemapDocuments } from "./registry";
import { renderToStaticMarkup } from "react-dom/server";
import { PublicPage } from "./PublicPage";

it("calculates BMI without rounding before classification", () => {
  expect(calculateBmi(175, 70)).toEqual({ value: 70 / 1.75 ** 2, category: 1 });
  for (const [weight, category] of [[73.99, 0], [74, 1], [99.99, 1], [100, 2], [119.99, 2], [120, 3]]) {
    expect(calculateBmi(200, weight).category).toBe(category);
  }
});
it("bounds BMI height and weight including inclusive endpoints", () => {
  for (const height of [0, -1, 129.9, 220.1, NaN, Infinity]) expect(() => calculateBmi(height, 70)).toThrow(RangeError);
  for (const weight of [0, -1, 34.9, 250.1, NaN, Infinity]) expect(() => calculateBmi(175, weight)).toThrow(RangeError);
  expect(calculateBmi(130, 35).value).toBeCloseTo(20.7101);
  expect(calculateBmi(220, 250).value).toBeCloseTo(51.6529);
});
it("accepts Persian and Arabic digits without accepting empty or malformed values", () => {
  expect(parseToolNumber("۱۷۵٫۵")).toBe(175.5);
  expect(parseToolNumber("٧٠.٥")).toBe(70.5);
  for (const value of ["", " ", "1e2", "70kg", "1,750", "0x50"]) expect(() => parseToolNumber(value)).toThrow();
});
it("renders BMI as a canonical indexable meaningful public tool", () => {
  const path = "/tools/bmi-calculator";
  const seo = resolveSeo(path);
  expect(seo.canonical).toBe("https://fitician.fit/tools/bmi-calculator");
  expect(seo.robots).toBe("index, follow");
  expect(seo.jsonLd.map(schema => schema["@type"])).toEqual(["WebPage", "BreadcrumbList"]);
  expect(Object.values(sitemapDocuments()).join("")).toContain(`${seo.canonical}</loc>`);
  const html = renderToStaticMarkup(<PublicPage payload={publicPayload(path)} />);
  expect(html).toContain("BMI");
  expect(html).toContain("۲۰ سال");
  expect(html).toContain('name="height"');
  expect(html).toContain('name="weight"');
  expect(html).toContain('dir="rtl"');
  expect(html).not.toContain("<video");
  expect(html).toContain('type="submit" disabled=""');
});
it("calculates BMI with localized input and announces the result", () => {
  render(<Calculator kind="bmi" />);
  fireEvent.change(screen.getByLabelText("قد"), { target: { value: "۱۷۵" } });
  fireEvent.change(screen.getByLabelText("وزن"), { target: { value: "۷۰" } });
  fireEvent.click(screen.getByRole("button", { name: "محاسبه نتیجه" }));
  expect(screen.getByRole("status")).toHaveTextContent("22.9");
  expect(screen.getByRole("status")).toHaveTextContent("بازه میانی مرجع");
  expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
});
it("clears stale results and focuses an invalid field", () => {
  render(<Calculator kind="bmi" />);
  fireEvent.click(screen.getByRole("button", { name: "محاسبه نتیجه" }));
  fireEvent.change(screen.getByLabelText("قد"), { target: { value: "0" } });
  fireEvent.click(screen.getByRole("button", { name: "محاسبه نتیجه" }));
  expect(screen.getByRole("alert")).toHaveTextContent("قد");
  expect(screen.getByLabelText("قد")).toHaveFocus();
  expect(screen.getByLabelText("قد")).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByRole("status")).not.toHaveTextContent("22.9");
});
it.each(["calorie", "protein"] as const)("preserves %s calculation", kind => {
  render(<Calculator kind={kind} />);
  fireEvent.click(screen.getByRole("button", { name: "محاسبه نتیجه" }));
  expect(screen.getByRole("status")).toHaveTextContent(kind === "calorie" ? "1,979" : "98 – 140");
});
