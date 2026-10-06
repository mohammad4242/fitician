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
  await waitFor(() => expect(screen.getByRole("article", { name: "پرس سینه دمبل" })).toBeInTheDocument());
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
  await waitFor(() => expect(screen.getByRole("article", { name: "پرس سینه دمبل" })).toBeInTheDocument());
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
