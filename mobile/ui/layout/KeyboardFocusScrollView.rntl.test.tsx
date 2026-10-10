import { act, renderHook } from "@testing-library/react-native";
import { afterEach, beforeEach, expect, jest, test } from "@jest/globals";
import { Keyboard, Platform, TextInput, type ScrollView } from "react-native";

const mockScroll = jest.fn();
let inputY = 230;
const focusedInput = { measureInWindow: (callback: (x: number, y: number, width: number, height: number) => void) => callback(16, inputY, 328, 52) };
let onKeyboardShow: () => void;
let mockRemove: ReturnType<typeof jest.fn>;

import { useAndroidKeyboardFocusScroll } from "./KeyboardFocusScrollView";

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
  inputY = 230;
  mockScroll.mockClear();
});

afterEach(() => { jest.restoreAllMocks(); jest.useRealTimers(); });

function useScroll() {
  return useAndroidKeyboardFocusScroll({
    current: {
      getNativeScrollRef: () => ({ measureInWindow: (callback: (x: number, y: number, width: number, height: number) => void) => callback(0, 22, 360, 253) }),
      scrollTo: mockScroll,
    } as unknown as ScrollView,
  }, 16, { current: 200 });
}

test("reveals the complete focused input within the reduced Android scroll viewport", () => {
  renderHook(useScroll);
  act(() => onKeyboardShow());
  expect(mockScroll).not.toHaveBeenCalled();
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).toHaveBeenCalledWith({ y: 223, animated: true });
});

test("reveals a new OTP input when the keyboard is already open", () => {
  const { result } = renderHook(useScroll);
  act(() => result.current());
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).toHaveBeenCalledTimes(1);
});

test("does not move an input already fully visible", () => {
  inputY = 100;
  const { result } = renderHook(useScroll);
  act(() => result.current());
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).not.toHaveBeenCalled();
});

test("reveals an input above the viewport without negative offsets", () => {
  inputY = 10;
  const { result } = renderHook(useScroll);
  act(() => result.current());
  act(() => jest.advanceTimersByTime(20));
  expect(mockScroll).toHaveBeenCalledWith({ y: 172, animated: true });
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
