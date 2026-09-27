import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
const dom = new JSDOM("<!doctype html><body></body>", {
  url: "http://localhost/",
});
for (const key of [
  "window",
  "document",
  "HTMLElement",
  "customElements",
  "CustomEvent",
  "Element",
  "SVGElement",
])
  globalThis[key] = dom.window[key];
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
await import(
  "../../../custom_components/homecircle/frontend/homecircle-card.js"
);
const response = () => ({
  schema_version: 1,
  members: [],
  counts: { home: 0, away: 0, driving: 0, unavailable: 0 },
  focus_ids: { overview: [], home: [], away: [], driving: [], unavailable: [] },
});
const tick = () => new Promise((resolve) => setImmediate(resolve));
function card(hass) {
  const value = document.createElement("homecircle-card");
  value._updateMap = () => {};
  value.setConfig({ type: "custom:homecircle-card" });
  value.hass = hass;
  document.body.append(value);
  return value;
}
test("authorization rejection clears displayed snapshot and retained signatures", async () => {
  let reject = false;
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => {
      if (reject) throw { code: "unauthorized" };
      return response();
    },
  });
  await tick();
  assert.ok(value._data);
  assert.ok(value._signature);
  reject = true;
  await value._load();
  assert.equal(value._data, null);
  assert.equal(value._signature, null);
  assert.match(value.shadowRoot.textContent, /cannot view all selected/);
  value.remove();
});
test("snapshot rejection waits for the timer or a new connection before retrying", async () => {
  let calls = 0;
  const connection = {};
  const failing = async () => {
    calls++;
    throw { code: "unauthorized" };
  };
  const value = card({ connection, connected: true, callWS: failing });
  await tick();
  assert.equal(calls, 1);
  for (let i = 0; i < 5; i++) {
    value.hass = { connection, connected: true, callWS: failing };
    await tick();
  }
  assert.equal(calls, 1);
  await value._load(); // The regular 15-second timer calls this method.
  assert.equal(calls, 2);
  value.hass = {
    connection: {},
    connected: true,
    callWS: async () => response(),
  };
  await tick();
  assert.ok(value._data);
  value.remove();
});
test("same-connection reconnect requests a fresh snapshot", async () => {
  let calls = 0;
  const connection = {};
  const callWS = async () => {
    calls++;
    return response();
  };
  const value = card({ connection, connected: true, callWS });
  await tick();
  value.hass = { connection, connected: false, callWS };
  value.hass = { connection, connected: true, callWS };
  await tick();
  assert.equal(calls, 2);
  assert.ok(value._data);
  value.remove();
});
test("late responses cannot restore data after disconnect; reconnect recovers", async () => {
  let resolve;
  const connection = {};
  const value = card({
    connection,
    connected: true,
    callWS: () => new Promise((r) => (resolve = r)),
  });
  value.hass = { connection, connected: false };
  resolve(response());
  await tick();
  assert.equal(value._data, null);
  assert.match(value.shadowRoot.textContent, /disconnected/);
  value.hass = {
    connection: {},
    connected: true,
    callWS: async () => response(),
  };
  await tick();
  assert.ok(value._data);
  value.remove();
  assert.equal(value._data, null);
  assert.equal(value._signature, null);
  assert.equal(value.shadowRoot.childElementCount, 0);
});
test("editor drops pending household labels when closed", async () => {
  let resolve;
  const value = document.createElement("homecircle-card-editor");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  value.hass = {
    connection: {},
    connected: true,
    callWS: () => new Promise((r) => (resolve = r)),
  };
  value.remove();
  resolve({
    members: [{ id: "person.example_member", name: "Example Member" }],
  });
  await tick();
  assert.equal(value._members, null);
  assert.equal(value.shadowRoot.childElementCount, 0);
});
test("supplied display names are text, never markup", async () => {
  const data = response();
  const name = "<img src=x onerror=alert(1)>";
  data.members = [
    {
      id: "person.example_member",
      name,
      presence: "home",
      primary_home: true,
      place: null,
      focusable: false,
      location: null,
      battery: null,
      charging: null,
      driving: { value: null, status: "unknown" },
    },
  ];
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  assert.ok(value.shadowRoot.textContent.includes(name));
  assert.equal(value.shadowRoot.querySelector("img"), null);
  value.remove();
});

test("tile failure survives rerender and clears on map disposal", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "osm" });
  value._mapNote = document.createElement("div");
  value._points = [{ id: "person.example_member" }];
  value._tileUnavailable = true;
  value._updateMapNote();
  assert.match(value._mapNote.textContent, /Street tiles unavailable/);
  value._updateMapNote();
  assert.match(value._mapNote.textContent, /Street tiles unavailable/);
  value._destroyMap();
  assert.equal(value._tileUnavailable, false);
});

test("stale member styling clears on fresh evidence and keeps pet identity", async () => {
  let freshness = "stale";
  const fictionalOrigin = 0;
  const snapshot = () => ({
    ...response(),
    members: [
      {
        id: "person.example_member",
        name: "Example Pet",
        kind: "pet",
        presence: "home",
        focusable: true,
        location: {
          latitude: fictionalOrigin,
          longitude: fictionalOrigin,
          evidence: {
            reported_at: new Date(Date.now() - 22 * 3600000).toISOString(),
            freshness,
          },
        },
        battery: 28,
        charging: null,
        driving: { value: null, status: "unknown" },
      },
    ],
    focus_ids: {
      overview: ["person.example_member"],
      home: ["person.example_member"],
    },
  });
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => snapshot(),
  });
  await tick();
  assert.ok(value.shadowRoot.querySelector(".member.stale .stale-report"));
  assert.match(value.shadowRoot.textContent, /22 hours/);
  assert.match(value.shadowRoot.textContent, /Pet · Home/);
  freshness = "fresh";
  await value._load();
  assert.equal(value.shadowRoot.querySelector(".member.stale"), null);
  assert.match(value.shadowRoot.textContent, /22 hours/);
  value.remove();
});
