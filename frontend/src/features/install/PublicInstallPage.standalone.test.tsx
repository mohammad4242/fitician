import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import i18n from "i18next";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { PublicInstallPage } from "./PublicInstallPage";

const originalUserAgent = navigator.userAgent;
afterEach(async () => {
  cleanup();
  await i18n.changeLanguage("fa");
  Object.defineProperty(navigator, "userAgent", { configurable: true, value: originalUserAgent });
});

it("renders the localized standalone notice above the tabs, hides the hero line, and shows store icons", async () => {
  render(<MemoryRouter><PublicInstallPage
    standaloneNotice={{ fa: "برای نصب و استفاده، فیلترشکنتو خاموش کن.", en: "Turn off your VPN to install and use Fitician." }}
    hideHeroDescription
    storeIcons={{ cafeBazaar: "/cafe-bazaar.svg", myket: "/myket.svg" }}
    continueHref="https://fitician.fit/"
    iosInstallHref="https://fitician.fit/install"
    copyHref="https://fitician.fit/install"
  /></MemoryRouter>);

  const notice = screen.getByText("برای نصب و استفاده، فیلترشکنتو خاموش کن.");
  expect(notice).toBeInTheDocument();
  expect(notice.compareDocumentPosition(screen.getByRole("tablist")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByText("روی اندروید یا آیفون؛ همیشه دم دست.")).not.toBeInTheDocument();
  expect(document.querySelector('img[src="/cafe-bazaar.svg"]')).toBeInTheDocument();
  expect(document.querySelector('img[src="/myket.svg"]')).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /دانلود مستقیم APK/ })).toHaveAttribute("href", "/download/android");
  expect(screen.getByRole("link", { name: "ورود به فیتیشن" })).toHaveAttribute("href", "https://fitician.fit/");

  fireEvent.click(screen.getByRole("button", { name: "English" }));
  expect(await screen.findByText("Turn off your VPN to install and use Fitician.")).toBeInTheDocument();
});

it("sends standalone iPhone users to the canonical install origin", () => {
  Object.defineProperty(navigator, "userAgent", { configurable: true, value: "Mozilla/5.0 (iPhone)" });
  render(<MemoryRouter><PublicInstallPage iosInstallHref="https://fitician.fit/install" /></MemoryRouter>);

  expect(screen.getByText("روی اندروید یا آیفون؛ همیشه دم دست.")).toBeInTheDocument();
  expect(screen.queryByText(/Turn off your VPN/)).not.toBeInTheDocument();
  expect(document.querySelector(".public-install__standalone-notice")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "آیفون" }));
  expect(screen.getByRole("link", { name: "نصب وب‌اپلیکیشن فیتیشن" })).toHaveAttribute("href", "https://fitician.fit/install");
  expect(screen.getByText((_, element) => element?.classList.contains("public-install__step-copy") === true
    && element.textContent?.includes("در پایان Add را بزن.") === true)).toBeInTheDocument();
});
