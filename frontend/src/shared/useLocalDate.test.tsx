import { act, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useLocalDate } from "./useLocalDate";

it("changes the date at midnight rather than waiting for the next polling interval", () => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(new Date(2026, 8, 29, 23, 59, 50));
    function Probe() { return <span>{useLocalDate()}</span>; }
    render(<Probe />);
    expect(screen.getByText("2026-09-29")).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(10_000); });
    expect(screen.getByText("2026-09-30")).toBeInTheDocument();
  } finally { vi.useRealTimers(); }
});
