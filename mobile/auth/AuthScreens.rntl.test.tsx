import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { Dimensions, KeyboardAvoidingView, ScrollView } from "react-native";
import { requestAndroidGoogleIdToken } from "./googleNativeCredential";
import { SafeAreaProvider } from "react-native-safe-area-context";
import type { PublicSignupCampaign, TransportRequest } from "@fitician/core";

jest.mock("expo-router", () => ({ useLocalSearchParams: jest.fn(), useRouter: jest.fn() }));
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("./MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("./AppleSignIn", () => ({ useAppleSignIn: jest.fn() }));
jest.mock("./GoogleSignIn", () => ({ useGoogleSignIn: jest.fn() }));
jest.mock("expo-apple-authentication", () => ({
  AppleAuthenticationButton: () => null,
  AppleAuthenticationButtonStyle: { BLACK: "black" },
  AppleAuthenticationButtonType: { SIGN_IN: "sign-in" },
}));

import { useLocalSearchParams, useRouter } from "expo-router";

import { useAppleSignIn } from "./AppleSignIn";
import type { AppleAuthCredential } from "./appleCredential";
import { useGoogleSignIn } from "./GoogleSignIn";
import { useMobileAuth } from "./MobileAuthProvider";
import { authStyles } from "./authStyles";
import RegisterScreen from "../app/(auth)/auth/register";
import SignInScreen from "../app/(auth)/auth/sign-in";
import VerifyEmailScreen from "../app/(auth)/auth/verify-email";

const mockPush = jest.fn();
const mockReplace = jest.fn();
type MockAuth = {
  busy: boolean;
  register: jest.Mock<(credentials: { email: string; password: string }) => Promise<unknown>>;
  request: jest.Mock<(request: TransportRequest) => Promise<PublicSignupCampaign | null>>;
  sendPhoneOtp: jest.Mock<(phoneNumber: string) => Promise<{ retry_after_seconds: number }>>;
  sessionExpired: boolean;
  signInWithGoogle: jest.Mock<(credential: string) => Promise<unknown>>;
  signInWithApple: jest.Mock<(credential: unknown) => Promise<unknown>>;
  signInWithPassword: jest.Mock<(credentials: { email: string; password: string }) => Promise<unknown>>;
  startupError: string | null;
  verifyEmail: jest.Mock<(token: string) => Promise<void>>;
  verifyPhoneOtp: jest.Mock<(phoneNumber: string, code: string) => Promise<unknown>>;
};
let mockAuth: MockAuth;
let mockGoogleCredential: jest.Mock<() => Promise<string>>;
let mockAppleCredential: jest.Mock<() => Promise<AppleAuthCredential>>;
const mockUseLocalSearchParams = jest.mocked(useLocalSearchParams);
const mockUseRouter = jest.mocked(useRouter);
const mockUseAppleSignIn = jest.mocked(useAppleSignIn);
const mockUseGoogleSignIn = jest.mocked(useGoogleSignIn);
const mockUseMobileAuth = jest.mocked(useMobileAuth);
const registerCampaign = {
  code: "register-bonus",
  package_code: "complete" as const,
  duration_days: 42,
  term_weeks: 6 as const,
  available_until: null,
  public_badge_fa: "هدیه ثبت‌نام",
  public_badge_en: "Signup Gift",
  public_title_fa: "حساب کامل مهمان فیتیشن",
  public_title_en: "Your complete account is on us",
  public_message_fa: "ثبت‌نام کن و شروع کن.",
  public_message_en: "Create your account and start.",
  public_cta_fa: "هدیه‌ام رو بگیر",
  public_cta_en: "Claim my gift",
  show_on_landing: true,
  show_on_register: true,
};

function renderScreen(screenComponent: React.ReactElement, height = 800, width = 390) {
  return render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height, width, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      {screenComponent}
    </SafeAreaProvider>,
  );
}

function renderSignIn() {
  return renderScreen(<SignInScreen />);
}

function renderRegister() {
  return renderScreen(<RegisterScreen />);
}

beforeEach(() => {
  mockPush.mockClear();
  mockReplace.mockClear();
  mockAuth = {
    busy: false,
    register: jest.fn<MockAuth["register"]>().mockResolvedValue({}),
    request: jest.fn<(request: TransportRequest) => Promise<PublicSignupCampaign | null>>(
      () => new Promise<never>(() => undefined),
    ),
    sendPhoneOtp: jest.fn<MockAuth["sendPhoneOtp"]>().mockResolvedValue({ retry_after_seconds: 2 }),
    sessionExpired: false,
    signInWithApple: jest.fn<MockAuth["signInWithApple"]>().mockResolvedValue({}),
    signInWithGoogle: jest.fn<MockAuth["signInWithGoogle"]>().mockResolvedValue({}),
    signInWithPassword: jest.fn<MockAuth["signInWithPassword"]>().mockResolvedValue({}),
    startupError: null,
    verifyEmail: jest.fn<MockAuth["verifyEmail"]>().mockResolvedValue(undefined),
    verifyPhoneOtp: jest.fn<MockAuth["verifyPhoneOtp"]>().mockResolvedValue({}),
  };
  mockGoogleCredential = jest.fn<() => Promise<string>>().mockResolvedValue("google-credential");
  mockAppleCredential = jest.fn<() => Promise<AppleAuthCredential>>().mockResolvedValue({
    email: null,
    fullName: null,
    identityToken: "apple-credential",
    nonce: "nonce-1",
  });
  mockUseRouter.mockReturnValue({ push: mockPush, replace: mockReplace } as never);
  mockUseLocalSearchParams.mockReturnValue({} as never);
  mockUseGoogleSignIn.mockReturnValue({
    available: true,
    ready: true,
    signIn: mockGoogleCredential,
  });
  mockUseAppleSignIn.mockReturnValue({
    available: false,
    ready: true,
    signIn: mockAppleCredential,
  });
  mockUseMobileAuth.mockReturnValue(mockAuth as never);
});

test("presents the Web auth hierarchy with native fields and method selection", () => {
  renderSignIn();

  expect(screen.getByText("خوش برگشتی")).toBeTruthy();
  expect(screen.getByRole("header", { name: "ادامهٔ مسیر از همین‌جا" })).toBeTruthy();
  expect(screen.getByTestId("auth-form-panel")).toBeTruthy();
  expect(screen.queryByTestId("auth-cinematic-shell")).toBeNull();
  expect(screen.getByTestId("segmented-control")).toBeTruthy();
  expect(screen.getByRole("radio", { name: "ایمیل" })).toBeTruthy();
  expect(screen.getAllByLabelText("ایمیل")).toHaveLength(2);
  expect(screen.getByRole("button", { name: "ورود به فیتیشن" })).toBeTruthy();
  expect(screen.getByText("یا")).toBeTruthy();
  expect(screen.getByText("هنوز حساب نداری؟")).toBeTruthy();
});

test("uses the quiet Web-aligned scaffold without the old decorative accent rule", () => {
  expect(authStyles.brand).toBeDefined();
  expect("accentRule" in authStyles).toBe(false);
});

test("renders a public Signup Bonus above Register without adding a second CTA", async () => {
  mockAuth.request.mockResolvedValue(registerCampaign);
  renderRegister();

  expect(await screen.findByTestId("signup-campaign-card")).toBeTruthy();
  expect(screen.getByText("حساب کامل مهمان فیتیشن")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "هدیه‌ام رو بگیر" })).toBeNull();
  expect(screen.getByRole("button", { name: "ساخت حساب" })).toBeTruthy();
});

test("keeps the phone method inline and preserves the forgot-password source", async () => {
  mockUseLocalSearchParams.mockReturnValue({ source: "public-onboarding" } as never);
  renderSignIn();

  fireEvent.press(screen.getByRole("radio", { name: "شماره موبایل" }));
  expect(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹")).toBeTruthy();
  expect(screen.queryByPlaceholderText("name@example.com")).toBeNull();

  fireEvent.changeText(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789");
  fireEvent.press(screen.getByRole("button", { name: "ارسال کد ورود" }));
  await waitFor(() => expect(mockAuth.sendPhoneOtp).toHaveBeenCalledWith("09123456789"));
  expect(mockPush).not.toHaveBeenCalledWith("/auth/phone-otp");

  fireEvent.press(screen.getByRole("radio", { name: "ایمیل" }));
  fireEvent.press(screen.getByRole("button", { name: "فراموشی رمز عبور؟" }));

  expect(mockPush).toHaveBeenCalledWith({
    pathname: "/auth/forgot-password",
    params: { source: "public-onboarding" },
  });
});

test("submits the Web email login path to the public onboarding destination", async () => {
  mockUseLocalSearchParams.mockReturnValue({ source: "public-onboarding" } as never);
  renderSignIn();

  fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.press(screen.getByRole("button", { name: "ورود به فیتیشن" }));

  await waitFor(() => expect(mockAuth.signInWithPassword).toHaveBeenCalledWith({ email: "person@example.com", password: "abcdefgh" }));
  expect(mockReplace).toHaveBeenCalledWith({
    pathname: "/onboarding",
    params: { source: "public-onboarding" },
  });
});

test("renders inline OTP verification and resend countdown", async () => {
  jest.useFakeTimers();
  try {
    renderSignIn();
    fireEvent.press(screen.getByRole("radio", { name: "شماره موبایل" }));
    fireEvent.changeText(screen.getByPlaceholderText("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789");
    fireEvent.press(screen.getByRole("button", { name: "ارسال کد ورود" }));

    await waitFor(() => expect(screen.getByLabelText("کد ورود")).toBeTruthy());
    expect(screen.getByText("ارسال مجدد تا ۲ ثانیه")).toBeTruthy();

    act(() => jest.advanceTimersByTime(2_000));
    fireEvent.press(screen.getByRole("button", { name: "ارسال مجدد کد" }));
    expect(mockAuth.sendPhoneOtp).toHaveBeenCalledTimes(2);

    fireEvent.changeText(screen.getByLabelText("کد ورود"), "123456");
    fireEvent.press(screen.getByRole("button", { name: "تأیید و ورود" }));
    await waitFor(() => expect(mockAuth.verifyPhoneOtp).toHaveBeenCalledWith("09123456789", "123456"));
  } finally {
    jest.useRealTimers();
  }
});

test("uses Google and keeps the public onboarding destination", async () => {
  mockUseLocalSearchParams.mockReturnValue({ source: "public-onboarding" } as never);
  renderSignIn();

  const googleIcon = screen.getByTestId("google-brand-icon");
  expect(googleIcon.parent?.type).not.toBe("Text");
  fireEvent.press(screen.getByRole("button", { name: "ادامه با گوگل" }));

  await waitFor(() => expect(mockAuth.signInWithGoogle).toHaveBeenCalledWith("google-credential"));
  expect(mockReplace).toHaveBeenCalledWith({
    pathname: "/onboarding",
    params: { source: "public-onboarding" },
  });
});

test("does not repeat email verification when the auth snapshot changes", async () => {
  mockUseLocalSearchParams.mockReturnValue({ token: "verification-token" } as never);
  const firstAuth = mockAuth;
  const view = renderScreen(<VerifyEmailScreen />);

  await waitFor(() => expect(firstAuth.verifyEmail).toHaveBeenCalledTimes(1));

  mockUseMobileAuth.mockReturnValue({ ...firstAuth, busy: true } as never);
  view.rerender(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height: 800, width: 390, x: 0, y: 0 },
        insets: { bottom: 0, left: 0, right: 0, top: 0 },
      }}
    >
      <VerifyEmailScreen />
    </SafeAreaProvider>,
  );

  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(firstAuth.verifyEmail).toHaveBeenCalledTimes(1);
});

test("keeps Register in the Web field order and validates confirmation", async () => {
  renderRegister();

  expect(screen.getByLabelText("ایمیل")).toBeTruthy();
  expect(screen.getByLabelText("رمز عبور")).toBeTruthy();
  expect(screen.getByLabelText("تکرار رمز عبور")).toBeTruthy();
  expect(screen.getByText("حداقل ۸ نویسه")).toBeTruthy();

  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.changeText(screen.getByLabelText("تکرار رمز عبور"), "different");
  fireEvent.press(screen.getByRole("button", { name: "ساخت حساب" }));

  await waitFor(() => expect(screen.getByText("تکرار رمز عبور یکسان نیست.")).toBeTruthy());
  expect(mockAuth.register).not.toHaveBeenCalled();
});

test("preserves the public onboarding source through Register", async () => {
  mockUseLocalSearchParams.mockReturnValue({ source: "public-onboarding" } as never);
  renderRegister();

  fireEvent.changeText(screen.getByLabelText("ایمیل"), "person@example.com");
  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.changeText(screen.getByLabelText("تکرار رمز عبور"), "abcdefgh");
  fireEvent.press(screen.getByRole("button", { name: "ساخت حساب" }));

  await waitFor(() => expect(mockAuth.register).toHaveBeenCalledWith({ email: "person@example.com", password: "abcdefgh" }));
  expect(mockReplace).toHaveBeenCalledWith({
    pathname: "/onboarding",
    params: { source: "public-onboarding" },
  });
});

for (const state of [{ available: false, ready: true }, { available: true, ready: false }]) {
  test(`disables Google when unavailable or not ready ${JSON.stringify(state)}`, () => {
    mockUseGoogleSignIn.mockReturnValue({ ...state, signIn: mockGoogleCredential });
    renderSignIn();
    const button = screen.getByRole("button", { name: "ادامه با گوگل" });
    expect(button.props.accessibilityState.disabled).toBe(true);
    fireEvent.press(button);
    expect(mockGoogleCredential).not.toHaveBeenCalled();
  });
}

test("keeps email usable while Google is pending and after Google rejects", async () => {
  let reject!: (error: Error) => void;
  mockGoogleCredential.mockImplementation(() => new Promise((_resolve, rejectPromise) => { reject = rejectPromise; }));
  renderSignIn();
  const googleButton = () => screen.getByRole("button", { name: "ادامه با گوگل" });
  fireEvent.press(googleButton());
  expect(googleButton().props.accessibilityState).toMatchObject({ busy: true, disabled: true });
  fireEvent.press(googleButton());
  expect(mockGoogleCredential).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "ورود به فیتیشن" }).props.accessibilityState.disabled).toBe(false);
  await act(async () => { reject(new Error("failed")); });
  expect(googleButton().props.accessibilityState.busy).toBe(false);
  fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.press(screen.getByRole("button", { name: "ورود به فیتیشن" }));
  await waitFor(() => expect(mockAuth.signInWithPassword).toHaveBeenCalled());
});

test("discards a Google credential returned after email sign-in", async () => {
  let settle!: (token: string) => void;
  mockGoogleCredential.mockImplementation(() => new Promise((resolve) => { settle = resolve; }));
  renderSignIn();
  fireEvent.press(screen.getByRole("button", { name: "ادامه با گوگل" }));
  fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
  fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
  fireEvent.press(screen.getByRole("button", { name: "ورود به فیتیشن" }));
  await waitFor(() => expect(mockAuth.signInWithPassword).toHaveBeenCalled());
  await act(async () => { settle("late-google-credential"); });
  expect(mockAuth.signInWithGoogle).not.toHaveBeenCalled();
  expect(mockReplace).toHaveBeenCalledTimes(1);
});

// RNTL verifies the scrolling/touch contract, not native layout geometry.
test("preserves scrolling and email touch submission at small height with large fonts", async () => {
  const originalWindow = Dimensions.get("window");
  const originalScreen = Dimensions.get("screen");
  act(() => Dimensions.set({ window: { width: 320, height: 320, scale: 1, fontScale: 2 }, screen: { width: 320, height: 480, scale: 1, fontScale: 2 } }));
  try {
    mockGoogleCredential.mockImplementation(() => new Promise(() => undefined));
    const view = renderScreen(<SignInScreen />, 320, 320);
    const scroll = view.UNSAFE_getByType(ScrollView);
    expect(scroll.props.scrollEnabled).not.toBe(false);
    expect(scroll.props.keyboardShouldPersistTaps).toBe("handled");
    expect(view.UNSAFE_getByType(KeyboardAvoidingView).props.enabled).toBe(true);
    fireEvent.press(screen.getByRole("button", { name: "ادامه با گوگل" }));
    fireEvent.scroll(scroll, { nativeEvent: { contentOffset: { y: 500, x: 0 }, contentSize: { height: 1200, width: 320 }, layoutMeasurement: { height: 320, width: 320 } } });
    fireEvent.changeText(screen.getAllByLabelText("ایمیل")[1], "person@example.com");
    fireEvent.changeText(screen.getByLabelText("رمز عبور"), "abcdefgh");
    fireEvent.press(screen.getByRole("button", { name: "ورود به فیتیشن" }));
    await waitFor(() => expect(mockAuth.signInWithPassword).toHaveBeenCalledWith({ email: "person@example.com", password: "abcdefgh" }));
  } finally { act(() => Dimensions.set({ window: originalWindow, screen: originalScreen })); }
});

test("stops the Google loader at the native deadline and leaves email enabled", async () => {
  jest.useFakeTimers();
  try {
    mockGoogleCredential.mockImplementation(() => requestAndroidGoogleIdToken({
      configure: () => undefined,
      checkPlayServices: () => new Promise(() => undefined),
      signIn: async () => ({ data: null, type: "cancelled" }),
      createAccount: async () => ({ data: null, type: "cancelled" }),
      presentExplicitSignIn: async () => ({ data: null, type: "cancelled" }),
    }, "web.apps.googleusercontent.com"));
    renderSignIn();
    fireEvent.press(screen.getByRole("button", { name: "ادامه با گوگل" }));
    await act(async () => { await jest.advanceTimersByTimeAsync(45_000); });
    expect(screen.getByRole("button", { name: "ادامه با گوگل" }).props.accessibilityState.busy).toBe(false);
    expect(screen.getByRole("button", { name: "ورود به فیتیشن" }).props.accessibilityState.disabled).toBe(false);
    expect(screen.getByText(/مهلت ورود با گوگل تمام شد/u)).toBeTruthy();
    expect(mockAuth.signInWithGoogle).not.toHaveBeenCalled();
  } finally { jest.useRealTimers(); }
});
