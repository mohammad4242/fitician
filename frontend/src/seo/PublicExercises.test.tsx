import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, expect, it, vi } from "vitest";
import { PublicExercisePage as PublicPage } from "./PublicExercises";
import { publicPayload } from "./registry";

beforeEach(() => {
  window.history.replaceState(null, "", "/exercise-library");
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status: 503 }))));
});
it("browses anonymously with member selectors and preserves filter state in public links", async () => {
  render(<PublicPage payload={publicPayload("/exercise-library")} />);
  fireEvent.click(screen.getByRole("button", { name: /بالاتنه.*Upper Body/ }));
  fireEvent.click(screen.getByRole("button", { name: /سینه.*Chest/ }));
  await waitFor(() => expect(document.querySelector('a[href^="/exercise-library/dumbbell-bench-press?"]')).toBeInTheDocument());
  const card = screen.getByRole("article", { name: "پرس سینه دمبل" });
  expect(within(card).getByRole("link", { name: "مشاهده حرکت" })).toHaveAttribute("href", expect.stringContaining("/exercise-library/dumbbell-bench-press?body_region=upper_body&primary_muscle=chest"));
  expect(screen.getByRole("searchbox")).toBeInTheDocument();
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-match" } });
  await waitFor(() => expect(screen.queryByRole("article", { name: "پرس سینه دمبل" })).not.toBeInTheDocument());
  expect(document.querySelector('[href^="/admin"]')).toBeNull();
  expect(vi.mocked(fetch).mock.calls.every(([url]) => String(url).includes("/api/v1/public/"))).toBe(true);
});
it("prerenders the real media/detail presentation and educational text", () => {
  const payload = publicPayload("/exercise-library/dumbbell-bench-press");
  const html = renderToStaticMarkup(<PublicPage payload={payload} />);
  expect(html).toContain('class="exercise-detail-sheet"');
  expect(html.match(/<main[ >]/g)).toHaveLength(1);
  expect(html).toContain('data-testid="exercise-media-carousel"');
  expect(html).toContain(payload.exercise!.instructions_fa[0]);
  expect(html).toContain(payload.exercise!.safety_notes_fa[0]);
  expect(html).toContain("Dumbbell Bench Press");
  expect(html).not.toContain("/admin/");
});

it("supports focus, equipment, difficulty, pagination and browser back", async () => {
  render(<PublicPage payload={publicPayload("/exercise-library")} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "صفحه بعد" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "صفحه بعد" }));
  await waitFor(() => expect(window.location.search).toContain("page=2"));
  fireEvent.click(screen.getByRole("button", { name: /بالاتنه.*Upper Body/ }));
  fireEvent.click(screen.getByRole("button", { name: /سینه.*Chest/ }));
  fireEvent.click(screen.getByRole("button", { name: /میان‌سینه.*Mid Chest/ }));
  fireEvent.change(screen.getByLabelText("تجهیزات"), { target: { value: "dumbbell" } });
  fireEvent.change(screen.getByLabelText("سطح سختی"), { target: { value: "intermediate" } });
  await waitFor(() => expect(document.querySelector('a[href^="/exercise-library/dumbbell-bench-press?"]')).toBeInTheDocument());
  expect(window.location.search).toContain("muscle_focus=mid_chest");
  expect(window.location.search).toContain("equipment=dumbbell");
  window.history.replaceState(null, "", "/exercise-library?body_region=lower_body");
  window.dispatchEvent(new PopStateEvent("popstate"));
  await waitFor(() => expect(screen.getByRole("button", { name: /جلو پا.*Quadriceps/ })).toBeInTheDocument());
});

it("keeps shared Persian exercise copy synchronized without shipping member translations", async () => {
  const { default: fa } = await import("@fitician/core/i18n/fa");
  const { default: language } = await import("./exercise-language.json");
  expect(language.catalog).toEqual(fa.translation.catalog);
  expect(language.exerciseDetail).toEqual(fa.translation.exerciseDetail);
});

it("retains catalogue filters when navigating through related exercises", async () => {
  window.history.replaceState(null, "", "/exercise-library/dumbbell-bench-press?body_region=upper_body&primary_muscle=chest");
  render(<PublicPage payload={publicPayload("/exercise-library/dumbbell-bench-press")} />);
  await waitFor(() => expect(document.querySelector(".exercise-detail-back")).toHaveAttribute("href", "/exercise-library?body_region=upper_body&primary_muscle=chest"));
  for (const link of document.querySelectorAll(".public-related-exercises .exercise-card__link")) {
    expect(link).toHaveAttribute("href", expect.stringContaining("?body_region=upper_body&primary_muscle=chest"));
  }
});

it("finds imported chest exercises without login and opens their prerendered detail", async () => {
  render(<PublicPage payload={publicPayload("/exercise-library")} />);
  fireEvent.click(screen.getByRole("button", { name: /بالاتنه.*Upper Body/ }));
  fireEvent.click(screen.getByRole("button", { name: /سینه.*Chest/ }));
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Barbell Decline Bench Press" } });
  await waitFor(() => expect(screen.getByRole("link", { name: "مشاهده حرکت" })).toHaveAttribute("href", expect.stringContaining("/exercise-library/fedb-0033-barbell-decline-bench-press")));
  const payload = publicPayload("/exercise-library/fedb-0033-barbell-decline-bench-press");
  const html = renderToStaticMarkup(<PublicPage payload={payload} />);
  expect(html).toContain("Barbell Decline Bench Press");
  expect(html).toContain(payload.exercise!.instructions_fa[0]);
  expect(html).toContain(payload.exercise!.safety_notes_fa[0]);
});

it("ships only card data to catalogue browsing instead of every exercise detail", () => {
  const payload = publicPayload("/exercise-library");
  expect(payload.exercises.length).toBeGreaterThan(0);
  for (const record of payload.exercises) {
    expect(record).not.toHaveProperty("instructions_fa");
    expect(record).not.toHaveProperty("safety_notes_fa");
    expect(record).not.toHaveProperty("media_assets");
  }
});

it("keeps approved public videos and alternate media controls in the shared detail", async () => {
  const payload = publicPayload("/exercise-library/fedb-drv-close-feet-leg-press-close-feet-leg-press");
  render(<PublicPage payload={payload} />);
  const video = document.querySelector(".exercise-media-carousel video");
  expect(video).toHaveAttribute("controls");
  expect(video).toHaveAttribute("playsinline");
  const assets = payload.exercise!.media_assets!;
  expect(assets.length).toBe(2);
  const selector = screen.getByRole("combobox", { name: "رسانهٔ نمایش" });
  const second = within(selector).getAllByRole("option")[1] as HTMLOptionElement;
  fireEvent.change(selector, { target: { value: second.value } });
  expect(document.querySelector(".exercise-media-carousel video")).toHaveAttribute("src", expect.stringContaining(assets[1].media_path));
  expect(document.querySelector('[href^="/admin"]')).toBeNull();
});
