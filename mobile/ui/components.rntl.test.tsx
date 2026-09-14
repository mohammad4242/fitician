import { fireEvent, render, screen, within } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
import { Animated, StyleSheet, Text } from "react-native";
import { Circle } from "react-native-svg";

jest.mock("expo-router", () => ({
  useFocusEffect: (effect: () => void) => effect(),
}));

import { Button } from "./components/Button";
import { CinematicSurface } from "./components/CinematicSurface";
import { TextField } from "./components/Input";
import { MetricRing } from "./components/MetricRing";
import { Dialog, Sheet } from "./components/Overlay";
import { Notice } from "./components/Feedback";
import { TrainingWeekdaySelector } from "./components/TrainingWeekdaySelector";
import { calculateRingGeometry } from "./visualMetrics";

test("renders the shared button with native accessibility and press behavior", () => {
  const onPress = jest.fn();

  render(<Button label="ذخیره" onPress={onPress} />);

  const button = screen.getByRole("button", { name: "ذخیره" });
  expect(button.props.accessibilityState).toMatchObject({ disabled: false, busy: false });
  expect(button.props.style).toEqual(
    expect.arrayContaining([expect.objectContaining({ minHeight: 48, minWidth: 48 })]),
  );

  fireEvent.press(button);
  expect(onPress).toHaveBeenCalledTimes(1);
});

test("announces the Persian loading state while preserving the button state", () => {
  render(<Button label="ذخیره" loading onPress={jest.fn()} />);

  const button = screen.getByRole("button", { name: "ذخیره" });
  expect(button.props.accessibilityState).toMatchObject({ busy: true, disabled: true });
  expect(screen.getByLabelText("در حال بارگذاری")).toBeTruthy();
});

test("keeps screen-reader names, font scaling, and focus order in source order", () => {
  render(
    <>
      <TextField label="ایمیل" />
      <Button label="اول" onPress={jest.fn()} />
      <Button label="دوم" onPress={jest.fn()} />
    </>,
  );

  const field = screen.getByLabelText("ایمیل");
  expect(field.props.allowFontScaling).toBe(true);
  expect(field.props.accessibilityLabel).toBe("ایمیل");
  expect(screen.getAllByRole("button").map((button) => button.props.accessibilityLabel)).toEqual([
    "اول",
    "دوم",
  ]);
});

test("exposes metric progress and its visible value to assistive technology", () => {
  render(<MetricRing label="پیشرفت کالری امروز" progress={0.375} />);

  const ring = screen.getByRole("progressbar", { name: "پیشرفت کالری امروز" });
  expect(ring.props.accessibilityValue).toEqual({ max: 100, min: 0, now: 38 });
  expect(screen.getByText("۳۸٪")).toBeTruthy();
});

test("keeps the shared ring static unless focus animation is explicitly enabled", () => {
  render(<MetricRing label="پیشرفت کالری امروز" progress={0.375} />);

  const progressCircle = screen.UNSAFE_getAllByType(Circle)[1];
  expect(progressCircle.props.strokeDashoffset).toBe(calculateRingGeometry(92, 8, 0.375).dashOffset);
});

test("uses the requested duration for the opt-in focus entrance animation", () => {
  const timing = jest.spyOn(Animated, "timing").mockReturnValue({ start: jest.fn() } as never);

  render(<MetricRing animateOnFocus animationDuration={900} label="پیشرفت کالری امروز" progress={0.375} />);

  expect(timing).toHaveBeenCalledWith(
    expect.anything(),
    expect.objectContaining({ duration: 900, toValue: 0.375, useNativeDriver: false }),
  );
  timing.mockRestore();
});

test("keeps Persian overlays direction-aware", () => {
  const view = render(
    <>
      <Sheet onClose={jest.fn()} title="جزئیات" visible><Text>متن</Text><TextField label="نام" /></Sheet>
      <Dialog message="پیام" onClose={jest.fn()} title="تأیید" visible />
    </>,
  );

  expect(view).toBeTruthy();
});

test("anchors the shared cinematic surface to the RTL layout boundary", () => {
  render(
    <CinematicSurface testID="cinematic-surface">
      <Text>محتوا</Text>
    </CinematicSurface>,
  );

  expect(StyleSheet.flatten(screen.getByTestId("cinematic-surface").props.style)).toMatchObject({
    direction: "rtl",
  });
});

test("announces errors and exposes native modal boundaries", () => {
  const view = render(
    <>
      <Notice message="اتصال برقرار نیست" title="خطا" variant="danger" />
      <Sheet onClose={jest.fn()} title="جزئیات" visible><Text>متن</Text></Sheet>
      <Dialog message="ادامه می‌دهی؟" onClose={jest.fn()} title="تأیید" visible />
    </>,
  );

  const alert = view.UNSAFE_getByProps({ accessibilityRole: "alert" });
  expect(alert.props.accessibilityLiveRegion).toBe("assertive");
  expect(view.getByLabelText("جزئیات").props.accessibilityViewIsModal).toBe(true);
  expect(view.getByLabelText("تأیید").props.accessibilityViewIsModal).toBe(true);
});

test("keeps official weekday presets and exact custom selection accessible", () => {
  const onChange = jest.fn();
  const view = render(
    <TrainingWeekdaySelector
      onChange={onChange}
      selectedWeekdays={[0, 1, 3, 4]}
      trainingDays={4}
    />,
  );

  expect(screen.getByRole("radio", { name: "شنبه · یکشنبه · سه‌شنبه · چهارشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
  expect(screen.getByRole("radio", { name: "یکشنبه · دوشنبه · چهارشنبه · پنجشنبه" })).toBeTruthy();

  fireEvent.press(screen.getByRole("radio", { name: "روزهای تمرین را خودم انتخاب می‌کنم" }));
  const custom = screen.getByLabelText("روزهای دلخواه");
  expect(within(custom).getAllByRole("checkbox")).toHaveLength(7);
  expect(within(custom).getAllByRole("checkbox").filter((item) => item.props.accessibilityState?.disabled))
    .toHaveLength(3);

  fireEvent.press(within(custom).getByRole("checkbox", { name: "شنبه" }));
  expect(onChange).toHaveBeenLastCalledWith([1, 3, 4]);
  view.rerender(
    <TrainingWeekdaySelector
      onChange={onChange}
      selectedWeekdays={[1, 3, 4]}
      trainingDays={4}
    />,
  );
  const updatedCustom = screen.getByLabelText("روزهای دلخواه");
  expect(within(updatedCustom).getByRole("checkbox", { name: "جمعه" }).props.accessibilityState)
    .toMatchObject({ disabled: false });
  fireEvent.press(within(updatedCustom).getByRole("checkbox", { name: "جمعه" }));
  expect(onChange).toHaveBeenLastCalledWith([1, 3, 4, 6]);
});

test("renders every shared two-day preset", () => {
  const view = render(
    <TrainingWeekdaySelector onChange={jest.fn()} selectedWeekdays={[0, 3]} trainingDays={2} />,
  );

  expect(screen.getByRole("radio", { name: "شنبه · سه‌شنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
  view.rerender(
    <TrainingWeekdaySelector onChange={jest.fn()} selectedWeekdays={[1, 4]} trainingDays={2} />,
  );
  expect(screen.getByRole("radio", { name: "یکشنبه · چهارشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
  view.rerender(
    <TrainingWeekdaySelector onChange={jest.fn()} selectedWeekdays={[2, 5]} trainingDays={2} />,
  );
  expect(screen.getByRole("radio", { name: "دوشنبه · پنجشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
});
