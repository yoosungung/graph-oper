import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDurationMin } from "./durationLabel.ts";

test("seconds render as minutes with one decimal", () => {
  assert.equal(formatDurationMin(60), "1분");
  assert.equal(formatDurationMin(90), "1.5분");
  assert.equal(formatDurationMin(27), "0.5분");
  assert.equal(formatDurationMin(2544), "42.4분");
});
