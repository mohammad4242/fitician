import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, TransportError } from "@fitician/core";

import i18n from "../../i18n";
import type { ExerciseDetail } from "./types";

const api = vi.hoisted(() => ({ getExercise: vi.fn() }));

vi.mock("./api", () => api);
vi.mock("../../shared/AuthenticatedHeader", () => ({
  AuthenticatedHeader: () => null,
}));

import { ExerciseDetailPage } from "./ExerciseDetailPage";

const detail: ExerciseDetail = {
  id: "018f0000-0000-7000-8000-000000000001",
  slug: "dumbbell-bench-press",
  name_en: "Dumbbell Bench Press",
  name_fa: "پرس سینه دمبل",
  content_type: "exercise",
  body_region: "upper_body",
  primary_muscle: "chest",
  muscle_focus: "mid_chest",
  labels: [],
  secondary_muscles: ["triceps", "shoulders"],
  equipment: ["dumbbell", "bench"],
  difficulty: "intermediate",
  instructions_en: [
    "Lie on a flat bench with both feet planted.",
    "Lower the dumbbells with control beside the chest.",
    "Press upward without locking the elbows hard.",
  ],
  instructions_fa: [
    "روی نیمکت صاف دراز بکش و هر دو پا را روی زمین نگه دار.",
    "دمبل‌ها را با کنترل کنار سینه پایین بیاور.",
    "دمبل‌ها را بالا ببر، بدون اینکه آرنج‌ها را با فشار قفل کنی.",
  ],
  safety_notes_en: [
    "Keep your shoulder blades back and down; do not let the shoulders roll forward and take tension away from the chest.",
    "Lower the dumbbells far enough to get a good chest stretch without forcing the front of the shoulder into an uncomfortable position.",
    "Keep the wrists roughly stacked over the elbows instead of letting the dumbbells drift too far in or out.",
    "As you press, think about bringing the upper arms toward each other rather than only pushing the dumbbells upward.",
    "Control the return so the chest stays loaded instead of dropping the dumbbells.",
  ],
  safety_notes_fa: [
    "کتف‌هاتو عقب و پایین نگه دار؛ نذار موقع پرس شونه‌ها بیان جلو و فشار سینه رو بدزدن.",
    "دمبل‌ها رو تا جایی پایین بیار که سینه خوب کش بیاد، ولی جلوی شونه تحت فشار بد قرار نگیره.",
    "مچ رو تقریباً روی آرنج نگه دار؛ نذار دمبل‌ها بیش‌ازحد داخل یا بیرون فرار کنن.",
    "بالا که میای فقط دمبل رو هل نده؛ فکر کن دو بازوت رو داری به سمت هم جمع می‌کنی.",
    "برگشت رو کنترل کن تا فشار روی سینه بمونه؛ دمبل‌ها رو رها نکن.",
  ],
  media_path: "/exercises/upper-body/chest/dumbbell-bench-press.gif",
  media_type: "gif",
  media_source_url: null,
  media_license: "Project owner supplied and authorized",
  media_attribution: "Provided by Fitsho project owner",
};

beforeEach(async () => {
  api.getExercise.mockReset();
  api.getExercise.mockResolvedValue(detail);
  await i18n.changeLanguage("fa");
});

afterEach(() => vi.clearAllMocks());

describe("exercise detail states", () => {
  it("uses the supplied strength still above the exercise detail", async () => {
    renderDetail();

    const background = await screen.findByTestId("member-header-image");
    expect(background).toHaveAttribute(
      "src",
      expect.stringContaining("hero-strength-fallback"),
    );
    expect(background.parentElement).toHaveClass("member-page-background");
  });

  it("shows a loading state while the exercise is requested", async () => {
    const user = userEvent.setup();
    const pending = deferred<ExerciseDetail | null>();
    api.getExercise.mockReturnValue(pending.promise);
    renderDetail();

    const message = await screen.findByText("در حال دریافت جزئیات حرکت…");
    expect(message.closest('[role="status"]')).toBeInTheDocument();

    pending.resolve(detail);
    await user.click(await screen.findByText("راهنمای حرکت", { exact: true }));
    expect(await screen.findByRole("heading", { name: "پرس سینه دمبل" })).toBeVisible();
  });

  it("retries a failed request", async () => {
    const user = userEvent.setup();
    api.getExercise
      .mockRejectedValueOnce(new TransportError("offline"))
      .mockResolvedValueOnce(detail);
    renderDetail();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "اتصال اینترنت در دسترس نیست",
    );
    await user.click(screen.getByRole("button", { name: "دوباره تلاش کنید" }));

    await user.click(await screen.findByText("راهنمای حرکت", { exact: true }));
    expect(await screen.findByRole("heading", { name: "پرس سینه دمبل" })).toBeVisible();
  });

  it("uses a safe shared presentation for a backend failure", async () => {
    api.getExercise.mockRejectedValueOnce(
      new ApiError(503, "private provider detail", null, "SERVICE_UNAVAILABLE", {
        requestId: "detail-request-1",
      }),
    );
    renderDetail();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("سرویس موقتاً در دسترس نیست");
    expect(alert).not.toHaveTextContent("private provider detail");
    expect(alert).not.toHaveTextContent("detail-request-1");
  });

  it("shows an unknown exercise state with a catalog return link", async () => {
    api.getExercise.mockResolvedValue(null);
    renderDetail(
      "/exercises/unknown?body_region=upper_body&primary_muscle=chest",
    );

    expect(await screen.findByRole("heading", { name: "حرکت پیدا نشد" })).toBeVisible();
    expect(screen.getByRole("link", { name: "بازگشت به کتابخانه حرکات" })).toHaveAttribute(
      "href",
      "/exercises?body_region=upper_body&primary_muscle=chest",
    );
  });
});

describe("exercise detail content", () => {
  it("collapses the guide, execution, and safety sections until their titles are clicked", async () => {
    const user = userEvent.setup();
    renderDetail();

    for (const title of ["راهنمای حرکت", "روش اجرای صحیح", "نکات فرم و ایمنی"]) {
      const titleNode = await screen.findByText(title, { exact: true });
      const section = titleNode.closest("details");
      expect(section).not.toBeNull();
      expect(section).not.toHaveAttribute("open");

      await user.click(titleNode);

      expect(section).toHaveAttribute("open");
    }
  });

  it("renders bilingual names, media, metadata, steps, safety notes, and navigation", async () => {
    const user = userEvent.setup();
    renderDetail();

    await user.click(await screen.findByText("راهنمای حرکت", { exact: true }));
    await user.click(screen.getByText("روش اجرای صحیح", { exact: true }));
    await user.click(screen.getByText("نکات فرم و ایمنی", { exact: true }));

    const heading = await screen.findByRole("heading", { name: "پرس سینه دمبل" });
    expect(heading).toHaveAttribute("dir", "rtl");
    expect(screen.getByText("Dumbbell Bench Press")).toHaveAttribute("dir", "ltr");
    expect(screen.getByRole("img", { name: "نمایش حرکت پرس سینه دمبل" })).toHaveAttribute(
      "src",
      "/media/exercises/upper-body/chest/dumbbell-bench-press.gif",
    );
    const facts = screen.getByText("عضله اصلی").closest("dl");
    expect(facts).not.toBeNull();
    expect(within(facts!).getByText("سینه")).toBeVisible();
    expect(screen.getByText("پشت بازو، سرشانه")).toBeVisible();
    expect(screen.getByText("دمبل، نیمکت")).toBeVisible();
    expect(screen.getByText("متوسط")).toBeVisible();

    const instructions = screen.getByText("روش اجرای صحیح", { exact: true }).closest("details");
    expect(instructions).not.toBeNull();
    expect(within(instructions!).getAllByRole("listitem")).toHaveLength(3);
    expect(within(instructions!).getByText(detail.instructions_fa[0])).toBeVisible();

    const safety = screen.getByText("نکات فرم و ایمنی", { exact: true }).closest("details");
    expect(safety).not.toBeNull();
    expect(
      within(safety!).getAllByRole("listitem").map((item) => item.textContent),
    ).toEqual(detail.safety_notes_fa);

    const breadcrumb = screen.getByRole("navigation", { name: "مسیر جزئیات حرکت" });
    expect(within(breadcrumb).getByRole("link", { name: "کتابخانه حرکات" })).toHaveAttribute(
      "href",
      "/exercises?body_region=upper_body&primary_muscle=chest",
    );
    expect(screen.getByRole("link", { name: "بازگشت به کتابخانه حرکات" })).toHaveAttribute(
      "href",
      "/exercises?body_region=upper_body&primary_muscle=chest",
    );
  });

  it("uses English instructions and preserves Persian name direction in English", async () => {
    const user = userEvent.setup();
    await i18n.changeLanguage("en");
    renderDetail();

    await user.click(await screen.findByText("Movement guide", { exact: true }));
    await user.click(screen.getByText("Correct execution", { exact: true }));

    expect(
      await screen.findByRole("heading", { name: "Dumbbell Bench Press" }),
    ).toHaveAttribute("dir", "ltr");
    expect(screen.getByText("پرس سینه دمبل")).toHaveAttribute("dir", "rtl");
    expect(screen.getByText(detail.instructions_en[0])).toBeVisible();
    expect(screen.queryByText(detail.instructions_fa[0])).not.toBeInTheDocument();
    await user.click(screen.getByText("Form and safety notes", { exact: true }));
    const safety = screen
      .getByText("Form and safety notes", { exact: true })
      .closest("details");
    expect(safety).not.toBeNull();
    expect(
      within(safety!).getAllByRole("listitem").map((item) => item.textContent),
    ).toEqual(detail.safety_notes_en);
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
  });

  it("lets the member select among ordered assets for their gender", async () => {
    const user = userEvent.setup();
    api.getExercise.mockResolvedValue({
      ...detail,
      media_assets: [
        {
          presentation: "male",
          role: "video",
          sort_order: 0,
          media_path: "/media/male.mp4",
          media_type: "video",
          media_source_url: null,
          media_license: null,
          media_attribution: null,
        },
        mediaAsset("/media/male-second.mp4", "male", 1),
      ],
    });
    renderDetail();

    const selector = await screen.findByLabelText("رسانهٔ نمایش");
    await user.selectOptions(selector, "male-video-1");

    const video = screen.getByLabelText("نمایش حرکت پرس سینه دمبل");
    expect(video.tagName).toBe("VIDEO");
    expect(video).toHaveAttribute("src", "/media/male-second.mp4");
  });

  it("switches between male and female video sets below the carousel", async () => {
    const user = userEvent.setup();
    api.getExercise
      .mockResolvedValueOnce({
        ...detail,
        media_presentation: "male",
        media_assets: [mediaAsset("/media/male.mp4", "male", 0)],
      })
      .mockResolvedValueOnce({
        ...detail,
        media_presentation: "female",
        media_assets: [mediaAsset("/media/female.mp4", "female", 0)],
      });
    renderDetail();

    expect(await screen.findByRole("button", { name: "ویدئوی مرد" })).toHaveAttribute(
      "aria-pressed", "true",
    );
    await user.click(screen.getByRole("button", { name: "ویدئوی زن" }));

    expect(await screen.findByLabelText("نمایش حرکت پرس سینه دمبل")).toHaveAttribute(
      "src", "/media/female.mp4",
    );
    expect(api.getExercise).toHaveBeenNthCalledWith(2, "dumbbell-bench-press", "female");
  });

  it("uses legacy media when the profile gender has no asset", async () => {
    api.getExercise.mockResolvedValue({
      ...detail,
      media_assets: [],
    });
    renderDetail();

    expect(await screen.findByRole("img", { name: "نمایش حرکت پرس سینه دمبل" })).toHaveAttribute(
      "src", "/media/exercises/upper-body/chest/dumbbell-bench-press.gif",
    );
  });

  it("swipes left to next media and right to previous media", async () => {
    api.getExercise.mockResolvedValue({
      ...detail,
      media_assets: [
        mediaAsset("/media/male.mp4", "male", 0),
        mediaAsset("/media/male-second.mp4", "male", 1),
      ],
    });
    renderDetail();

    await screen.findByTestId("exercise-media-carousel");
    const carousel = screen.getByTestId("exercise-media-surface");
    expect(screen.getByText("۱ / ۲")).toBeVisible();

    fireEvent.pointerDown(carousel, { clientX: 240, clientY: 140 });
    fireEvent.pointerUp(carousel, { clientX: 160, clientY: 140 });
    expect(screen.getByLabelText("نمایش حرکت پرس سینه دمبل")).toHaveAttribute(
      "src", "/media/male-second.mp4",
    );
    expect(screen.getByText("۲ / ۲")).toBeVisible();

    fireEvent.pointerDown(carousel, { clientX: 160, clientY: 140 });
    fireEvent.pointerUp(carousel, { clientX: 240, clientY: 140 });
    expect(screen.getByLabelText("نمایش حرکت پرس سینه دمبل")).toHaveAttribute(
      "src", "/media/male.mp4",
    );
    expect(screen.getByText("۱ / ۲")).toBeVisible();
  });

  it("deduplicates matching assets without adding legacy media", async () => {
    api.getExercise.mockResolvedValue({
      ...detail,
      media_assets: [
        mediaAsset(detail.media_path, "male", 0),
        mediaAsset("/media/male-second.mp4", "male", 1),
      ],
    });
    renderDetail();

    await screen.findByTestId("exercise-media-carousel");
    const carousel = screen.getByTestId("exercise-media-surface");
    expect(screen.getByText("۱ / ۲")).toBeVisible();
    expect(screen.getByLabelText("نمایش حرکت پرس سینه دمبل")).toHaveAttribute(
      "src",
      "/media/exercises/upper-body/chest/dumbbell-bench-press.gif",
    );

    fireEvent.pointerDown(carousel, { clientX: 240, clientY: 140 });
    fireEvent.pointerUp(carousel, { clientX: 160, clientY: 140 });
    expect(screen.getByLabelText("نمایش حرکت پرس سینه دمبل")).toHaveAttribute(
      "src",
      "/media/male-second.mp4",
    );
  });

  it("does not show carousel navigation for a single deduplicated media item", async () => {
    api.getExercise.mockResolvedValue({
      ...detail,
      media_assets: [mediaAsset(detail.media_path, "male", 0)],
    });
    renderDetail();

    expect(await screen.findByTestId("exercise-media-carousel")).toBeVisible();
    expect(screen.queryByText(/۱ \/ \d/)).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "رسانهٔ نمایش" })).not.toBeInTheDocument();
  });
});

function mediaAsset(
  mediaPath: string,
  presentation: "male" | "female" | "unspecified",
  sortOrder: number,
) {
  return {
    presentation,
    role: "video" as const,
    sort_order: sortOrder,
    media_path: mediaPath,
    media_type: "video" as const,
    media_source_url: null,
    media_license: null,
    media_attribution: `${presentation} creator`,
  };
}

function renderDetail(
  path = "/exercises/dumbbell-bench-press?body_region=upper_body&primary_muscle=chest",
) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/exercises/:slug" element={<ExerciseDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}
