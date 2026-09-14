import { fireEvent, render, screen, within } from "@testing-library/react-native";
import { jest, test, expect } from "@jest/globals";

jest.mock("expo-router", () => ({
  useLocalSearchParams: () => ({}),
  useRouter: () => ({ replace: jest.fn() }),
}));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../ui/navigation/BackBehaviorProvider", () => ({ useAndroidBackHandler: jest.fn() }));
jest.mock("../ui/navigation/RouteGuards", () => ({
  useMobileRouteSnapshot: jest.fn(),
  useRefreshMobileProfileStatus: jest.fn(),
}));

import { TrainingProfileStage } from "./OnboardingScreen";
import { emptyProfileFormValues } from "./onboardingForms";

test("sets the primary preset after training-day selection and supports custom Friday", () => {
  const values = emptyProfileFormValues();
  values.experience_level = "beginner";
  values.training_location = "gym";
  values.session_duration_minutes = "45";
  values.training_intensity = "moderate";

  render(
    <TrainingProfileStage
      busy={false}
      initialValues={values}
      onBack={jest.fn(() => true)}
      onSubmit={jest.fn()}
    />,
  );

  fireEvent.press(screen.getByRole("button", { name: "ادامه" }));
  const trainingDays = screen.getByLabelText("روزهای تمرین در هفته");
  fireEvent.changeText(trainingDays, "4");

  expect(screen.getByRole("radio", { name: "شنبه · یکشنبه · سه‌شنبه · چهارشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
  fireEvent.press(screen.getByRole("radio", { name: "یکشنبه · دوشنبه · چهارشنبه · پنجشنبه" }));
  expect(screen.getByRole("radio", { name: "یکشنبه · دوشنبه · چهارشنبه · پنجشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });

  fireEvent.press(screen.getByRole("radio", { name: "روزهای تمرین را خودم انتخاب می‌کنم" }));
  const custom = screen.getByLabelText("روزهای دلخواه");
  expect(within(custom).getAllByRole("checkbox")).toHaveLength(7);
  fireEvent.press(within(custom).getByRole("checkbox", { name: "یکشنبه" }));
  expect(within(custom).getByRole("checkbox", { name: "جمعه" }).props.accessibilityState)
    .toMatchObject({ disabled: false });
});

test("resets the weekday selection to the primary preset when the count changes", () => {
  const values = emptyProfileFormValues();
  values.experience_level = "beginner";

  render(
    <TrainingProfileStage
      busy={false}
      initialValues={values}
      onBack={jest.fn(() => true)}
      onSubmit={jest.fn()}
    />,
  );

  fireEvent.press(screen.getByRole("button", { name: "ادامه" }));
  const trainingDays = screen.getByLabelText("روزهای تمرین در هفته");
  fireEvent.changeText(trainingDays, "4");
  fireEvent.changeText(trainingDays, "3");

  expect(screen.getByRole("radio", { name: "شنبه · دوشنبه · چهارشنبه" }).props.accessibilityState)
    .toMatchObject({ selected: true });
});
