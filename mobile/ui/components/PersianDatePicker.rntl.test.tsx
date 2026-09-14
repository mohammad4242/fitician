import { fireEvent, render, screen } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";

import { PersianDatePicker } from "./PersianDatePicker";
import { PersianDateTimePicker } from "./PersianDateTimePicker";

test("shows an ISO date as a Persian Jalali date and starts closed", () => {
  render(
    <PersianDatePicker
      accessibilityLabel="تاریخ تولد"
      label="تاریخ تولد"
      testID="birth-date"
      value="2026-09-14"
      onChange={jest.fn()}
    />,
  );

  expect(screen.getByText("۲۳ شهریور ۱۴۰۵")).toBeTruthy();
  expect(screen.getByTestId("birth-date-trigger").props.accessibilityState).toMatchObject({
    expanded: false,
  });
  expect(screen.queryByTestId("birth-date-option-day-23")).toBeNull();
});

test("selects Jalali parts and returns the Gregorian ISO date", () => {
  const onChange = jest.fn();
  render(
    <PersianDatePicker
      accessibilityLabel="تاریخ شروع"
      label="تاریخ شروع"
      testID="start-date"
      value="2026-09-14"
      onChange={onChange}
    />,
  );

  fireEvent.press(screen.getByTestId("start-date-trigger"));
  fireEvent.press(screen.getByTestId("start-date-option-day-23"));
  fireEvent.press(screen.getByTestId("start-date-option-month-6"));
  fireEvent.press(screen.getByTestId("start-date-option-year-1405"));
  fireEvent.press(screen.getByRole("button", { name: "انتخاب" }));

  expect(onChange).toHaveBeenCalledWith("2026-09-14");
  expect(screen.queryByTestId("start-date-option-day-23")).toBeNull();
});

test("enforces bounds and clears nullable dates", () => {
  const onChange = jest.fn();
  render(
    <PersianDatePicker
      accessibilityLabel="تاریخ آزمایش"
      allowClear
      label="تاریخ آزمایش"
      max="2026-09-14"
      min="2026-09-01"
      testID="lab-date"
      value="2026-09-14"
      onChange={onChange}
    />,
  );

  fireEvent.press(screen.getByTestId("lab-date-trigger"));
  expect(screen.getByTestId("lab-date-option-day-24").props.accessibilityState).toMatchObject({ disabled: true });
  fireEvent.press(screen.getByRole("button", { name: "پاک کردن" }));
  expect(onChange).toHaveBeenCalledWith("");
  expect(screen.queryByTestId("lab-date-option-day-14")).toBeNull();
});

test("exposes an accessible expanded state and cancel action", () => {
  render(
    <PersianDatePicker
      accessibilityLabel="تاریخ برنامه"
      label="تاریخ برنامه"
      testID="plan-date"
      value="2026-09-14"
      onChange={jest.fn()}
    />,
  );

  const trigger = screen.getByTestId("plan-date-trigger");
  fireEvent.press(trigger);
  expect(trigger.props.accessibilityState).toMatchObject({ expanded: true });
  fireEvent.press(screen.getByRole("button", { name: "انصراف" }));
  expect(screen.queryByTestId("plan-date-option-day-23")).toBeNull();
});

test("interprets Persian datetime in Tehran and returns an ISO instant", () => {
  const onChange = jest.fn();
  render(
    <PersianDateTimePicker
      accessibilityLabel="زمان شروع"
      label="زمان شروع"
      testID="start-datetime"
      value="2026-09-14T15:00:00.000Z"
      onChange={onChange}
    />,
  );

  expect(screen.getByText("۲۳ شهریور ۱۴۰۵ · ۱۸:۳۰")).toBeTruthy();
  fireEvent.press(screen.getByTestId("start-datetime-trigger"));
  fireEvent.press(screen.getByTestId("start-datetime-option-hour-18"));
  fireEvent.press(screen.getByTestId("start-datetime-option-minute-30"));
  fireEvent.press(screen.getByRole("button", { name: "انتخاب" }));

  expect(onChange).toHaveBeenCalledWith("2026-09-14T15:00:00.000Z");
});
