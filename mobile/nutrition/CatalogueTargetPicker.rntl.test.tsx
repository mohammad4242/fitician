import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";

import type { NutritionCatalogueTarget } from "@fitician/core/nutrition";
import { CatalogueTargetPicker, type CatalogueTargetSearchOptions } from "./CatalogueTargetPicker";

const food: NutritionCatalogueTarget = {
  target_type: "food",
  target_id: "food-1",
  name_fa: "مرغ",
  name_en: "Chicken",
  category: "poultry",
  image_url: null,
};

const meal: NutritionCatalogueTarget = {
  target_type: "meal",
  target_id: "meal-1",
  name_fa: "برنج و مرغ",
  name_en: "Chicken and rice",
  category: "lunch",
  image_url: null,
};

test("searches the Sheet, selects Food and Meal targets, and renders chips", async () => {
  const searchOptions = jest.fn<CatalogueTargetSearchOptions>().mockResolvedValue({ items: [food, meal] });
  const onChange = jest.fn();
  render(
    <CatalogueTargetPicker
      label="غذاهای مورد علاقه"
      onChange={onChange}
      searchOptions={searchOptions}
      value={[]}
    />,
  );

  fireEvent.press(screen.getByRole("button", { name: "غذاهای مورد علاقه افزودن" }));
  const input = screen.getByLabelText("غذاهای مورد علاقه جست‌وجو");
  fireEvent.changeText(input, "مرغ");
  await waitFor(() => expect(searchOptions).toHaveBeenCalledWith({ limit: 20, query: "مرغ" }), { timeout: 1200 });

  expect(screen.getByRole("button", { name: "مرغ، ماده غذایی" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "برنج و مرغ، وعده" })).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "مرغ، ماده غذایی" }));
  expect(onChange).toHaveBeenLastCalledWith([food]);
});

test("hydrates selected targets, removes them, and never commits arbitrary text", async () => {
  const searchOptions = jest.fn<CatalogueTargetSearchOptions>().mockResolvedValue({ items: [] });
  const onChange = jest.fn();
  render(
    <CatalogueTargetPicker
      label="حساسیت‌های غذایی"
      onChange={onChange}
      searchOptions={searchOptions}
      value={[{ ...food, details: null }]}
      includeDetails
    />,
  );

  expect(screen.getByText("مرغ")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "حذف مرغ" }));
  expect(onChange).toHaveBeenCalledWith([]);

  fireEvent.press(screen.getByRole("button", { name: "حساسیت‌های غذایی افزودن" }));
  const input = screen.getByLabelText("حساسیت‌های غذایی جست‌وجو");
  fireEvent.changeText(input, "پیتزای مخصوص محمد");
  await waitFor(() => expect(screen.getByText("مورد تأییدشده‌ای پیدا نشد.")).toBeTruthy(), { timeout: 1200 });
  expect(onChange).toHaveBeenCalledTimes(1);
});
