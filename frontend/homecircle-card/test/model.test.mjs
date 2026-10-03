import { test } from "node:test";
import assert from "node:assert/strict";
import {
  selection,
  visibleMembers,
  markerGroups,
  pinFitPadding,
  reportLabel,
  validateConfig,
} from "../src/model.js";
// Fictional origin and screen separation; never household coordinates.
const origin = 0,
  screenSeparation = 100;
const member = (id, presence = "home", focusable = true) => ({
  id,
  name: id,
  presence,
  focusable,
  location: focusable
    ? { latitude: origin, longitude: origin, evidence: { reported_at: null } }
    : null,
});
test("Home focus excludes secondary residences while counts can include them", () => {
  const members = [
    member("house"),
    member("residence"),
    member("router", "home", false),
  ];
  assert.equal(members.filter((m) => m.presence === "home").length, 3);
  assert.deepEqual(
    selection(members, "home", { home: ["house"] }).map((m) => m.id),
    ["house"],
  );
  assert.deepEqual(
    selection(members, "overview", { overview: ["house", "residence"] }).map(
      (m) => m.id,
    ),
    ["house", "residence"],
  );
  assert.equal(selection(members, "router", {}).length, 0);
});
test("hidden members stay out of map and member selection", () => {
  const members = visibleMembers(
    { members: [member("visible"), member("hidden")] },
    ["hidden"],
  );
  assert.deepEqual(
    selection(members, "overview", { overview: ["visible", "hidden"] }).map(
      (m) => m.id,
    ),
    ["visible"],
  );
});
test("screen overlap groups remain individually selectable", () => {
  const members = [member("one"), member("two"), member("three")];
  members[2].location.longitude = screenSeparation;
  const groups = markerGroups(members, (p) => ({
    x: p.longitude,
    y: p.latitude,
  }));
  assert.deepEqual(
    groups.map((g) => g.members.map((m) => m.id)),
    [["one", "two"], ["three"]],
  );
});
test("pin fit padding leaves positive map area on narrow cards", () => {
  for (const size of [
    { x: 140, y: 220 },
    { x: 314, y: 220 },
    { x: 25, y: 25 },
  ]) {
    const { paddingTopLeft, paddingBottomRight } = pinFitPadding(size);
    assert.ok(paddingTopLeft[0] + paddingBottomRight[0] < size.x);
    assert.ok(paddingTopLeft[1] + paddingBottomRight[1] < size.y);
  }
  assert.deepEqual(pinFitPadding({ x: 314, y: 220 }), {
    paddingTopLeft: [112, 120],
    paddingBottomRight: [48, 48],
  });
});
test("unknown report time is never a live claim; stale remains explicit", () => {
  const value = member("one");
  assert.match(reportLabel(value), /unknown/);
  value.location.evidence = {
    reported_at: "2026-01-01T00:00:00Z",
    freshness: "stale",
  };
  assert.match(
    reportLabel(value, Date.parse("2026-01-01T00:20:00Z")),
    /Stale.*20 min/,
  );
  assert.match(reportLabel(member("none", "home", false)), /No usable/);
});
test("HA observation time is labeled separately when report time is unknown", () => {
  const value = member("phone");
  const now = Date.parse("2026-01-01T01:00:00Z");
  value.location.evidence.observed_at = "2026-01-01T00:26:00Z";
  assert.equal(
    reportLabel(value, now),
    "HA state updated 34 min ago · Location report time unknown",
  );
  value.location.evidence.reported_at = "2026-01-01T00:50:00Z";
  value.location.evidence.freshness = "fresh";
  assert.equal(reportLabel(value, now), "Reported 10 min ago");
  value.location.evidence.reported_at = null;
  value.location.evidence.observed_at = "2026-01-01T01:10:00Z";
  assert.equal(reportLabel(value, now), "Location report time unknown");
});
test("tiles are opt-in and invalid provider choices are rejected", () => {
  assert.equal(
    validateConfig({ type: "custom:homecircle-card" }).map_tiles,
    "none",
  );
  assert.throws(() =>
    validateConfig({ type: "custom:homecircle-card", map_tiles: "unapproved" }),
  );
});

test("report ages use readable units without disguising stale or invalid evidence", () => {
  const value = member("one");
  const stamp = Date.parse("2026-01-01T00:00:00Z");
  value.location.evidence = {
    reported_at: new Date(stamp).toISOString(),
    freshness: "stale",
  };
  for (const [minutes, label] of [
    [0, "less than a minute"],
    [59, "59 min"],
    [60, "1 hour"],
    [1336, "22 hours"],
    [1440, "1 day"],
    [2880, "2 days"],
  ]) {
    assert.equal(
      reportLabel(value, stamp + minutes * 60000),
      `Stale · Reported ${label} ago`,
    );
  }
  value.location.evidence.reported_at = "invalid";
  assert.match(reportLabel(value), /unknown/);
});
