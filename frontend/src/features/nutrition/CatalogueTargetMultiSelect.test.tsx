import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import * as nutritionApi from "./api";
import { CatalogueTargetMultiSelect } from "./CatalogueTargetMultiSelect";
import type { NutritionCatalogueTarget } from "./types";

vi.mock("./api", () => ({ getNutritionCatalogueOptions: vi.fn() }));

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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(nutritionApi.getNutritionCatalogueOptions).mockResolvedValue({ items: [food, meal] });
});

function renderPicker(value: NutritionCatalogueTarget[] = [], onChange = vi.fn()) {
  render(
    <CatalogueTargetMultiSelect
      label="غذاهای مورد علاقه"
      value={value}
      onChange={onChange}
    />,
  );
  return onChange;
}

it("debounces search and renders food and meal type badges", async () => {
  const user = userEvent.setup();
  renderPicker();

  await user.type(screen.getByRole("combobox", { name: "غذاهای مورد علاقه" }), "مرغ");

  expect((await screen.findAllByRole("option", { name: /مرغ/ }))[0]).toBeInTheDocument();
  expect(screen.getByText("ماده غذایی")).toBeInTheDocument();
  expect(screen.getByText("وعده")).toBeInTheDocument();
  expect(nutritionApi.getNutritionCatalogueOptions).toHaveBeenCalledWith(
    expect.objectContaining({ query: "مرغ", limit: 20 }),
    expect.any(AbortSignal),
  );
});

it("shows loading and then adds a selected catalogue item", async () => {
  const user = userEvent.setup();
  let resolve: ((value: { items: NutritionCatalogueTarget[] }) => void) | undefined;
  vi.mocked(nutritionApi.getNutritionCatalogueOptions).mockImplementation(
    () => new Promise((nextResolve) => { resolve = nextResolve; }),
  );
  const onChange = renderPicker();

  await user.click(screen.getByRole("combobox", { name: "غذاهای مورد علاقه" }));
  expect(await screen.findByText("در حال جست‌وجو…")).toBeInTheDocument();
  resolve?.({ items: [food] });

  const option = (await screen.findAllByRole("option", { name: /^مرغ/ }))[0];
  await user.click(within(option).getByRole("button"));
  expect(onChange).toHaveBeenCalledWith([food]);
});

it("removes a chip and prevents duplicate selection", async () => {
  const user = userEvent.setup();
  const onChange = renderPicker([food]);

  await user.click(screen.getByRole("button", { name: "حذف مرغ" }));
  expect(onChange).toHaveBeenCalledWith([]);
  onChange.mockClear();

  await user.click(screen.getByRole("combobox", { name: "غذاهای مورد علاقه" }));
  const duplicate = (await screen.findAllByRole("option", { name: /^مرغ/ }))[0];
  await user.click(within(duplicate).getByRole("button"));
  expect(onChange).not.toHaveBeenCalled();
});

it("selects only the highlighted option and rejects arbitrary text", async () => {
  const user = userEvent.setup();
  vi.mocked(nutritionApi.getNutritionCatalogueOptions).mockImplementation(({ query } = {}) => Promise.resolve({
    items: query === "پیتزای مخصوص محمد" ? [] : [food, meal],
  }));
  const onChange = renderPicker();
  const input = screen.getByRole("combobox", { name: "غذاهای مورد علاقه" });

  await user.type(input, "پیتزای مخصوص محمد");
  await waitFor(() => expect(nutritionApi.getNutritionCatalogueOptions).toHaveBeenCalled());
  await user.keyboard("{Enter}");
  expect(onChange).not.toHaveBeenCalled();

  await user.clear(input);
  await screen.findAllByRole("option", { name: /مرغ/ });
  await user.keyboard("{Enter}");
  expect(onChange).toHaveBeenCalledWith([food]);
});

it("reports catalogue request errors", async () => {
  const user = userEvent.setup();
  vi.mocked(nutritionApi.getNutritionCatalogueOptions).mockRejectedValue(new Error("offline"));
  renderPicker();

  await user.click(screen.getByRole("combobox", { name: "غذاهای مورد علاقه" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("جست‌وجوی فهرست انجام نشد");
});
