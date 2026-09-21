import assert from "node:assert/strict";
import { test } from "node:test";
import { movedEnough, pullDelta } from "./dragNeighbors.ts";

test("neighbors move a fraction of the drag", () => {
  assert.deepEqual(pullDelta({ x: 0, y: 0 }, { x: 10, y: 0 }), { x: 5.5, y: 0 });
  assert.deepEqual(pullDelta({ x: 1, y: 2 }, { x: 1, y: 12 }), { x: 0, y: 5.5 });
});

test("a tiny nudge does not trigger a relax", () => {
  assert.equal(movedEnough({ x: 0, y: 0 }, { x: 3, y: 4 }), false);
  assert.equal(movedEnough({ x: 0, y: 0 }, { x: 8, y: 0 }), true);
});
