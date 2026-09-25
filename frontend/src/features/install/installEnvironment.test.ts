import { describe, expect, it } from "vitest";

import { detectInstallEnvironment } from "./installEnvironment";

const iphone = {
  userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1",
  canPrompt: false,
};

describe("detectInstallEnvironment", () => {
  it("shows iOS installation instructions in an iPhone browser", () => {
    expect(detectInstallEnvironment(iphone)).toBe("ios");
  });

  it("shows browser handoff guidance for Instagram on iPhone", () => {
    expect(detectInstallEnvironment({ ...iphone, userAgent: `${iphone.userAgent} Instagram 372.0` }))
      .toBe("ios-in-app-browser");
  });

  it("recognizes Facebook's iOS in-app browser markers", () => {
    expect(detectInstallEnvironment({ ...iphone, userAgent: `${iphone.userAgent} FBAN/FBIOS;FBAV/500.0` }))
      .toBe("ios-in-app-browser");
  });

  it("shows iOS installation instructions on iPad", () => {
    expect(detectInstallEnvironment({
      userAgent: "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1",
      canPrompt: false,
    })).toBe("ios");
  });

  it("recognizes iPadOS desktop mode through platform and touch points", () => {
    expect(detectInstallEnvironment({
      userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/17.5 Safari/605.1.15",
      platform: "MacIntel",
      maxTouchPoints: 5,
      canPrompt: false,
    })).toBe("ios");
  });

  it("treats navigator standalone as already installed", () => {
    expect(detectInstallEnvironment({ ...iphone, standalone: true })).toBe("installed");
  });

  it("treats display-mode standalone as already installed", () => {
    expect(detectInstallEnvironment({ ...iphone, displayModeStandalone: true })).toBe("installed");
  });

  it("treats the PWA install event as installed", () => {
    expect(detectInstallEnvironment({ ...iphone, pwaState: "installed" })).toBe("installed");
  });

  it("marks Chromium with a real prompt available", () => {
    expect(detectInstallEnvironment({
      userAgent: "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
      canPrompt: true,
    })).toBe("chromium-prompt");
  });

  it("marks Chromium without an install event", () => {
    expect(detectInstallEnvironment({
      userAgent: "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
      canPrompt: false,
    })).toBe("chromium-unavailable");
  });

  it("classifies unsupported desktop browsers as other", () => {
    expect(detectInstallEnvironment({
      userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
      canPrompt: false,
    })).toBe("other");
  });
});
