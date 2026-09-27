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
