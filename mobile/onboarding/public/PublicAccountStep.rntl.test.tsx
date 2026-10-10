import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { ScrollView, StyleSheet } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("../../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../../auth/GoogleSignIn", () => ({ useGoogleSignIn: jest.fn() }));
jest.mock("expo-router", () => ({ useRouter: () => ({ replace: mockReplace }) }));
jest.mock("../../ui/navigation/BackBehaviorProvider", () => ({ useAndroidBackHandler: jest.fn() }));
jest.mock("../publicOnboardingDraftStore", () => ({
  SecurePublicOnboardingDraftStore: jest.fn().mockImplementation(() => ({
    load: mockLoadDraft,
    save: jest.fn(),
  })),
}));

import { useGoogleSignIn } from "../../auth/GoogleSignIn";
import { useMobileAuth } from "../../auth/MobileAuthProvider";
import { publicOnboardingStyles } from "./publicOnboardingStyles";
import { PublicAccountStep } from "./PublicAccountStep";
import { PublicOnboardingScreen } from "../PublicOnboardingScreen";
import { createInitialOnboardingState, transitionOnboardingState } from "@fitician/core/onboarding";

const mockReplace = jest.fn();
const mockLoadDraft = jest.fn<() => Promise<unknown>>();

const mockUseGoogleSignIn = jest.mocked(useGoogleSignIn);
const mockUseMobileAuth = jest.mocked(useMobileAuth);
type MockAuth = {
  busy: boolean;
  register: jest.Mock<(credentials: { email: string; password: string }) => Promise<unknown>>;
  sendPhoneOtp: jest.Mock<(phoneNumber: string) => Promise<{ retry_after_seconds: number }>>;
  signInWithGoogle: jest.Mock<(credential: string) => Promise<unknown>>;
  signInWithPassword: jest.Mock<(credentials: { email: string; password: string }) => Promise<unknown>>;
  user: null;
  verifyPhoneOtp: jest.Mock<(phoneNumber: string, code: string) => Promise<unknown>>;
};
let mockAuth: MockAuth;
let mockGoogleCredential: jest.Mock<() => Promise<string>>;

function renderAccount(onAuthenticated = jest.fn(), onEdit = jest.fn()) {
  return render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height: 800, width: 390, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      <PublicAccountStep mode="training" onAuthenticated={onAuthenticated} onEdit={onEdit} />
    </SafeAreaProvider>,
  );
}

beforeEach(() => {
  mockAuth = {
    busy: false,
    register: jest.fn<MockAuth["register"]>().mockResolvedValue({}),
    sendPhoneOtp: jest.fn<MockAuth["sendPhoneOtp"]>().mockResolvedValue({ retry_after_seconds: 2 }),
    signInWithGoogle: jest.fn<MockAuth["signInWithGoogle"]>().mockResolvedValue({}),
    signInWithPassword: jest.fn<MockAuth["signInWithPassword"]>().mockResolvedValue({}),
    user: null,
    verifyPhoneOtp: jest.fn<MockAuth["verifyPhoneOtp"]>().mockResolvedValue({}),
  };
  mockGoogleCredential = jest.fn<() => Promise<string>>().mockResolvedValue("google-credential");
  mockUseMobileAuth.mockReturnValue(mockAuth as never);
  mockUseGoogleSignIn.mockReturnValue({
    available: true,
    ready: true,
    signIn: mockGoogleCredential,
  });
});

test("matches the Web final account hierarchy and email registration handoff", async () => {
  const onAuthenticated = jest.fn();
  const onEdit = jest.fn();
  renderAccount(onAuthenticated, onEdit);

  expect(screen.getByText("آخرین قدم")).toBeTruthy();
  expect(screen.getByRole("header", { name: "حالا حسابت را بساز" })).toBeTruthy();
  expect(screen.getByText("مسیر امن انتقال اطلاعات")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Apple به‌زودی" })).toBeDisabled();

  fireEvent.press(screen.getByRole("button", { name: "بازگشت و ویرایش پاسخ‌ها" }));
  expect(onEdit).toHaveBeenCalledTimes(1);

  fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.changeText(screen.getByLabelText("تکرار رمز عبور"), "abcdefgh");
  fireEvent.press(screen.getByRole("button", { name: "ساخت حساب و ذخیره پاسخ‌ها" }));

  await waitFor(() => expect(mockAuth.register).toHaveBeenCalledWith({ email: "person@example.com", password: "abcdefgh" }));
  expect(onAuthenticated).toHaveBeenCalledTimes(1);
});

test("uses the Web mobile account card layout", () => {
  renderAccount();

  expect(StyleSheet.flatten(screen.getByTestId("public-account-providers").props.style)).toMatchObject({
    flexDirection: "column",
  });
  expect(screen.getByTestId("public-account-card")).toBeTruthy();
});

test("supports existing-account login, Google, and inline phone OTP resend", async () => {
  jest.useFakeTimers();
  try {
    const onAuthenticated = jest.fn();
    renderAccount(onAuthenticated);

    fireEvent.press(screen.getByRole("button", { name: "قبلاً حساب ساخته‌ام" }));
    expect(screen.queryByLabelText("تکرار رمز عبور")).toBeNull();
    fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
    fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
    fireEvent.press(screen.getByRole("button", { name: "ورود و ذخیره پاسخ‌ها" }));
    await waitFor(() => expect(mockAuth.signInWithPassword).toHaveBeenCalledWith({ email: "person@example.com", password: "abcdefgh" }));

    fireEvent.press(screen.getByRole("tab", { name: "شماره تلفن" }));
    fireEvent.changeText(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789");
    fireEvent.press(screen.getByRole("button", { name: "ارسال کد ورود" }));
    await waitFor(() => expect(screen.getByLabelText("کد ورود")).toBeTruthy());
    expect(mockAuth.sendPhoneOtp).toHaveBeenCalledWith("09123456789");
    expect(screen.getByLabelText("کد ورود").props.autoFocus).toBe(true);

    act(() => jest.advanceTimersByTime(2_000));
    fireEvent.press(screen.getByRole("button", { name: "ارسال دوباره کد" }));
    await waitFor(() => expect(mockAuth.sendPhoneOtp).toHaveBeenCalledTimes(2));

    fireEvent.changeText(screen.getByLabelText("کد ورود"), "123456");
    fireEvent.press(screen.getByRole("button", { name: "تأیید و ذخیره پاسخ‌ها" }));
    await waitFor(() => expect(mockAuth.verifyPhoneOtp).toHaveBeenCalledWith("09123456789", "123456"));

    fireEvent.press(screen.getByRole("tab", { name: "ایمیل" }));
    fireEvent.press(screen.getByRole("button", { name: "Google" }));
    await waitFor(() => expect(mockAuth.signInWithGoogle).toHaveBeenCalledWith("google-credential"));
    expect(onAuthenticated).toHaveBeenCalled();
  } finally {
    jest.useRealTimers();
  }
});

// These assertions protect the native layout contract. Physical IME/viewport
// acceptance is separate; Jest does not calculate Yoga layout or tap geometry.
test("restored public registration uses a scroll container and content-height account surface", async () => {
  const shared = {
    birth_date: "1992-05-12", current_weight_kg: 70, display_name: "QA",
    fitness_goal: "build_muscle" as const, height_cm: 170, sex: "male" as const,
  };
  const selected = transitionOnboardingState(createInitialOnboardingState(), { type: "select_product_mode", mode: "training" });
  const answered = transitionOnboardingState(selected, { type: "save_shared_profile", profile: shared });
  const draft = transitionOnboardingState(answered, { type: "save_training_profile", profile: {
    ...shared, shoulder_circumference_cm: null, waist_circumference_cm: null,
    hip_circumference_cm: null, experience_level: "beginner", training_age_months: null,
    training_days_per_week: 3, preferred_weekdays: null, priority_muscles: null,
    training_location: "gym", home_training_setup: null, available_equipment: null,
    session_duration_minutes: 45, training_intensity: "moderate", training_cautions: [],
    plan_duration_weeks: 4,
  } });
  mockLoadDraft.mockResolvedValue({ status: "valid", state: draft });
  render(
    <SafeAreaProvider initialMetrics={{
      frame: { width: 360, height: 640, x: 0, y: 0 },
      insets: { top: 24, bottom: 24, left: 0, right: 0 },
    }}>
      <PublicOnboardingScreen />
    </SafeAreaProvider>,
  );
  await screen.findByTestId("public-account-card");
  const scroll = screen.UNSAFE_getByType(ScrollView);
  expect(scroll.props.keyboardShouldPersistTaps).toBe("handled");
  const surface = screen.getByTestId("public-account-surface");
  const surfaceStyle = StyleSheet.flatten(surface.props.style);
  expect(surfaceStyle.flex).toBeUndefined();
  expect(surfaceStyle.justifyContent).toBe("flex-start");

  fireEvent.press(screen.getByRole("tab", { name: "شماره تلفن" }));
  fireEvent.changeText(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789");
  fireEvent.press(screen.getByRole("button", { name: "ارسال کد ورود" }));
  await screen.findByLabelText("کد ورود");
  expect(screen.getByLabelText("کد ورود").props.autoFocus).toBe(true);
  fireEvent.changeText(screen.getByLabelText("کد ورود"), "123456");
  fireEvent.press(screen.getByRole("button", { name: "تأیید و ذخیره پاسخ‌ها" }));
  await waitFor(() => expect(mockReplace).toHaveBeenCalledWith({ pathname: "/onboarding", params: { source: "public-onboarding" } }));
  expect(mockLoadDraft).toHaveBeenCalledTimes(1);
});

test("keeps phone verification retryable after validation and backend errors", async () => {
  const onAuthenticated = jest.fn();
  mockAuth.verifyPhoneOtp.mockRejectedValueOnce(new Error("network unavailable"));
  renderAccount(onAuthenticated);
  fireEvent.press(screen.getByRole("tab", { name: "شماره تلفن" }));
  fireEvent.changeText(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789");
  fireEvent.press(screen.getByRole("button", { name: "ارسال کد ورود" }));
  await screen.findByLabelText("کد ورود");
  const confirm = () => screen.getByRole("button", { name: "تأیید و ذخیره پاسخ‌ها" });
  fireEvent.press(confirm());
  expect(mockAuth.verifyPhoneOtp).not.toHaveBeenCalled();
  expect(onAuthenticated).not.toHaveBeenCalled();
  fireEvent.changeText(screen.getByLabelText("کد ورود"), "123456");
  fireEvent.press(confirm());
  await waitFor(() => expect(mockAuth.verifyPhoneOtp).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(confirm()).not.toBeDisabled());
  expect(onAuthenticated).not.toHaveBeenCalled();
  fireEvent.press(confirm());
  await waitFor(() => expect(onAuthenticated).toHaveBeenCalledTimes(1));
});

test("lets resend and change-number controls wrap at large font and display sizes", () => {
  expect(StyleSheet.flatten(publicOnboardingStyles.phoneActions)).toMatchObject({ flexWrap: "wrap" });
});
