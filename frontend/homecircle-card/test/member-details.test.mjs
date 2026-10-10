import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { openMemberDialog } from "../src/member-dialog.js";

const dom = new JSDOM("<!doctype html><body></body>");
globalThis.document = dom.window.document;
globalThis.CustomEvent = dom.window.CustomEvent;
dom.window.HTMLDialogElement.prototype.showModal = function () {
  this.open = true;
};
dom.window.HTMLDialogElement.prototype.close = function () {
  this.dispatchEvent(new dom.window.Event("close"));
};

function fixture(overrides = {}) {
  const exampleCoordinate = 0;
  return {
    id: "person.example_member",
    name: "Example",
    presence: "home",
    place: "Home",
    focusable: true,
    issues: [],
    location: {
      latitude: exampleCoordinate,
      longitude: exampleCoordinate,
      origin: "active_gps",
      evidence: {
        source_label: "Tracker: Example phone · Mobile App",
        card_source_label: "Tracker: Home Assistant",
        reported_at: "2026-01-01T10:00:00+00:00",
        observed_at: "2026-01-01T12:00:00+00:00",
        freshness: "stale",
      },
    },
    diagnostics: {
      active_source: "device_tracker.example_phone",
      selected_trackers: [
        {
          entity_id: "device_tracker.example_phone",
          label: "Tracker: Example phone · Mobile App",
          state: "home",
          active: true,
        },
      ],
    },
    ...overrides,
  };
}

function open(member = fixture(), extra = {}) {
  const card = { _data: { members: [member] }, ...extra };
  const dialog = openMemberDialog(
    card,
    { user: { is_admin: false } },
    member.id,
  );
  return {
    card,
    dialog,
    refresh: [...dialog.querySelectorAll("button")].find(
      (control) => control.textContent === "Refresh details",
    ),
  };
}

test("everyday details surface freshness and keep diagnostics expandable", () => {
  const { dialog } = open();
  const technical = dialog.querySelector("details");
  assert.equal(technical.open, false);
  assert.match(
    dialog.querySelector(".report-summary").textContent,
    /Stale report/,
  );
  assert.match(dialog.textContent, /Example phone · Home Assistant/);
  assert.equal(dialog.textContent.includes("Mobile App"), false);
  assert.equal(dialog.textContent.includes("moving test"), false);
  assert.equal(
    technical.contains(
      [...dialog.querySelectorAll("dt")].find(
        (node) => node.textContent === "Map coordinates",
      ),
    ),
    true,
  );
  dialog.close();
});

test("a withheld position surfaces conflict guidance before location and diagnostics", () => {
  const { dialog } = open(
    fixture({
      location: null,
      focusable: false,
      issues: ["tracker_presence_conflict"],
    }),
  );
  const headings = [...dialog.querySelectorAll("h3")].map(
    (node) => node.textContent,
  );
  assert.ok(
    headings.indexOf("Needs attention") < headings.indexOf("Location report"),
  );
  assert.match(
    dialog.querySelector(".report-summary").textContent,
    /Map position withheld/,
  );
  assert.equal(dialog.querySelector("details").open, false);
  dialog.close();
});

test("refresh keeps diagnostics open and reports a source switch separately from time", async () => {
  const { card, dialog, refresh } = open(undefined, {
    _load: async function () {
      this._data.members = [
        fixture({
          location: {
            ...fixture().location,
            evidence: {
              ...fixture().location.evidence,
              source_label: "Tracker: Example cloud",
            },
          },
        }),
      ];
    },
  });
  dialog.querySelector("details").open = true;
  refresh.click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(dialog.querySelector("details").open, true);
  assert.match(
    dialog.querySelector(".refresh-feedback").textContent,
    /Map source changed/,
  );
  assert.equal(
    card._data.members[0].location.evidence.reported_at,
    fixture().location.evidence.reported_at,
  );
  dialog.close();
});

test("disconnected refresh gives the connection reason and does not request data", () => {
  let calls = 0;
  const { dialog, refresh } = open(undefined, {
    _hass: { connected: false },
    _load: async () => {
      calls++;
    },
  });
  refresh.click();
  assert.equal(calls, 0);
  assert.match(
    dialog.querySelector(".refresh-feedback").textContent,
    /disconnected/,
  );
  dialog.close();
});

test("tracker history uses the exact selected entity and closes details", () => {
  let event;
  const { dialog } = open(undefined, {
    dispatchEvent: (value) => {
      event = value;
    },
  });
  dialog.querySelector("details").open = true;
  dialog.querySelector(".history-button").click();
  assert.equal(event.type, "hass-more-info");
  assert.deepEqual(event.detail, {
    entityId: "device_tracker.example_phone",
    view: "history",
  });
  assert.equal(document.querySelector("dialog"), null);
});

test("unknown GPS time is not described as a tracker supplied report", () => {
  const member = fixture();
  member.location.evidence.reported_at = null;
  member.location.evidence.freshness = "unknown";
  const { dialog } = open(member);
  assert.match(
    dialog.querySelector(".report-summary").textContent,
    /HA tracker updated/,
  );
  assert.match(dialog.textContent, /GPS report time unavailable/);
  assert.equal(
    dialog.textContent.includes("Tracker supplied a location report time"),
    false,
  );
  dialog.close();
});

test("recent activity explains observations and keeps older events and diagnostics independent", async () => {
  const events = [
    {
      kind: "refresh",
      value: "requested",
      observed_at: "2026-01-01T12:00:00Z",
    },
    {
      kind: "freshness",
      value: "stale",
      observed_at: "2026-01-01T11:55:00Z",
      reported_at: "2026-01-01T11:00:00Z",
    },
    {
      kind: "source",
      value: "Tracker: Example phone · Mobile App",
      observed_at: "2026-01-01T11:50:00Z",
    },
    { kind: "presence", value: "away", observed_at: "2026-01-01T11:45:00Z" },
    { kind: "started", observed_at: "2026-01-01T11:40:00Z" },
    { kind: "presence", value: "home", observed_at: "2026-01-01T11:40:00Z" },
  ];
  const member = fixture({ activity: { events, persistent: true } });
  const { dialog, card, refresh } = open(member, { _load: async () => {} });
  const activity = dialog.querySelector(".recent-activity");
  assert.match(activity.textContent, /delivery unconfirmed/);
  assert.match(activity.textContent, /Observation started or resumed/);
  assert.match(activity.textContent, /Tracker report:/);
  assert.equal(activity.querySelectorAll("time").length, 6);
  assert.equal(activity.querySelector(".older-activity").open, false);
  activity.querySelector(".older-activity").open = true;
  dialog.querySelector(".technical-details").open = true;
  refresh.click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(dialog.querySelector(".older-activity").open, true);
  assert.equal(dialog.querySelector(".technical-details").open, true);
  assert.equal(card._data.members[0].location.evidence.freshness, "stale");
  dialog.close();
});

test("empty activity and unavailable persistence are explained without raw markup", () => {
  const { dialog } = open(
    fixture({ activity: { events: [], persistent: false } }),
  );
  assert.match(
    dialog.querySelector(".recent-activity").textContent,
    /History begins/,
  );
  assert.match(
    dialog.querySelector(".recent-activity").textContent,
    /only while HomeCircle is running/,
  );
  dialog.close();
  const unsafe = open(
    fixture({
      activity: {
        events: [
          {
            kind: "source",
            value: "<img src=x>",
            observed_at: "2026-01-01T12:00:00Z",
          },
        ],
      },
    }),
  );
  assert.equal(unsafe.dialog.querySelector(".recent-activity img"), null);
  unsafe.dialog.close();
});
