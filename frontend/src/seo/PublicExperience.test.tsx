import { renderToStaticMarkup } from "react-dom/server";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { PublicDiscovery } from "./PublicDiscovery";
import { PublicPage } from "./PublicPage";
import { publicPayload } from "./registry";

it("gives homepage discovery six feature cards and one complete footer", () => {
  const html = renderToStaticMarkup(<PublicDiscovery />);
  expect(html).toContain("بیشتر از فیتیشن کشف کن");
  expect(html.match(/class="discovery-card"/g)).toHaveLength(6);
  expect(html.match(/<footer/g)).toHaveLength(1);
  expect(html).toContain("سیاست تحریریه");
  expect(html).toContain("fitician-brand-logo");
});
it("renders dedicated topic experiences while retaining educational HTML", () => {
  for (const [path, marker] of [["/workout-program", "public-workout"], ["/nutrition", "public-nutrition"],
    ["/body-analysis", "public-body"], ["/learn", "public-learn"], ["/about", "public-about"]]) {
    const payload = publicPayload(path);
    const html = renderToStaticMarkup(<PublicPage payload={payload} />);
    expect(html).toContain(marker);
    expect(html).toContain("fitician-brand-logo");
    expect(html.match(/<h1[ >]/g)).toHaveLength(1);
    expect(html).toContain('href="/login"');
    expect(html.match(/<footer/g)).toHaveLength(1);
    for (const section of payload.page.sections) {
      for (const paragraph of section.paragraphs) expect(html).toContain(paragraph);
    }
  }
});
it("supports an accessible mobile navigation toggle", () => {
  render(<PublicPage payload={publicPayload("/nutrition")} />);
  const button = screen.getByRole("button", { name: "منوی فیتیشن" });
  expect(button).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded", "true");
  fireEvent.keyDown(button, { key: "Escape" });
  expect(button).toHaveAttribute("aria-expanded", "false");
});
