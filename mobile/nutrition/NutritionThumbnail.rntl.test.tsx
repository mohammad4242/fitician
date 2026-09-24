import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";

jest.mock("../config/nativeRuntimeConfig", () => ({ getMobileRuntimeConfig: jest.fn() }));
jest.mock("../ui/components/AppIcon", () => ({ AppIcon: () => null }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => null }));

import { getMobileRuntimeConfig } from "../config/nativeRuntimeConfig";
import { NutritionThumbnail } from "./NutritionThumbnail";

const mockGetMobileRuntimeConfig = jest.mocked(getMobileRuntimeConfig);
const defaultRuntimeConfig = {
  apiBaseUrl: "https://api.example.test",
  appLinkHost: "fitician.fit",
  environment: "development" as const,
  frontendOrigin: "https://fitician.fit",
  googleAndroidClientId: null,
  googleIosClientId: null,
  googleWebClientId: null,
  publicMediaBaseUrl: "https://public-media.example.test",
};

beforeEach(() => {
  mockGetMobileRuntimeConfig.mockReturnValue(defaultRuntimeConfig);
});

test("resolves catalogue media through the public base and shows loading", () => {
  render(<NutritionThumbnail imageUrl="/media/meal-catalogue/meal.webp" name="عدسی" />);
  const image = screen.getByLabelText("تصویر عدسی");
  expect(image.props.source.uri)
    .toBe("https://public-media.example.test/public/meal-catalogue/meal.webp");
  expect(screen.getByLabelText("در حال بارگذاری تصویر")).toBeTruthy();
});

test("falls back after an image load error", () => {
  render(<NutritionThumbnail imageUrl="/media/meal-catalogue/meal.webp" name="عدسی" />);
  const image = screen.getByLabelText("تصویر عدسی");
  fireEvent(image, "error");
  expect(screen.queryByLabelText("در حال بارگذاری تصویر")).toBeNull();
  expect(screen.getByLabelText("تصویر عدسی موجود نیست")).toBeTruthy();
});

test("falls back to the backend in development without a public media base", () => {
  mockGetMobileRuntimeConfig.mockReturnValue({
    ...defaultRuntimeConfig,
    publicMediaBaseUrl: null,
  });
  render(<NutritionThumbnail imageUrl="/media/meal.webp" name="عدسی" />);
  expect(screen.getByLabelText("تصویر عدسی").props.source.uri)
    .toBe("https://api.example.test/media/meal.webp");
});

test("rejects unrelated absolute URLs and recovers when the image changes", () => {
  const view = render(<NutritionThumbnail imageUrl={null} name="عدسی" />);
  expect(screen.getByLabelText("تصویر عدسی موجود نیست")).toBeTruthy();
  view.rerender(<NutritionThumbnail imageUrl="https://cdn.example.test/a.webp" name="عدسی" />);
  expect(screen.getByLabelText("تصویر عدسی موجود نیست")).toBeTruthy();
});
