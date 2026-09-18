import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { NutritionExerciseQuestions } from "./NutritionExerciseQuestions";

it("collects only minimum structured exercise details for nutrition-only members with auto-advancing", async () => {
  await i18n.changeLanguage("en");
  const user = userEvent.setup();
  const onComplete = vi.fn();
  render(<NutritionExerciseQuestions onBack={vi.fn()} onComplete={onComplete} />);

  expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "I train regularly" }));

  await user.click(await screen.findByRole("button", { name: "Mixed training" }));
  await user.click(await screen.findByRole("button", { name: "4 days per week" }));
  await screen.findByRole("button", { name: "30 minutes" });
  for (const label of ["30 minutes", "45 minutes", "60 minutes", "75 minutes", "90 minutes", "More than 90 minutes"]) {
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
  }
  await user.click(await screen.findByRole("button", { name: "45 minutes" }));
  await user.click(await screen.findByRole("button", { name: "Moderate" }));

  await vi.waitFor(() => {
    expect(onComplete).toHaveBeenCalledWith({
      trains: true,
      exercise_type: "mixed",
      days_per_week: 4,
      minutes_per_session: 45,
      intensity: "moderate",
    });
  });
  expect(screen.queryByText("Where will you train?")).not.toBeInTheDocument();
});

it("maps more than 90 minutes to 120 minutes per session", async () => {
  await i18n.changeLanguage("en");
  const user = userEvent.setup();
  const onComplete = vi.fn();
  render(<NutritionExerciseQuestions onBack={vi.fn()} onComplete={onComplete} />);

  await user.click(screen.getByRole("button", { name: "I train regularly" }));
  await user.click(await screen.findByRole("button", { name: "Mixed training" }));
  await user.click(await screen.findByRole("button", { name: "3 days per week" }));
  await user.click(await screen.findByRole("button", { name: "More than 90 minutes" }));
  await user.click(await screen.findByRole("button", { name: "Moderate" }));

  await vi.waitFor(() => {
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ minutes_per_session: 120 }));
  });
});

it("skips every exercise detail when a nutrition-only member does not train", async () => {
  await i18n.changeLanguage("fa");
  const user = userEvent.setup();
  const onComplete = vi.fn();
  render(<NutritionExerciseQuestions onBack={vi.fn()} onComplete={onComplete} />);

  expect(screen.queryByRole("button", { name: "ادامه" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "تمرین نمی‌کنم" }));

  await vi.waitFor(() => {
    expect(onComplete).toHaveBeenCalledWith({ trains: false });
  });
  expect(screen.queryByText("نوع اصلی تمرینت چیست؟")).not.toBeInTheDocument();
});

it("requires goal reselection when a non-training member selected muscle gain", async () => {
  await i18n.changeLanguage("fa");
  const user = userEvent.setup();
  const onComplete = vi.fn();
  render(<NutritionExerciseQuestions fitnessGoal="build_muscle" onBack={vi.fn()} onComplete={onComplete} />);

  await user.click(screen.getByRole("button", { name: "تمرین نمی‌کنم" }));

  expect(screen.getByRole("alert")).toHaveTextContent("هدفت را تغییر بده");
  expect(screen.queryByRole("button", { name: "ادامه" })).not.toBeInTheDocument();
  expect(onComplete).not.toHaveBeenCalled();
});
