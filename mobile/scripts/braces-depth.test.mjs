import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const braces = require("braces");
const boundedDepthError = { name: "SyntaxError", message: /nesting depth/ };
const nested = (open, close, depth) => open.repeat(depth) + "a" + close.repeat(depth);

for (const method of ["parse", "compile", "expand", "stringify"]) {
  test(`${method} rejects the advisory's deeply nested brace pattern before stack exhaustion`, () => {
    assert.throws(() => braces[method](nested("{", "}", 4000)), boundedDepthError);
  });
}

test("parentheses and mixed containers cannot bypass the nesting bound", () => {
  assert.throws(() => braces.compile(nested("(", ")", 4000)), boundedDepthError);
  assert.throws(() => braces.parse("({".repeat(65) + "a" + "})".repeat(65)), boundedDepthError);
});

for (const method of ["compile", "expand", "stringify"]) {
  test(`${method} rejects deep externally supplied ASTs and cycles`, () => {
    const ast = { type: "root", nodes: [] };
    let node = ast;
    for (let i = 0; i < 4000; i++) {
      const child = { type: "root", nodes: [], parent: node };
      node.nodes.push(child);
      node = child;
    }
    assert.throws(() => braces[method](ast), boundedDepthError);
    const cycle = { type: "root", nodes: [] };
    cycle.nodes.push(cycle);
    assert.throws(() => braces[method](cycle), boundedDepthError);
  });
}

test("the 128-container boundary remains usable", () => {
  const pattern = nested("{", "}", 128);
  const ast = braces.parse(pattern);
  assert.equal(braces.stringify(ast), pattern);
  assert.doesNotThrow(() => braces.compile(ast));
  assert.doesNotThrow(() => braces.expand(ast));
  assert.throws(() => braces.parse(nested("{", "}", 129)), boundedDepthError);
});

test("ordinary ranges, alternatives, escaping, quotes and glob consumers keep their behavior", () => {
  assert.equal(braces.compile("a/{b,c}/d"), "a/(b|c)/d");
  assert.deepEqual(braces.expand("a/{b,c}/d"), ["a/b/d", "a/c/d"]);
  assert.deepEqual(braces.expand("{1..3}"), ["1", "2", "3"]);
  assert.deepEqual(braces.expand("{a,b}{1,2}"), ["a1", "a2", "b1", "b2"]);
  assert.deepEqual(braces.expand("\\{literal\\}"), ["{literal}"]);
  assert.deepEqual(braces.expand('"{literal}"'), ["{literal}"]);
  assert.deepEqual(braces.expand("[{literal}]"), ["[{literal}]"]);
  const micromatch = require("micromatch");
  assert.deepEqual(micromatch(["src/a.ts", "src/b.tsx", "src/c.js"], "src/*.{ts,tsx}"),
    ["src/a.ts", "src/b.tsx"]);
});

test("unbalanced input and caller options cannot disable the depth bound", () => {
  assert.throws(() => braces.parse("{".repeat(129)), boundedDepthError);
  assert.throws(() => braces.parse(nested("{", "}", 4000), { maxDepth: Infinity }), boundedDepthError);
  assert.equal(braces.stringify(braces.parse('"' + nested("{", "}", 4000) + '"')),
    nested("{", "}", 4000));
});
