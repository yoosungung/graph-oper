import assert from "node:assert/strict";
import { test } from "node:test";
import { formatAmountMan } from "./amountLabel.ts";

test("won renders as man-won with one decimal", () => {
  assert.equal(formatAmountMan(10_000), "1만원");
  assert.equal(formatAmountMan(15_000), "1.5만원");
  assert.equal(formatAmountMan(63_730), "6.4만원");
  assert.equal(formatAmountMan(450_000_000), "45,000만원");
});
