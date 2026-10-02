jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
}));
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react-native";
import { jest, test, expect } from "@jest/globals";
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
}));
jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../ui/layout", () => ({
  Screen: ({ children }: { children: React.ReactNode }) => children,
}));
jest.mock("../ui/rtl", () => ({
  ...(jest.requireActual("../ui/rtl") as Record<string, unknown>),
  languageForDirection: () => "fa",
}));
import { useMobileAuth } from "../auth/MobileAuthProvider";
import { SupportScreen } from "./SupportScreen";
test("renders shared help and searches Persian article content", () => {
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request: jest.fn() } as never);
  render(<SupportScreen mode="home" />);
  fireEvent.changeText(screen.getByLabelText("جست‌وجو در مرکز راهنما"), "ورود");
  expect(screen.getByText("نمی‌توانم وارد حسابم شوم")).toBeTruthy();
});
test("renders member ticket list empty state", async () => {
  const request = jest.fn(async () => ({ items: [], older_cursor: null }));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<SupportScreen mode="tickets" />);
  await waitFor(() =>
    expect(screen.getByText("هنوز درخواستی ثبت نکرده‌ای")).toBeTruthy(),
  );
});
test("retries a failed request with the same id", async () => {
  const request = jest
    .fn<() => Promise<never>>()
    .mockRejectedValue(new Error("offline"));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request } as never);
  render(<SupportScreen mode="new" />);
  fireEvent.changeText(screen.getByLabelText("موضوع"), "Help");
  fireEvent.changeText(screen.getByLabelText("توضیحات"), "Question");
  fireEvent.press(screen.getByRole("button", { name: "ارسال درخواست" }));
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
  await screen.findByText("ارتباط برقرار نشد. دوباره تلاش کن.");
  fireEvent.press(screen.getByRole("button", { name: "English" }));
  fireEvent.press(screen.getByRole("button", { name: "Submit a request" }));
  await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
  expect(request.mock.calls[0]).toEqual(request.mock.calls[1]);
  fireEvent.press(screen.getByRole("button", { name: "فارسی" }));
});
test("clears private tickets immediately when the account changes", async () => {
  const request = jest.fn(async () => ({
    items: [
      {
        id: "first-ticket",
        subject: "Private request",
        category: "technical",
        status: "open",
        last_activity_at: "2026-10-01T10:00:00Z",
      },
    ],
    older_cursor: null,
  }));
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "first" }, request } as never);
  const view = render(<SupportScreen mode="tickets" />);
  expect(await screen.findByText("Private request")).toBeTruthy();
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({
      user: { id: "second" },
      request: jest.fn(() => new Promise(() => undefined)),
    } as never);
  view.rerender(<SupportScreen mode="tickets" />);
  expect(screen.queryByText("Private request")).toBeNull();
});
test("supports English Help content and LTR headings", () => {
  jest
    .mocked(useMobileAuth)
    .mockReturnValue({ user: { id: "member" }, request: jest.fn() } as never);
  render(<SupportScreen mode="home" />);
  fireEvent.press(screen.getByRole("button", { name: "English" }));
  expect(screen.getByText("How can we help?")).toHaveStyle({
    writingDirection: "ltr",
  });
  fireEvent.changeText(
    screen.getByLabelText("Search the Help Center"),
    "delete account",
  );
  expect(screen.getByText("How do I delete my account?")).toBeTruthy();
});
