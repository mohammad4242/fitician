import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";

import i18n from "../i18n";
import { PersianDatePicker } from "./PersianDatePicker";
import { PersianDateTimePicker } from "./PersianDateTimePicker";

afterEach(async () => {
  await i18n.changeLanguage("fa");
});

it("shows an ISO date as a Jalali date in Persian", () => {
  render(<PersianDatePicker ariaLabel="تاریخ تولد" label="تاریخ تولد" onChange={() => undefined} value="2026-09-14" />);

  expect(screen.getByRole("button", { name: "تاریخ تولد" })).toHaveTextContent("۲۳ شهریور ۱۴۰۵");
  expect(screen.queryByDisplayValue("2026-09-14")).not.toBeInTheDocument();
});

it("selects a Jalali date and returns the Gregorian ISO date", async () => {
  const user = userEvent.setup();
  let nextValue = "";
  render(<PersianDatePicker ariaLabel="تاریخ" onChange={(value) => { nextValue = value; }} value="2026-09-14" />);

  await user.click(screen.getByRole("button", { name: "تاریخ" }));
  await user.selectOptions(screen.getByRole("combobox", { name: "تاریخ - روز" }), "24");
  await user.click(screen.getByRole("button", { name: "انتخاب" }));

  expect(nextValue).toBe("2026-09-15");
});

it("enforces date bounds and supports clearing", async () => {
  const user = userEvent.setup();
  let nextValue = "2026-09-14";
  const { rerender } = render(
    <PersianDatePicker
      ariaLabel="تاریخ"
      label="تاریخ"
      max="2026-09-20"
      min="2026-09-15"
      onChange={(value) => { nextValue = value; }}
      value={nextValue}
    />,
  );

  await user.click(screen.getByRole("button", { name: "تاریخ" }));
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
  expect(screen.getByRole("alert")).toHaveTextContent("تاریخ معتبر");

  rerender(<PersianDatePicker ariaLabel="تاریخ" onChange={(value) => { nextValue = value; }} value={nextValue} />);
  await user.click(screen.getByRole("button", { name: "تاریخ" }));
  await user.click(screen.getByRole("button", { name: "پاک کردن" }));
  expect(nextValue).toBe("");
});

it("supports keyboard closing and accessible dialog state", async () => {
  const user = userEvent.setup();
  render(<PersianDatePicker ariaLabel="تاریخ" onChange={() => undefined} value="" />);

  const trigger = screen.getByRole("button", { name: "تاریخ" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

it("interprets Persian datetime input in Asia/Tehran and ignores the device timezone", async () => {
  const user = userEvent.setup();
  let nextValue: string | null = null;
  render(
    <PersianDateTimePicker
      ariaLabel="زمان"
      label="زمان"
      onChange={(value) => { nextValue = value; }}
      value="2026-09-14T15:00:00.000Z"
    />,
  );

  await user.click(screen.getByRole("button", { name: "زمان" }));
  expect(screen.getByRole("spinbutton", { name: "ساعت" })).toHaveValue(18);
  const hourInput = screen.getByRole("spinbutton", { name: "ساعت" });
  await user.clear(hourInput);
  await user.type(hourInput, "19");
  await user.click(screen.getByRole("button", { name: "انتخاب" }));

  expect(nextValue).toBe("2026-09-14T16:00:00.000Z");
});

it("keeps the English branch Gregorian", async () => {
  await i18n.changeLanguage("en");
  const onChange = (value: string) => value;
  render(<PersianDatePicker ariaLabel="Birth date" onChange={onChange} value="2026-09-14" />);

  expect(screen.getByDisplayValue("2026-09-14")).toHaveAttribute("type", "date");
});
