import { act, renderHook } from "@testing-library/react-native";
import { afterEach, beforeEach, expect, jest, test } from "@jest/globals";
import { Keyboard, Platform, TextInput, type ScrollView } from "react-native";

import { useAndroidKeyboardFocusScroll } from "./KeyboardFocusScrollView";

const mockScroll = jest.fn();
const focusedInput = {};
let onKeyboardShow: () => void;
let mockRemove: ReturnType<typeof jest.fn>;

beforeEach(() => {
  jest.useFakeTimers();
  jest.replaceProperty(Platform, "OS", "android");
  jest.spyOn(Keyboard, "isVisible").mockReturnValue(true);
  jest.spyOn(TextInput.State, "currentlyFocusedInput").mockReturnValue(focusedInput as never);
  mockRemove = jest.fn();
  jest.spyOn(Keyboard, "addListener").mockImplementation((event, listener) => {
    if (event === "keyboardDidShow") onKeyboardShow = listener as () => void;
    return { remove: mockRemove } as never;
  });
  mockScroll.mockClear();
});

afterEach(() => {
  jest.restoreAllMocks();
  jest.useRealTimers();
});

function useScroll() {
  return useAndroidKeyboardFocusScroll({
    current: { scrollResponderScrollNativeHandleToKeyboard: mockScroll } as unknown as ScrollView,
  }, 40);
}

test("reveals the focused input after Android keyboard layout settles", () => {
  renderHook(useScroll);
  act(() => onKeyboardShow());
  expect(mockScroll).not.toHaveBeenCalled();
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).toHaveBeenCalledWith(focusedInput, 40, true);
});

test("reveals a new OTP input when the keyboard is already open", () => {
  const { result } = renderHook(useScroll);
  act(() => result.current());
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).toHaveBeenCalledTimes(1);
});

test("does not scroll after the keyboard closes or the form unmounts", () => {
  const { result, unmount } = renderHook(useScroll);
  act(() => result.current());
  jest.mocked(Keyboard.isVisible).mockReturnValue(false);
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).not.toHaveBeenCalled();
  jest.mocked(Keyboard.isVisible).mockReturnValue(true);
  act(() => result.current());
  unmount();
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).not.toHaveBeenCalled();
  expect(mockRemove).toHaveBeenCalled();
});
