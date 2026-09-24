import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExerciseMedia } from "./ExerciseMedia";

const placeholderPath = "/exercises/exercise-placeholder.svg";

describe("ExerciseMedia", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders the shared placeholder with a meaningful name", () => {
    render(
      <ExerciseMedia path="" name="پلانک" mediaType="placeholder" />,
    );

    const image = screen.getByRole("img", { name: "نمایش حرکت پلانک" });
    expect(image).toHaveAttribute("src", placeholderPath);
  });

  it("renders approved image media with localized alternative text", () => {
    render(
      <ExerciseMedia
        path="/exercises/upper-body/chest/dumbbell-bench-press.gif"
        name="پرس سینه دمبل"
        mediaType="gif"
      />,
    );

    expect(
      screen.getByRole("img", { name: "نمایش حرکت پرس سینه دمبل" }),
    ).toHaveAttribute(
      "src",
      "/media/exercises/upper-body/chest/dumbbell-bench-press.gif",
    );
  });

  it("falls back to the shared placeholder when an image fails", () => {
    render(
      <ExerciseMedia
        path="/exercises/missing.gif"
        name="Goblet Squat"
        mediaType="gif"
      />,
    );

    fireEvent.error(screen.getByRole("img", { name: "Goblet Squat demonstration" }));

    expect(
      screen.getByRole("img", { name: "Goblet Squat demonstration" }),
    ).toHaveAttribute("src", placeholderPath);
  });

  it("renders video controls without autoplay and falls back after an error", () => {
    render(
      <ExerciseMedia
        path="/exercises/demo.mp4"
        name="Romanian Deadlift"
        mediaType="video"
      />,
    );

    const video = screen.getByLabelText("Romanian Deadlift demonstration");
    expect(video).toHaveAttribute("controls");
    expect(video).toHaveAttribute("playsinline");
    expect(video).not.toHaveAttribute("autoplay");
    expect(video).toHaveAttribute("poster", "/media/exercises/demo.poster.webp");

    fireEvent.error(video);

    expect(
      screen.getByRole("img", { name: "Romanian Deadlift demonstration" }),
    ).toHaveAttribute("src", placeholderPath);
  });

  it("uses the shared public base for a managed exercise video and its poster", () => {
    vi.stubEnv("VITE_MEDIA_PUBLIC_BASE_URL", "https://media.example.test/");

    render(
      <ExerciseMedia
        path="/media/exercises/x/media-a.mp4"
        name="Bench Press"
        mediaType="video"
      />,
    );

    const video = screen.getByLabelText("Bench Press demonstration");
    expect(video).toHaveAttribute(
      "src",
      "https://media.example.test/public/exercises/x/media-a.mp4",
    );
    expect(video).toHaveAttribute(
      "poster",
      "https://media.example.test/public/exercises/x/media-a.poster.webp",
    );
    expect(screen.queryByRole("img", { name: "Bench Press demonstration" })).toBeNull();
  });

  it("supports a silent looping preview without controls in summary cards", () => {
    render(<ExerciseMedia ambient path="/exercises/demo.mp4" name="Squat" mediaType="video" />);

    const video = screen.getByLabelText("Squat demonstration");
    expect(video).toHaveAttribute("autoplay");
    expect(video).toHaveAttribute("loop");
    expect(video).not.toHaveAttribute("controls");
  });
});
