import { test } from "node:test";
import assert from "node:assert/strict";
import { cropRectangle } from "../src/picture-crop.js";

test("square crop fits the full photo and can zoom out with white padding", () => {
  assert.deepEqual(cropRectangle(800, 400), { x: 0, y: -200, side: 800 });
  assert.deepEqual(cropRectangle(400, 800), { x: -200, y: 0, side: 800 });
  assert.deepEqual(cropRectangle(800, 400, 0.5), {
    x: -400,
    y: -600,
    side: 1600,
  });
  assert.deepEqual(cropRectangle(800, 400, 2, -100, 100), {
    x: 0,
    y: 0,
    side: 400,
  });
  assert.deepEqual(cropRectangle(800, 400, 2, 300, -300), {
    x: 400,
    y: 0,
    side: 400,
  });
});
