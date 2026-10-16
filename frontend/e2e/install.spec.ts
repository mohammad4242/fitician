import { devices, expect, test } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173";
const iphoneOptions = { ...devices["iPhone 13"], baseURL };

test("serves the public install page directly without authentication", async ({ page, request }) => {
  const pageErrors: string[] = [];
  const requestedUrls: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (browserRequest) => requestedUrls.push(browserRequest.url()));

  const response = await request.get("/install");
  expect(response.status()).toBe(200);
  expect(await response.text()).toContain("Fitician");

  await page.goto("/install", { waitUntil: "networkidle" });

  await expect(page).toHaveURL(`${baseURL}/install`);
  await expect(page.getByRole("heading", { name: "فیتیشن رو نصب کن" }))
    .toBeVisible();
  await expect(page.locator('[data-testid="public-install-brand-logo"]')).toBeVisible();

  await expect(page.getByRole("tab", { name: "اندروید" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "آیفون" })).toBeVisible();

  await page.reload({ waitUntil: "networkidle" });
  await expect(page).toHaveURL(`${baseURL}/install`);
  await expect(page.locator('[data-testid="public-install-brand-logo"]')).toBeVisible();
  expect(pageErrors).toEqual([]);
  expect(requestedUrls.some((url) => /image&videos|mediapipe|landing\.mp4|\/media\//i.test(url))).toBe(false);
});

test("shows the installed state without repeating installation steps", async ({ browser }) => {
  const context = await browser.newContext(iphoneOptions);
  try {
    await context.addInitScript(() => {
      Object.defineProperty(navigator, "standalone", { configurable: true, value: true });
    });
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: /فیتیشن روی دستگاهت نصب شده/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "ورود به فیتیشن" })).toHaveAttribute("href", "/");
    await expect(page.getByRole("heading", { name: "نصب فیتیشن روی صفحهٔ اصلی" })).toHaveCount(0);
  } finally {
    await context.close();
  }
});

test("shows Home Screen installation steps on iPhone", async ({ browser }) => {
  const context = await browser.newContext(iphoneOptions);
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });

    await expect(page).toHaveURL(`${baseURL}/install`);
    await expect(page.getByRole("heading", { name: "نصب فیتیشن روی صفحهٔ اصلی" })).toBeVisible();
    await expect(page.getByText("Share", { exact: true })).toBeVisible();
    await expect(page.getByText("Add to Home Screen", { exact: true })).toBeVisible();
    await expect(page.getByText("Open as Web App", { exact: true })).toBeVisible();
    await expect(page.getByText("Add", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "نصب فیتیشن" })).toHaveCount(0);
  } finally {
    await context.close();
  }
});

test("supports English LTR switching and a narrow 320px iPhone screen", async ({ browser }) => {
  const context = await browser.newContext({
    ...iphoneOptions,
    viewport: { width: 320, height: 700 },
  });
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });
    await expect(page.locator(".public-install")).toHaveAttribute("dir", "rtl");
    await page.locator(".public-install__header .language-switcher").click();

    await expect(page.locator(".public-install")).toHaveAttribute("dir", "ltr");
    await expect(page.getByRole("heading", { name: "Install Fitician", exact: true }))
      .toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally {
    await context.close();
  }
});

test("guides Instagram iPhone visitors to open the page in Safari", async ({ browser }) => {
  const context = await browser.newContext({
    ...iphoneOptions,
    userAgent: `${iphoneOptions.userAgent} Instagram 372.0`,
  });
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "یک قدم تا نصب فیتیشن" })).toBeVisible();
    await expect(page.getByText(/این صفحه داخل مرورگر اینستاگرام باز شده/)).toBeVisible();
    await expect(page.getByText("Open in Safari", { exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: "کپی لینک" })).toBeVisible();
    await expect(page.getByRole("button", { name: "نصب فیتیشن" })).toHaveCount(0);
  } finally {
    await context.close();
  }
});

test("copies the current install URL and announces success for Instagram visitors", async ({ browser }) => {
  const context = await browser.newContext({
    ...iphoneOptions,
    userAgent: `${iphoneOptions.userAgent} Instagram 372.0`,
  });
  try {
    await context.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: {
          writeText: (value: string) => Promise.resolve(localStorage.setItem("copiedInstallUrl", value)),
        },
      });
    });
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "کپی لینک" }).click();

    await expect(page.getByRole("status")).toHaveText("لینک کپی شد ✓");
    await expect.poll(() => page.evaluate(() => localStorage.getItem("copiedInstallUrl")))
      .toBe(`${baseURL}/install`);
  } finally {
    await context.close();
  }
});

test("handles clipboard denial without an unhandled page error", async ({ browser }) => {
  const context = await browser.newContext({
    ...iphoneOptions,
    userAgent: `${iphoneOptions.userAgent} Instagram 372.0`,
  });
  try {
    await context.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: () => Promise.reject(new Error("Clipboard permission denied")) },
      });
    });
    const page = await context.newPage();
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.goto("/install", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "کپی لینک" }).click();

    await expect(page.getByRole("status"))
      .toHaveText("کپی خودکار در دسترس نیست؛ لینک صفحه را از نوار آدرس کپی کن.");
    expect(pageErrors).toEqual([]);
  } finally {
    await context.close();
  }
});

test("uses the existing Chromium install prompt when the browser provides it", async ({ browser }) => {
  const context = await browser.newContext({
    ...iphoneOptions,
    userAgent: "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
  });
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });
    await expect(page.getByRole("button", { name: "نصب فیتیشن" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "دانلود مستقیم APK" })).toBeVisible();
    await expect(page.getByRole("link", { name: "ورود به فیتیشن" })).toHaveAttribute("href", "/");

    await page.evaluate(() => {
      const event = new Event("beforeinstallprompt", { cancelable: true }) as Event & {
        prompt: () => Promise<void>;
        userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
      };
      event.prompt = async () => { localStorage.setItem("installPromptCalled", "true"); };
      event.userChoice = Promise.resolve({ outcome: "accepted" });
      window.dispatchEvent(event);
    });

    await page.getByRole("tab", { name: "آیفون" }).click();
    await expect(page.getByRole("button", { name: "نصب فیتیشن", exact: true })).toHaveCount(0);
    await page.getByRole("tab", { name: "اندروید" }).click();

    const installButton = page.getByRole("button", { name: "نصب فیتیشن" });
    await expect(installButton).toBeVisible();
    await installButton.click();

    await expect(page.getByRole("heading", { name: /فیتیشن روی دستگاهت نصب شده/ })).toBeVisible();
    await expect.poll(() => page.evaluate(() => localStorage.getItem("installPromptCalled")))
      .toBe("true");
  } finally {
    await context.close();
  }
});

test("offers a web app link on desktop browsers", async ({ browser }) => {
  const context = await browser.newContext({
    baseURL,
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
  });
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });

    await expect(page.getByRole("tab", { name: "اندروید" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("link", { name: "ورود به فیتیشن" })).toHaveAttribute("href", "/");
  } finally {
    await context.close();
  }
});

for (const instagram of [false, true]) {
  test(`Android ${instagram ? "Instagram" : "Chrome"} defaults to APK with both platform tabs visible`, async ({ browser }) => {
    const context = await browser.newContext({
      ...devices["Pixel 7"], baseURL,
      userAgent: `${devices["Pixel 7"].userAgent}${instagram ? " Instagram 372.0" : ""}`,
    });
    try {
      const page = await context.newPage();
      await page.goto("/install", { waitUntil: "networkidle" });
      const android = page.getByRole("tab", { name: "اندروید" });
      const iphone = page.getByRole("tab", { name: "آیفون" });
      await expect(android).toHaveAttribute("aria-selected", "true");
      await expect(iphone).toBeVisible();
      await expect(page.getByRole("link", { name: "دانلود مستقیم APK" })).toHaveAttribute("href", "/download/android");
      await expect(page.getByRole("button", { name: /دریافت از کافه بازار.*به‌زودی/ })).toBeDisabled();
      await expect(page.getByRole("button", { name: /دریافت از مایکت.*به‌زودی/ })).toBeDisabled();
      await expect(page.locator(".public-install__downloads a")).toHaveCount(1);
      await iphone.click();
      await expect(iphone).toHaveAttribute("aria-selected", "true");
      await expect(android).toBeVisible();
      await expect(page.getByRole("button", { name: "نصب وب‌اپلیکیشن فیتیشن" })).toBeVisible();
      await expect(page.getByText("Add to Home Screen", { exact: true })).toBeVisible();
      await iphone.press("Home");
      await expect(android).toBeFocused();
      await expect(android).toHaveAttribute("aria-selected", "true");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    } finally { await context.close(); }
  });
}

test("iPhone defaults to Safari instructions and can switch to Android", async ({ browser }) => {
  const context = await browser.newContext(iphoneOptions);
  try {
    const page = await context.newPage();
    await page.goto("/install", { waitUntil: "networkidle" });
    await expect(page.getByRole("tab", { name: "آیفون" })).toHaveAttribute("aria-selected", "true");
    await page.getByRole("button", { name: "نصب وب‌اپلیکیشن فیتیشن" }).click();
    await expect(page.getByText("Share", { exact: true })).toBeVisible();
    await page.getByRole("tab", { name: "اندروید" }).click();
    await expect(page.getByRole("link", { name: "دانلود مستقیم APK" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "آیفون" })).toBeVisible();
  } finally { await context.close(); }
});

test("keeps the public install page dark when the saved app theme is light", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fitician.theme", "light"));
  await page.goto("/install", { waitUntil: "networkidle" });
  await expect(page.locator(".public-install__title")).toHaveCSS("color", "rgb(232, 244, 241)");
  await expect(page.locator(".public-install")).toHaveCSS("color-scheme", "dark");
});
