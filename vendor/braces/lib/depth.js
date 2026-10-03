'use strict';

// Bound every recursive walker, including caller-supplied ASTs.
const MAX_DEPTH = 128;
const checkDepth = depth => {
  if (depth > MAX_DEPTH) {
    throw new SyntaxError(`Input nesting depth exceeds maximum (${MAX_DEPTH})`);
  }
};

const assertAstDepth = ast => {
  const pending = [{ node: ast, depth: 0 }];
  while (pending.length) {
    const { node, depth } = pending.pop();
    if (!node || !Array.isArray(node.nodes)) continue;
    checkDepth(depth);
    for (const child of node.nodes) {
      pending.push({ node: child, depth: depth + 1 });
    }
  }
};

module.exports = { checkDepth, assertAstDepth };
