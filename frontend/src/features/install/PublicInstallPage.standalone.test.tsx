import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { PublicInstallPage } from "./PublicInstallPage";

const originalUserAgent = navigator.userAgent;
afterEach(() => {
  cleanup();
  Object.defineProperty(navigator, "userAgent", { configurable: true, value: originalUserAgent });
});

it("renders standalone notice and points Android download to the existing redirect", () => {
  render(<MemoryRouter><PublicInstallPage
    topNotice="برای نصب اپلیکیشن فیتیشن، فیلترشکن خود را خاموش کنید."
    continueHref="https://fitician.fit/"
    iosInstallHref="https://fitician.fit/install"
    copyHref="https://fitician.fit/install"
  /></MemoryRouter>);

  expect(screen.getByText("برای نصب اپلیکیشن فیتیشن، فیلترشکن خود را خاموش کنید.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /دانلود مستقیم APK/ })).toHaveAttribute("href", "/download/android");
  expect(screen.getByRole("link", { name: "ورود به فیتیشن" })).toHaveAttribute("href", "https://fitician.fit/");
});

it("sends standalone iPhone users to the canonical install origin", () => {
  Object.defineProperty(navigator, "userAgent", { configurable: true, value: "Mozilla/5.0 (iPhone)" });
  render(<MemoryRouter><PublicInstallPage iosInstallHref="https://fitician.fit/install" /></MemoryRouter>);

  fireEvent.click(screen.getByRole("tab", { name: "آیفون" }));
  expect(screen.getByRole("link", { name: "نصب وب‌اپلیکیشن فیتیشن" })).toHaveAttribute("href", "https://fitician.fit/install");
  expect(screen.getByText((_, element) => element?.classList.contains("public-install__step-copy") === true
    && element.textContent?.includes("در پایان Add را بزن.") === true)).toBeInTheDocument();
});
