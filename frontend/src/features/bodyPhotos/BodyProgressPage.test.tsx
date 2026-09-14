import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { ApiError } from "../../shared/apiClient";

const api = vi.hoisted(() => ({
  deleteBodyPhotoSession: vi.fn(),
  getBodyProgressTimeline: vi.fn(),
}));
const entitlementAccess = vi.hoisted(() => ({ allowed: true, remaining: 1, snapshot: null as unknown }));
vi.mock("./api", () => api);
vi.mock("../entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    snapshot: entitlementAccess.snapshot,
    loading: false,
    error: null,
    retry: vi.fn(),
    hasEntitlement: () => entitlementAccess.allowed,
    quotaFor: () => entitlementAccess.allowed ? { entitlement: "body_analysis.run", limit: 1, used: 1 - entitlementAccess.remaining, remaining: entitlementAccess.remaining, window_days: 7, reset_at: "2026-08-11T12:00:00Z" } : null,
  }),
}));

import { BodyProgressPage } from "./BodyProgressPage";

function timelineResponse(sessions: Array<Record<string, unknown>>) {
  return {
    schema_version: "1.0",
    items: sessions.map((session) => ({
      session,
      photos: session.photos,
      analysis: null,
      snapshot: null,
      comparison: null,
      review_state: {
        coach: { role: "coach", decision: null, reviewed_at: null, reviewed_result_version: null },
        doctor: { role: "doctor", decision: null, reviewed_at: null, reviewed_result_version: null },
        fully_reviewed: false,
      },
    })),
  };
}

beforeEach(async () => {
  vi.clearAllMocks();
  entitlementAccess.allowed = true;
  entitlementAccess.remaining = 1;
  entitlementAccess.snapshot = null;
  await i18n.changeLanguage("en");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("links each photo session to its result and keeps the workflow optional", async () => {
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([{
      id: "session-1",
      purpose: "initial_plan",
      state: "review_pending",
      photos: [{
        id: "photo-1",
        view: "front",
        content_url: "/api/v1/body-photos/photos/photo-1/content",
        created_at: "2026-08-03T10:00:00Z",
      }],
      operational_processing_consent: null,
      model_training_consent: null,
      submitted_at: "2026-08-03T10:00:00Z",
      created_at: "2026-08-03T10:00:00Z",
      updated_at: "2026-08-03T10:00:00Z",
    }]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("link", { name: /view analysis/i })).toHaveAttribute(
    "href",
    "/body-progress/session-1",
  );
  expect(screen.getByRole("heading", { name: "Body Analysis" })).toBeInTheDocument();
  expect(screen.getByRole("list", { name: "My body over time" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Latest progress photo" })).toHaveAttribute("src", "/api/v1/body-photos/photos/photo-1/content");
  expect(screen.getByText(/Optional — add standardized/i)).toBeInTheDocument();
});

it("shows an actionable empty state without the deprecated scanner visual", async () => {
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "No photo registered" })).toBeInTheDocument();
  expect(screen.queryByRole("img", { name: "Body analysis scanner preview" })).not.toBeInTheDocument();
  expect(screen.queryByText("Body scan and tracking")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Register new photos" })).toHaveAttribute(
    "href",
    "/body-progress/new",
  );
  expect(screen.queryByText("پیشرفت بدنی")).not.toBeInTheDocument();
});

it("shows a locked body-analysis start state for free members", async () => {
  entitlementAccess.allowed = false;
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "No photo registered" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Register new photos" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Register new photos" })).toBeDisabled();
  expect(screen.getByText("This action is not included in your current access.")).toBeInTheDocument();
});

it("shows the rolling quota reset before a new body-analysis session", async () => {
  entitlementAccess.remaining = 0;
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("button", { name: "Register new photos" })).toBeDisabled();
  expect(screen.getByText(/Available again/)).toBeInTheDocument();
});

it("separates incomplete uploads from submitted analyses and marks the latest analysis", async () => {
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([
      {
        id: "incomplete-1",
        purpose: "progress_check",
        state: "uploading",
        photos: [{ id: "front", view: "front", content_url: "/front" }],
        submitted_at: null,
        created_at: "2026-08-04T10:00:00Z",
        updated_at: "2026-08-04T10:00:00Z",
      },
      {
        id: "analysis-1",
        purpose: "initial_plan",
        state: "completed",
        photos: [{ id: "analysis-front", view: "front", content_url: "/analysis-front" }],
        submitted_at: "2026-08-03T10:00:00Z",
        created_at: "2026-08-03T10:00:00Z",
        updated_at: "2026-08-03T10:00:00Z",
      },
    ]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "Incomplete uploads" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "My body over time" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Continue upload" })).toHaveAttribute(
    "href",
    "/body-progress/new?sessionId=incomplete-1",
  );
  expect(screen.getByRole("link", { name: "View analysis" })).toHaveAttribute(
    "href",
    "/body-progress/analysis-1",
  );
  expect(screen.getByText("Latest scan")).toBeVisible();
  expect(screen.getAllByText(/1 \/ 3/)).toHaveLength(2);
});

it("deletes an incomplete session after confirmation", async () => {
  const user = userEvent.setup();
  api.deleteBodyPhotoSession.mockResolvedValue(undefined);
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([{
      id: "incomplete-1",
      purpose: "progress_check",
      state: "uploading",
      photos: [{ id: "front", view: "front", content_url: "/front" }],
      submitted_at: null,
      created_at: "2026-08-04T10:00:00Z",
      updated_at: "2026-08-04T10:00:00Z",
    }]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  expect(await screen.findByRole("link", { name: "Start photo session" })).toHaveAttribute(
    "href",
    "/body-progress/new",
  );
  await user.click(await screen.findByRole("button", { name: "Delete upload" }));
  expect(screen.getByRole("dialog", { name: "Delete incomplete upload?" })).toBeVisible();
  expect(api.deleteBodyPhotoSession).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Delete permanently" }));

  await waitFor(() => expect(api.deleteBodyPhotoSession).toHaveBeenCalledWith("incomplete-1"));
  expect(screen.queryByRole("link", { name: "Continue upload" })).not.toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("offers deletion for a saved analysis and restores focus after cancel", async () => {
  const user = userEvent.setup();
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([{
      id: "analysis-1",
      purpose: "initial_plan",
      state: "completed",
      photos: [{ id: "front", view: "front", content_url: "/front" }],
      submitted_at: "2026-08-03T10:00:00Z",
      created_at: "2026-08-03T10:00:00Z",
      updated_at: "2026-08-03T10:00:00Z",
    }]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  const deleteButton = await screen.findByRole("button", { name: "Delete analysis" });
  await user.click(deleteButton);

  expect(screen.getByRole("dialog", { name: "Delete saved analysis?" })).toHaveTextContent(
    /stored photos and this analysis session will be removed/i,
  );
  await user.click(screen.getByRole("button", { name: "Keep session" }));

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(deleteButton).toHaveFocus();
  expect(api.deleteBodyPhotoSession).not.toHaveBeenCalled();
});

it("closes the delete dialog with Escape", async () => {
  const user = userEvent.setup();
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([{
      id: "incomplete-1",
      purpose: "progress_check",
      state: "uploading",
      photos: [],
      submitted_at: null,
      created_at: "2026-08-04T10:00:00Z",
      updated_at: "2026-08-04T10:00:00Z",
    }]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "Delete upload" }));
  expect(screen.getByRole("dialog")).toBeVisible();
  await user.keyboard("{Escape}");

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("keeps the dialog open after a deletion failure and allows retry", async () => {
  const user = userEvent.setup();
  api.deleteBodyPhotoSession
    .mockRejectedValueOnce(new ApiError(
      503,
      "storage unavailable",
      null,
      "SERVICE_UNAVAILABLE",
    ))
    .mockResolvedValueOnce(undefined);
  api.getBodyProgressTimeline.mockResolvedValue(timelineResponse([{
      id: "incomplete-1",
      purpose: "progress_check",
      state: "uploading",
      photos: [],
      submitted_at: null,
      created_at: "2026-08-04T10:00:00Z",
      updated_at: "2026-08-04T10:00:00Z",
    }]));
  render(<MemoryRouter><BodyProgressPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "Delete upload" }));
  await user.click(screen.getByRole("button", { name: "Delete permanently" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The service is temporarily unavailable. Try again later.",
  );
  expect(screen.getByRole("dialog")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Delete permanently" }));

  await waitFor(() => expect(api.deleteBodyPhotoSession).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
