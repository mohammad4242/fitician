import { useCallback, useEffect, useRef, type RefObject } from "react";
import { Keyboard, Platform, ScrollView, TextInput, type ScrollViewProps } from "react-native";

export function useAndroidKeyboardFocusScroll(
  scrollRef: RefObject<ScrollView | null>,
  extraOffset: number,
) {
  const frame = useRef<number | null>(null);
  const reveal = useCallback(() => {
    if (Platform.OS !== "android" || !Keyboard.isVisible()) return;
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      frame.current = null;
      if (!Keyboard.isVisible()) return;
      const input = TextInput.State.currentlyFocusedInput();
      if (input) {
        scrollRef.current?.scrollResponderScrollNativeHandleToKeyboard(input, extraOffset, true);
      }
    });
  }, [extraOffset, scrollRef]);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    const subscription = Keyboard.addListener("keyboardDidShow", reveal);
    return () => {
      subscription.remove();
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    };
  }, [reveal]);
  return reveal;
}

export function KeyboardFocusScrollView({
  keyboardOffset,
  onFocus,
  onLayout,
  onContentSizeChange,
  ...props
}: ScrollViewProps & { readonly keyboardOffset: number }) {
  const scrollRef = useRef<ScrollView>(null);
  const reveal = useAndroidKeyboardFocusScroll(scrollRef, keyboardOffset);
  return (
    <ScrollView
      {...props}
      ref={scrollRef}
      onFocus={(event) => { onFocus?.(event); reveal(); }}
      onLayout={(event) => { onLayout?.(event); reveal(); }}
      onContentSizeChange={(width, height) => { onContentSizeChange?.(width, height); reveal(); }}
    />
  );
}
