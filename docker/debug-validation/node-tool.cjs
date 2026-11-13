// Fixed CLI adapters resolve the committed workspace's installed dependency.
const path = require("node:path");
const { createRequire } = require("node:module");
const { pathToFileURL } = require("node:url");
const resolve = createRequire(path.join(process.cwd(), "package.json"));
const tool = process.argv[2];
if (tool !== "typescript" && tool !== "vitest") throw new Error("Unsupported validation tool");
const root = path.dirname(resolve.resolve(`${tool}/package.json`));
const cli = path.join(root, tool === "typescript" ? "bin/tsc" : "vitest.mjs");
process.argv = [process.execPath, cli, ...process.argv.slice(3)];
if (tool === "typescript") require(cli);
else import(pathToFileURL(cli).href).catch(() => { process.exitCode = 1; });
