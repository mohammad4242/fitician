import test from "node:test";
import { verifyBracesPatch } from "./verify-braces-patch.mjs";

test("installed glob dependency rejects GHSA-vfj7-8cjw-p6xm and matches reviewed source", verifyBracesPatch);
