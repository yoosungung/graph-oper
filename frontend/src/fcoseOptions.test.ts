import assert from "node:assert/strict";
import { test } from "node:test";
import { expandLayout, relaxLayout, seedLayout } from "./fcoseOptions.ts";

test("layouts stay on current positions with fCoSE proof quality", () => {
  for (const options of [seedLayout(), expandLayout(), relaxLayout("n", { x: 1, y: 2 })]) {
    assert.equal(options.name, "fcose");
    assert.equal(options.randomize, false);
    assert.equal(options.quality, "proof");
    assert.equal(options.packComponents, false);
  }
});

test("seed fits the view, expand keeps the camera", () => {
  assert.equal(seedLayout().fit, true);
  assert.equal(seedLayout().animate, false);
  assert.equal(expandLayout().fit, false);
  assert.equal(expandLayout().animate, true);
});

test("relax pins the dropped node", () => {
  const options = relaxLayout("Phone:010", { x: 12, y: 34 });
  assert.equal(options.fit, false);
  assert.deepEqual(options.fixedNodeConstraint, [
    { nodeId: "Phone:010", position: { x: 12, y: 34 } },
  ]);
});
