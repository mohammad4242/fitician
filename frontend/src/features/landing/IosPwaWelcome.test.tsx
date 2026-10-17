import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import "../../i18n";
import androidGymImage from "../../../../mobile/assets/landing/pic_land.jpg";
import { PublicLandingPage } from "./PublicLandingPage";

vi.mock("../campaigns/publicCampaignApi", () => ({ getActiveSignupCampaign: vi.fn(async () => null) }));
const html = readFileSync("index.html", "utf8");
const bootstrap = html.match(/<script id="ios-pwa-environment">([\s\S]*?)<\/script>/)?.[1] ?? "";

function environment(agent: string, safari = false, display = false, platform = "", touches = 0) {
  vi.stubGlobal("navigator", { userAgent: agent, standalone: safari, platform, maxTouchPoints: touches });
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    matches: query === "(display-mode: standalone)" && display,
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
  Function(bootstrap)();
}
afterEach(() => { vi.unstubAllGlobals(); delete document.documentElement.dataset.iosPwa; });

it.each([
  ["iPhone", true, false, "", 0, true],
  ["iPhone", false, true, "", 0, true],
  ["iPad", false, true, "", 0, true],
  ["Macintosh", false, true, "MacIntel", 5, true],
  ["iPhone Safari", false, false, "", 0, false],
  ["iPhone CriOS", false, false, "", 0, false],
  ["Chrome Android", false, false, "", 0, false],
  ["Chrome Android", false, true, "", 0, false],
  ["Macintosh", false, true, "MacIntel", 0, false],
])("selects only installed iOS: %s %s %s", (agent, safari, display, platform, touches, welcome) => {
  environment(agent, safari, display, platform, touches);
  render(<MemoryRouter><PublicLandingPage /></MemoryRouter>);
  expect(Boolean(screen.queryByTestId("ios-pwa-welcome"))).toBe(welcome);
  expect(Boolean(screen.queryByTestId("landing-film"))).toBe(!welcome);
});

it("shows only the original Android image and two actions", () => {
  environment("iPhone", true);
  const { container } = render(<MemoryRouter><PublicLandingPage /></MemoryRouter>);
  expect(screen.getByTestId("public-entry-background")).toHaveAttribute("src", androidGymImage);
  expect(screen.getAllByRole("link")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "شروع کنیم" })).toHaveAttribute("href", "/get-started");
  expect(screen.getByRole("link", { name: "حساب داری؟ ورود" })).toHaveAttribute("href", "/login");
  expect(container.querySelector("video, header, nav, section, h1, h2")).toBeNull();
});

it.each([["شروع کنیم", "/get-started"], ["حساب داری؟ ورود", "/login"]])("navigates %s", async (label, path) => {
  environment("iPhone", true);
  render(<MemoryRouter><Routes><Route path="/" element={<PublicLandingPage />} /><Route path={path} element={<p>destination</p>} /></Routes></MemoryRouter>);
  await userEvent.click(screen.getByRole("link", { name: label }));
  expect(screen.getByText("destination")).toBeInTheDocument();
});

it("keeps SSR browser markup stable even in an iOS test environment", () => {
  environment("iPhone", true);
  const markup = renderToString(<MemoryRouter><PublicLandingPage /></MemoryRouter>);
  expect(markup).toContain('data-testid="landing-film"');
  expect(markup).not.toContain('data-testid="ios-pwa-welcome"');
});

it("supports navigator.standalone without matchMedia", () => {
  environment("iPhone", true);
  vi.stubGlobal("matchMedia", undefined);
  Function(bootstrap)();
  render(<MemoryRouter><PublicLandingPage /></MemoryRouter>);
  expect(screen.getByTestId("ios-pwa-welcome")).toBeInTheDocument();
});
