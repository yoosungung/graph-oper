import assert from "node:assert/strict";
import { test } from "node:test";
import { edgeWidth } from "./edgeWidth.ts";

test("ownership edges stay thin", () => {
  assert.equal(edgeWidth("OwnsPhone", {}), 1.2);
  assert.equal(edgeWidth("OwnsAccount", {}), 1.2);
});

test("more calls or longer duration makes a thicker link", () => {
  const few = edgeWidth("Called", { count: 1, duration_sec: 60 });
  const many = edgeWidth("Called", { count: 6, duration_sec: 60 });
  const longer = edgeWidth("Called", { count: 1, duration_sec: 600 });
  assert.ok(many > few);
  assert.ok(longer > few);
});

test("more transfers or larger amount makes a thicker link", () => {
  const small = edgeWidth("Transferred", { count: 1, amount: 10000 });
  const many = edgeWidth("Transferred", { count: 10, amount: 10000 });
  const large = edgeWidth("Transferred", { count: 1, amount: 1_000_000 });
  assert.ok(many > small);
  assert.ok(large > small);
});

test("extreme volume is clamped", () => {
  const huge = edgeWidth("Transferred", { count: 60, amount: 450_000_000 });
  assert.equal(huge, 8);
});
