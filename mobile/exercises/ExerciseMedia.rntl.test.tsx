import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";

const mockUseIsFocused = jest.fn(() => true);

jest.mock("expo-router", () => ({
  useIsFocused: () => mockUseIsFocused(),
}));
jest.mock("expo-video", () => {
  const React = jest.requireActual("react") as typeof import("react");
  const { View } = jest.requireActual("react-native") as typeof import("react-native");
  return {
    useVideoPlayer: () => ({ addListener: jest.fn(), status: "idle" }),
    VideoView: (props: Record<string, unknown>) => React.createElement(View, { testID: "native-video", ...props }),
  };
});
jest.mock("@expo/vector-icons", () => ({ MaterialCommunityIcons: () => null }));
jest.mock("../config/nativeRuntimeConfig", () => ({
  getMobileRuntimeConfig: () => ({
    apiBaseUrl: "https://api.example.test",
    publicMediaBaseUrl: "https://public-media.example.test",
  }),
}));
jest.mock("../ui/components", () => {
  const React = jest.requireActual("react") as typeof import("react");
  const { View } = jest.requireActual("react-native") as typeof import("react-native");
  return {
    AppIcon: () => null,
    Media: (props: Record<string, unknown>) => React.createElement(View, {
      accessibilityLabel: props.accessibilityLabel as string | undefined,
      onError: props.onError,
      source: props.source,
      testID: props.kind === "video" ? "native-video" : "native-image",
    } as never),
  };
});

import { ExerciseMedia } from "./ExerciseMedia";

beforeEach(() => {
  mockUseIsFocused.mockReturnValue(true);
});

test("releases the video subtree when its route loses focus", () => {
  const media = {
    accessibilityLabel: "رسانه حرکت",
    mediaType: "video" as const,
    name: "پرس بالا سینه دمبل",
    path: "/media/incline-press.mp4",
  };
  const { rerender } = render(<ExerciseMedia {...media} />);

  expect(screen.getByTestId("native-video")).toBeTruthy();

  mockUseIsFocused.mockReturnValue(false);
  rerender(<ExerciseMedia {...media} />);

  expect(screen.queryByTestId("native-video")).toBeNull();
});

test("keeps image media available when its route loses focus", () => {
  mockUseIsFocused.mockReturnValue(false);

  render(
    <ExerciseMedia
      accessibilityLabel="تصویر حرکت"
      mediaType="image"
      name="پرس بالا سینه دمبل"
      path="/media/incline-press.webp"
    />,
  );

  expect(screen.queryByTestId("native-video")).toBeNull();
  expect(screen.getByLabelText("تصویر حرکت")).toBeTruthy();
});

test("uses a real poster without mounting a deferred video player", () => {
  render(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      deferVideo
      mediaType="video"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.mp4"
    />,
  );

  expect(screen.queryByTestId("native-video")).toBeNull();
  expect(screen.getByLabelText("پوستر حرکت پرس بالا سینه دمبل").props.source.uri)
    .toBe("https://public-media.example.test/public/exercises/incline-press/media-abc.poster.webp");
  expect(screen.queryByText("برای مشاهده، جزئیات حرکت را باز کن")).toBeNull();
});

test("mounts the deferred video only when its preview is active", () => {
  render(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      deferVideo
      mediaType="video"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.mp4"
      videoActive
    />,
  );

  expect(screen.getByTestId("native-video")).toBeTruthy();
  expect(screen.queryByLabelText("پوستر حرکت پرس بالا سینه دمبل")).toBeNull();
  expect(screen.getByTestId("native-video").props.source.uri)
    .toBe("https://public-media.example.test/public/exercises/incline-press/media-abc.mp4");
});

test("uses the public media base for exercise images", () => {
  render(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      mediaType="image"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.webp"
    />,
  );

  expect(screen.getByLabelText("تصویر حرکت پرس بالا سینه دمبل").props.source.uri)
    .toBe("https://public-media.example.test/public/exercises/incline-press/media-abc.webp");
});

test("uses the same public base for GIF and animated exercise media", () => {
  const { rerender } = render(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      mediaType="gif"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.gif"
    />,
  );
  expect(screen.getByLabelText("تصویر حرکت پرس بالا سینه دمبل").props.source.uri)
    .toBe("https://public-media.example.test/public/exercises/incline-press/media-abc.gif");

  rerender(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      mediaType="animated_webp"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.webp"
    />,
  );
  expect(screen.getByLabelText("تصویر حرکت پرس بالا سینه دمبل").props.source.uri)
    .toBe("https://public-media.example.test/public/exercises/incline-press/media-abc.webp");
});

test("shows the existing fallback when a deferred video poster fails", () => {
  render(
    <ExerciseMedia
      accessibilityLabel="رسانه حرکت"
      deferVideo
      mediaType="video"
      name="پرس بالا سینه دمبل"
      path="/media/exercises/incline-press/media-abc.mp4"
    />,
  );

  fireEvent(screen.getByLabelText("پوستر حرکت پرس بالا سینه دمبل"), "error");

  expect(screen.getByText("نمایش حرکت آماده نیست")).toBeTruthy();
  expect(screen.queryByTestId("native-video")).toBeNull();
});

test("mounts only the explicitly active video in a deferred exercise list", () => {
  render(
    <>
      {["one", "two", "three"].map((slug, index) => (
        <ExerciseMedia
          accessibilityLabel={`رسانه ${slug}`}
          deferVideo
          key={slug}
          mediaType="video"
          name={slug}
          path={`/media/exercises/${slug}/media-${slug}.mp4`}
          videoActive={index === 1}
        />
      ))}
    </>,
  );

  expect(screen.getAllByTestId("native-video")).toHaveLength(1);
  expect(screen.getAllByTestId("native-image")).toHaveLength(2);
});
