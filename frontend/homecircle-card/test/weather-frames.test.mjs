import { test } from "node:test";
import assert from "node:assert/strict";
import {
  observedFrames,
  forecastFrames,
  frameTime,
} from "../src/weather-frames.js";
test("observed times match pinned mosaic URLs across midnight", () => {
  const frames = observedFrames({ meta: { valid: "2026-10-10T00:10:00Z" } });
  assert.equal(frames.length, 7);
  assert.equal(frames[0].time, Date.parse("2026-10-09T23:40:00Z"));
  assert.match(frames[0].url, /USCOMP-N0Q-202610092340/);
  assert.match(frameTime(frames[0]), /Observed/);
  assert.throws(() => observedFrames({ meta: { valid: "bad" } }));
});
test("forecast frames are future valid times from one explicit model run", () => {
  const frames = forecastFrames(
    { model_init_utc: "2026-10-10T05:00:00Z" },
    Date.parse("2026-10-10T07:10:00Z"),
  );
  assert.equal(frames.length, 9);
  assert.equal(frames[0].time, Date.parse("2026-10-10T07:15:00Z"));
  assert.match(frames[0].url, /REFD-F0135-202610100500/);
  assert.equal(frames.at(-1).time, Date.parse("2026-10-10T09:15:00Z"));
  assert.match(frameTime(frames[0]), /Forecast/);
  assert.throws(() =>
    forecastFrames(
      { model_init_utc: "2026-10-09T00:00:00Z" },
      Date.parse("2026-10-10T07:10:00Z"),
    ),
  );
  assert.throws(() => forecastFrames({ model_init_utc: "invalid" }));
});
