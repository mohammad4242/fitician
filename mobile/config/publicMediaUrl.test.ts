import { describe, expect, it } from "vitest";

import { resolvePublicMediaUrl } from "./publicMediaUrl";

const apiBaseUrl = "https://api.example.test/";

function config(publicMediaBaseUrl: string | null) {
  return { apiBaseUrl, publicMediaBaseUrl };
}

describe("native public media URLs", () => {
  it("maps managed media paths to the Web public object layout", () => {
    expect(resolvePublicMediaUrl("/media/foo/bar.webp", config("https://media.example.test")))
      .toBe("https://media.example.test/public/foo/bar.webp");
    expect(resolvePublicMediaUrl("/exercises/foo/bar.gif", config("https://media.example.test")))
      .toBe("https://media.example.test/public/exercises/foo/bar.gif");
  });

  it("normalizes trailing slashes on the public media base", () => {
    expect(resolvePublicMediaUrl("/media/foo.webp", config("https://media.example.test///")))
      .toBe("https://media.example.test/public/foo.webp");
  });

  it("uses the safe backend resolver when the public media base is absent", () => {
    expect(resolvePublicMediaUrl("/media/foo.webp", config(null)))
      .toBe("https://api.example.test/media/foo.webp");
  });

  it("accepts absolute URLs from the configured public media base or backend", () => {
    expect(resolvePublicMediaUrl(
      "https://media.example.test/public/foo.webp",
      config("https://media.example.test/"),
    )).toBe("https://media.example.test/public/foo.webp");
    expect(resolvePublicMediaUrl("https://api.example.test/media/foo.webp", config(null)))
      .toBe("https://api.example.test/media/foo.webp");
  });

  it("rejects unrelated absolute origins, traversal, and protocol-relative paths", () => {
    for (const path of [
      "https://cdn.example.test/foo.webp",
      "javascript:alert(1)",
      "file:///etc/passwd",
      "data:image/png;base64,abc",
      "/media/../private.webp",
      "/media/%2e%2e/private.webp",
      "/media/foo\\bar.webp",
      "//media.example.test/public/foo.webp",
      "/uploads/foo.webp",
    ]) {
      expect(() => resolvePublicMediaUrl(path, config("https://media.example.test"))).toThrow();
    }
  });

  it("resolves an exercise video and its poster beside each other on the same public base", () => {
    const runtime = config("https://media.example.test/");
    expect(resolvePublicMediaUrl("/media/exercises/bench/media-abc.mp4", runtime))
      .toBe("https://media.example.test/public/exercises/bench/media-abc.mp4");
    expect(resolvePublicMediaUrl("/media/exercises/bench/media-abc.poster.webp", runtime))
      .toBe("https://media.example.test/public/exercises/bench/media-abc.poster.webp");
  });
});
