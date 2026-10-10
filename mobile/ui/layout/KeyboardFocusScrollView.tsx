import { useCallback, useEffect, useRef, type RefObject } from "react";
import { Keyboard, Platform, ScrollView, TextInput, type ScrollViewProps } from "react-native";

export function useAndroidKeyboardFocusScroll(
  scrollRef: RefObject<ScrollView | null>,
  extraOffset: number,
  scrollOffset: RefObject<number>,
) {
  const frame = useRef<number | null>(null);
  const generation = useRef(0);
  const mounted = useRef(true);
  const reveal = useCallback(() => {
    if (Platform.OS !== "android" || !Keyboard.isVisible()) return;
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    const request = ++generation.current;
    frame.current = requestAnimationFrame(() => {
      frame.current = null;
      if (!Keyboard.isVisible()) return;
      const input = TextInput.State.currentlyFocusedInput();
      const scroll = scrollRef.current;
      if (!input || !scroll) return;
      // The keyboard frame can extend below KeyboardAvoidingView's viewport.
      // Measure that viewport rather than scrolling to the keyboard edge.
      scroll.getNativeScrollRef()?.measureInWindow((_x, viewportY, _width, viewportHeight) => {
        input.measureInWindow((_inputX, inputY, _inputWidth, inputHeight) => {
          if (!mounted.current || request !== generation.current || !Keyboard.isVisible()
            || TextInput.State.currentlyFocusedInput() !== input || scrollRef.current !== scroll) return;
          if (viewportHeight <= 0 || inputHeight <= 0) return;
          const above = inputY - viewportY - extraOffset;
          const below = inputY + inputHeight + extraOffset - viewportY - viewportHeight;
          const delta = inputHeight + extraOffset * 2 > viewportHeight
            ? above
            : below > 0 ? below : above < 0 ? above : 0;
          if (delta !== 0) scroll.scrollTo({ y: Math.max(0, scrollOffset.current + delta), animated: true });
        });
      });
    });
  }, [extraOffset, scrollOffset, scrollRef]);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    mounted.current = true;
    const subscription = Keyboard.addListener("keyboardDidShow", reveal);
    return () => {
      subscription.remove();
      mounted.current = false;
      generation.current += 1;
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
  onScroll,
  ...props
}: ScrollViewProps & { readonly keyboardOffset: number }) {
  const scrollRef = useRef<ScrollView>(null);
  const scrollOffset = useRef(0);
  const reveal = useAndroidKeyboardFocusScroll(scrollRef, keyboardOffset, scrollOffset);
  return (
    <ScrollView
      {...props}
      ref={scrollRef}
      scrollEventThrottle={props.scrollEventThrottle ?? 16}
      onScroll={(event) => { scrollOffset.current = event.nativeEvent.contentOffset.y; onScroll?.(event); }}
      onFocus={(event) => { onFocus?.(event); reveal(); }}
      onLayout={(event) => { onLayout?.(event); reveal(); }}
      onContentSizeChange={(width, height) => { onContentSizeChange?.(width, height); reveal(); }}
    />
  );
}
