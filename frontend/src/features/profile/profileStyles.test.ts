import { expect, it } from "vitest";

type FileSystem = {
  readFileSync: (path: string, encoding: "utf8") => string;
};

const nodeProcess = (globalThis as typeof globalThis & {
  process: { getBuiltinModule: (name: "fs") => FileSystem };
}).process;
const profileCss = nodeProcess
  .getBuiltinModule("fs")
  .readFileSync("src/features/profile/profile.css", "utf8");

it("keeps profile questions readable, helpers muted, and section legends accented", () => {
  expect(profileCss).toMatch(
    /\.profile-form \.profile-field label\s*\{[^}]*color:\s*var\(--fit(?:ician|sho)-ink\)/,
  );
  expect(profileCss).toMatch(
    /\.profile-form \.profile-field__hint\s*\{[^}]*color:\s*var\(--fit(?:ician|sho)-muted\)/,
  );
  expect(profileCss).toMatch(
    /\.profile-form \.profile-fieldset legend\s*\{[^}]*color:\s*var\(--fitician-accent-ink\)/,
  );
});
