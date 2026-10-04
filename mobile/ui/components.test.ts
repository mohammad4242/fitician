import { createElement } from "react";
import TestRenderer, { act } from "react-test-renderer";
import { expect, it, vi } from "vitest";
import { type ReactNode } from "react";

type NativeElement = {
  readonly type: string;
  readonly props: Record<string, unknown>;
};

const native = vi.hoisted(() => {
  const primitive = (type: string) => (props: Record<string, unknown>) => ({ type, props });
  return {
    ActivityIndicator: primitive("ActivityIndicator"),
    Image: primitive("Image"),
    Modal: primitive("Modal"),
    Pressable: primitive("Pressable"),
    ScrollView: primitive("ScrollView"),
    Text: primitive("Text"),
    TextInput: primitive("TextInput"),
    View: primitive("View"),
    play: vi.fn(),
  };
});

vi.mock("react-native", () => ({
  ...native,
  StyleSheet: {
    absoluteFill: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
    create: <T extends Record<string, unknown>>(styles: T): T => styles,
  },
}));

vi.mock("expo-video", () => ({
  useVideoPlayer: (
    _source: unknown,
    setup?: (player: { loop: boolean; muted: boolean; play: () => void }) => void,
  ) => {
    const player = { loop: false, muted: false, play: native.play };
    setup?.(player);
    return player;
  },
  VideoView: native.View,
}));

vi.mock("react-native-safe-area-context", () => ({ SafeAreaView: native.View }));

import { Button } from "./components/Button";
import { Card } from "./components/Card";
import { Dialog, Sheet } from "./components/Overlay";
import { FormField, TextField } from "./components/Input";
import { Media } from "./components/Media";
import { Notice, Skeleton } from "./components/Feedback";
import { ProgressBar } from "./components/ProgressBar";

function element(value: unknown): NativeElement {
  let current = value as { type: unknown; props: Record<string, unknown> };
  while (typeof current.type === "function") {
    current = renderComponent(() => (current.type as (props: Record<string, unknown>) => unknown)(current.props)) as typeof current;
  }
  expect(current).toMatchObject({ type: expect.any(String), props: expect.any(Object) });
  return current as NativeElement;
}

function flattenStyle(style: unknown): Record<string, unknown> {
  const resolved = typeof style === "function" ? style({ pressed: false }) : style;
  const values = Array.isArray(resolved) ? resolved.flat(Infinity) : [resolved];
  return Object.assign({}, ...values.filter((value): value is Record<string, unknown> => (
    typeof value === "object" && value !== null
  )));
}

it("renders token-based button variants and exposes busy state", () => {
  const result = element(
    renderComponent(() => Button({ label: "Save", loading: true, variant: "primary", onPress: vi.fn() })),
  );

  expect(result.type).toBe("Pressable");
  expect(result.props.accessibilityRole).toBe("button");
  expect(result.props.accessibilityState).toMatchObject({ busy: true, disabled: true });
  expect(result.props.disabled).toBe(true);
  expect(result.props.accessibilityLabel).toBe("Save");
  expect(element(result.props.children).props.accessibilityLabel).toBe("در حال بارگذاری");

  const style = (result.props.style as (state: { pressed: boolean }) => unknown)({ pressed: false });
  expect(style).toEqual(expect.arrayContaining([expect.objectContaining({ backgroundColor: "#50dfce" })]));
});

it("renders fields through a shared form-field shell with error feedback", () => {
  const result = element(
    renderComponent(() => TextField({ label: "Email", error: "Invalid email", value: "bad", onChangeText: vi.fn() })),
  );
  const shell = result;
  const children = shell.props.children as readonly unknown[];

  expect(shell.type).toBe("View");
  expect(element(children[0]).type).toBe("Text");
  expect(element(children[1]).type).toBe("TextInput");
  expect(element(children[2]).props.children).toBe("Invalid email");
  expect(element(children[1]).props.accessibilityHint).toBe("Invalid email");
  expect(element(children[1]).props.allowFontScaling).toBe(true);
});

it("applies the shared RTL boundary to cards, forms, and modal surfaces", () => {
  const card = element(renderComponent(() => Card({ children: "محتوا" })));
  expect(flattenStyle(card.props.style)).toMatchObject({ direction: "rtl" });

  const field = element(renderComponent(() => TextField({ label: "نام", value: "علی", onChangeText: vi.fn() })));
  expect(flattenStyle(field.props.style)).toMatchObject({ direction: "rtl" });

  const sheet = element(renderComponent(() => Sheet({ title: "جزئیات", visible: true, onClose: vi.fn(), children: "بدنه" })));
  expect(flattenStyle(element(sheet.props.children).props.style)).toMatchObject({ direction: "rtl" });

  const dialog = element(renderComponent(() => Dialog({ message: "حذف شود؟", visible: true, onClose: vi.fn() })));
  expect(flattenStyle(element(dialog.props.children).props.style)).toMatchObject({ direction: "rtl" });
});

it("keeps technical input values locally LTR inside the Persian form shell", () => {
  const field = element(
    renderComponent(() => TextField({ label: "ایمیل", textDirection: "ltr", value: "user@example.com", onChangeText: vi.fn() })),
  );
  const input = element((field.props.children as readonly unknown[])[1]);

  expect(flattenStyle(field.props.style)).toMatchObject({ direction: "rtl" });
  expect(flattenStyle(input.props.style)).toMatchObject({
    textAlign: "left",
    writingDirection: "ltr",
  });
});

it("infers LTR for technical fields when callers omit a direction", () => {
  const password = element(
    renderComponent(() => TextField({ label: "رمز عبور", secureTextEntry: true, value: "secret", onChangeText: vi.fn() })),
  );
  const numeric = element(
    renderComponent(() => TextField({ label: "کد", keyboardType: "number-pad", value: "1234", onChangeText: vi.fn() })),
  );
  const email = element(
    renderComponent(() => TextField({ label: "ایمیل", keyboardType: "email-address", value: "user@example.com", onChangeText: vi.fn() })),
  );
  const url = element(
    renderComponent(() => TextField({ label: "لینک", keyboardType: "url", value: "https://example.com", onChangeText: vi.fn() })),
  );

  expect(flattenStyle(element((password.props.children as readonly unknown[])[1]).props.style)).toMatchObject({
    textAlign: "left",
    writingDirection: "ltr",
  });
  expect(flattenStyle(element((numeric.props.children as readonly unknown[])[1]).props.style)).toMatchObject({
    textAlign: "left",
    writingDirection: "ltr",
  });
  expect(flattenStyle(element((email.props.children as readonly unknown[])[1]).props.style)).toMatchObject({
    textAlign: "left",
    writingDirection: "ltr",
  });
  expect(flattenStyle(element((url.props.children as readonly unknown[])[1]).props.style)).toMatchObject({
    textAlign: "left",
    writingDirection: "ltr",
  });
});

it("anchors shared progress bars to the RTL start edge", () => {
  const progress = element(renderComponent(() => ProgressBar({ label: "پیشرفت", progress: 0.5 })));

  expect(flattenStyle(progress.props.style)).toMatchObject({ direction: "rtl" });
});

it("preserves font scaling and source order for the shared button label", () => {
  const result = element(renderComponent(() => Button({ label: "Save", onPress: vi.fn() })));
  const label = element(result.props.children);

  expect(label.type).toBe("Text");
  expect(label.props.allowFontScaling).toBe(true);
  expect(label.props.children).toBe("Save");
});

it("supports reusable form-field content around non-text controls", () => {
  const result = element(
    renderComponent(() => FormField({
      description: "Optional",
      label: "Goal",
      children: native.View({}) as unknown as ReactNode,
    })),
  );
  const children = result.props.children as readonly unknown[];

  expect(result.type).toBe("View");
  expect(element(children[0]).props.children).toContain("Goal");
  expect(element(children[1]).type).toBe("View");
  expect(element(children[2]).props.children).toBe("Optional");
});

it("uses a pressable card only when the card is interactive", () => {
  const interactive = element(renderComponent(() => Card({ onPress: vi.fn(), variant: "interactive", children: "Plan" })));
  const staticCard = element(renderComponent(() => Card({ children: "Plan" })));

  expect(interactive.type).toBe("Pressable");
  expect(interactive.props.accessibilityRole).toBe("button");
  expect(staticCard.type).toBe("View");
});

it("keeps sheet and dialog overlays native and dismissible", () => {
  const onClose = vi.fn();
  const sheet = element(renderComponent(() => Sheet({ title: "Details", visible: true, onClose, children: "Body" })));
  const dialog = element(
    renderComponent(() => Dialog({
      message: "Delete this item?",
      onClose,
      onConfirm: vi.fn(),
      title: "Confirm",
      visible: true,
    })),
  );

  expect(sheet.type).toBe("Modal");
  expect(sheet.props.animationType).toBe("slide");
  expect(sheet.props.onRequestClose).toBe(onClose);
  expect(dialog.type).toBe("Modal");
  expect(dialog.props.animationType).toBe("fade");
  expect(dialog.props.onRequestClose).toBe(onClose);
});

it("provides skeleton, notices, and native image/video media", () => {
  const skeleton = element(renderComponent(() => Skeleton({ height: 24, width: "100%" })));
  const notice = element(renderComponent(() => Notice({ message: "Offline", title: "Connection", variant: "offline" })));
  const image = element(renderComponent(() => Media({ source: { uri: "https://example.test/image.jpg" } })));
  const video = element(renderComponent(() => Media({ kind: "video", source: "https://example.test/video.mp4", autoplay: true })));

  expect(skeleton.type).toBe("View");
  expect(notice.type).toBe("View");
  expect(image.type).toBe("Image");
  expect(video.type).toBe("View");
  expect(native.play).toHaveBeenCalledOnce();
});

vi.mock("expo-secure-store", () => ({ getItemAsync: vi.fn(async () => null), setItemAsync: vi.fn(async () => undefined) }));

// Mount the component so runtime theme hooks execute with a real React dispatcher.
function renderComponent(run: () => unknown): unknown {
  let result: unknown;
  act(() => { TestRenderer.create(createElement(function Capture() { result = run(); return null; })); });
  return result;
}
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
