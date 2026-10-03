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
test("scheduled refresh retries a rejected snapshot", async () => {
  let calls = 0;
  let refresh;
  const original = globalThis.setInterval;
  globalThis.setInterval = (callback, delay) => {
    assert.equal(delay, 15000);
    refresh = callback;
    return undefined;
  };
  try {
    const value = card({
      connection: {},
      connected: true,
      callWS: async () => {
        calls++;
        throw { code: "unauthorized" };
      },
    });
    await tick();
    assert.equal(calls, 1);
    refresh();
    await tick();
    assert.equal(calls, 2);
    value.remove();
  } finally {
    globalThis.setInterval = original;
  }
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
  assert.ok(value.shadowRoot.querySelector(".member.stale .report-part.stale"));
  assert.match(value.shadowRoot.textContent, /22 hours/);
  assert.match(value.shadowRoot.textContent, /Pet · Home/);
  assert.match(value.shadowRoot.textContent, /Battery 28%/);
  freshness = "fresh";
  await value._load();
  assert.equal(value.shadowRoot.querySelector(".member.stale"), null);
  assert.match(value.shadowRoot.textContent, /22 hours/);
  value.remove();
});

test("unknown report time stays distinct from an HA observation on a member card", async () => {
  const fictionalOrigin = 0;
  const data = response();
  data.members = [
    {
      id: "person.example_phone",
      name: "Example Phone",
      kind: "person",
      presence: "home",
      place: "Example Residence",
      focusable: true,
      location: {
        latitude: fictionalOrigin,
        longitude: fictionalOrigin,
        evidence: {
          reported_at: null,
          observed_at: new Date(Date.now() - 10 * 60000).toISOString(),
        },
      },
      battery: 44,
      charging: false,
      driving: { value: null, status: "unknown" },
    },
  ];
  data.focus_ids.overview = ["person.example_phone"];
  data.focus_ids.home = ["person.example_phone"];
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  const member = value.shadowRoot.querySelector(".member");
  assert.match(
    member.querySelector(".place").textContent,
    /At Example Residence/,
  );
  assert.equal(member.querySelector(".battery").textContent, "Battery 44%");
  assert.match(
    member.querySelector(".report-part.observed").textContent,
    /HA state updated/,
  );
  assert.equal(
    member.querySelector(".report-part.unknown").textContent,
    "Location report time unknown",
  );
  value.remove();
});

test("unavailable member stays counted without a map point and recovers on refresh", async () => {
  const fictionalOrigin = 0;
  const availableId = "person.example_home";
  const recoveringId = "person.example_recovering";
  const point = {
    latitude: fictionalOrigin,
    longitude: fictionalOrigin,
    evidence: { reported_at: null, observed_at: null, freshness: "unknown" },
  };
  const member = (id, name, presence, location) => ({
    id,
    name,
    kind: "person",
    presence,
    place: null,
    focusable: Boolean(location),
    location,
    battery: null,
    charging: null,
    driving: { value: null, status: "unknown" },
  });
  let recovered = false;
  const snapshot = () => ({
    ...response(),
    members: [
      member(availableId, "Example Home", "home", point),
      member(
        recoveringId,
        "Example Recovering",
        recovered ? "away" : "unavailable",
        recovered ? { ...point, longitude: fictionalOrigin + 1 } : null,
      ),
    ],
    focus_ids: {
      overview: recovered ? [availableId, recoveringId] : [availableId],
      home: [availableId],
      away: recovered ? [recoveringId] : [],
      driving: [],
      unavailable: [],
    },
  });
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => snapshot(),
  });
  let points;
  value._updateMap = (selected) => {
    points = selected;
    value._points = selected;
    value._updateMapNote();
  };
  await tick();
  assert.equal(points.length, 1);
  assert.equal(
    value.shadowRoot.querySelector('[aria-label="Unavailable: 1"] .count')
      .textContent,
    "1",
  );
  assert.match(
    value.shadowRoot.querySelector(".member .badge.unavailable").textContent,
    /Unavailable/,
  );
  assert.match(value.shadowRoot.textContent, /No usable map position/);
  value.shadowRoot.querySelector('[aria-label="Unavailable: 1"]').click();
  assert.equal(points.length, 0);
  assert.match(value._mapNote.textContent, /No usable map position/);
  value.shadowRoot.querySelector(".overview").click();
  assert.equal(points.length, 1);
  recovered = true;
  await value._load();
  assert.equal(points.length, 2);
  assert.ok(value.shadowRoot.querySelector('[aria-label="Unavailable: 0"]'));
  assert.ok(value.shadowRoot.querySelector('[aria-label="Away: 1"]'));
  value.remove();
});

test("wall kiosk control hides and restores HA navigation for this browser", async () => {
  const events = [];
  const onKiosk = (event) => events.push(event.detail.enable);
  window.addEventListener("hass-kiosk-mode", onKiosk);
  const originalFrame = globalThis.requestAnimationFrame;
  globalThis.requestAnimationFrame = (callback) => callback();
  try {
    const value = document.createElement("homecircle-card");
    value._updateMap = () => {};
    value.setConfig({ type: "custom:homecircle-card", fill_screen: true });
    value.hass = {
      connection: {},
      connected: true,
      callWS: async () => response(),
    };
    document.body.append(value);
    await tick();
    const toggle = value.shadowRoot.querySelector(".kiosk-toggle");
    assert.equal(toggle.textContent, "Kiosk view");
    toggle.click();
    assert.equal(
      new URL(window.location.href).searchParams.get("homecircle_kiosk"),
      "1",
    );
    assert.equal(toggle.textContent, "Exit kiosk");
    assert.equal(toggle.getAttribute("aria-pressed"), "true");
    toggle.click();
    assert.equal(
      new URL(window.location.href).searchParams.has("homecircle_kiosk"),
      false,
    );
    assert.equal(toggle.textContent, "Kiosk view");
    toggle.click();
    value.remove();
    assert.deepEqual(events, [true, false, true, false]);
  } finally {
    window.history.replaceState({}, "", "http://localhost/");
    window.removeEventListener("hass-kiosk-mode", onKiosk);
    globalThis.requestAnimationFrame = originalFrame;
  }
});

test("overlapping-marker choice retains keyboard focus after a marker redraw", async () => {
  const data = response();
  const fictionalOrigin = 0;
  data.members = ["person.example_one", "person.example_two"].map((id) => ({
    id,
    name: id,
    kind: "person",
    presence: "home",
    focusable: true,
    location: {
      latitude: fictionalOrigin,
      longitude: fictionalOrigin,
      evidence: {},
    },
    battery: null,
    charging: null,
    driving: { value: null, status: "unknown" },
  }));
  data.members[0].picture = "/api/image/serve/example/512x512";
  data.members[1].picture =
    "https://life360-images-pub.life360.com/example/pet.jpeg";
  data.focus_ids.overview = data.members.map((member) => member.id);
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  const memberPicture = value.shadowRoot.querySelectorAll(
    ".member .avatar img",
  )[1];
  assert.equal(memberPicture?.getAttribute("src"), data.members[1].picture);
  assert.equal(memberPicture?.referrerPolicy, "no-referrer");
  let separated = false;
  const markerIcons = [];
  value._map = {
    latLngToContainerPoint: ([, longitude]) => ({
      x: separated && longitude > fictionalOrigin ? 100 : 0,
      y: 0,
    }),
    remove() {},
  };
  value._layer = {
    clearLayers() {
      value._mapNode.replaceChildren();
    },
    addLayer(marker) {
      markerIcons.push(marker.options.icon.options);
      value._mapNode.append(marker.options.icon.options.html);
    },
  };
  value._points = data.members;
  value._markers();
  const cluster = value._mapNode.querySelector('[data-focus^="cluster:"]');
  assert.ok(cluster);
  assert.deepEqual(markerIcons.at(-1).iconSize, [90, 108]);
  assert.deepEqual(markerIcons.at(-1).iconAnchor, [45, 108]);
  assert.equal(cluster.querySelectorAll(".marker-avatar").length, 2);
  assert.equal(
    cluster.querySelector("img")?.getAttribute("src"),
    data.members[0].picture,
  );
  assert.equal(cluster.querySelectorAll("img").length, 2);
  memberPicture.dispatchEvent(new window.Event("error"));
  assert.equal(
    value.shadowRoot.querySelectorAll(".member .avatar img").length,
    1,
  );
  assert.match(
    cluster.getAttribute("aria-label"),
    /example_one, person.example_two/,
  );
  assert.doesNotMatch(cluster.textContent, /^2$/);
  cluster.focus();
  value._markers();
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    cluster.dataset.focus,
  );
  data.members[1].location.longitude = fictionalOrigin + 1;
  separated = true;
  value._markers();
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    "marker:person.example_one",
  );
  assert.deepEqual(markerIcons.at(-1).iconSize, [54, 68]);
  assert.deepEqual(markerIcons.at(-1).iconAnchor, [27, 68]);
  separated = false;
  value._markers();
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    cluster.dataset.focus,
  );
  value._mapNode.querySelector('[data-focus^="cluster:"]').click();
  assert.equal(
    value._mapNode
      .querySelector('[data-focus^="cluster:"]')
      .getAttribute("aria-expanded"),
    "true",
  );
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    "group:person.example_one",
  );
  value._markers();
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    "group:person.example_one",
  );
  value.remove();
});

test("choosing a single map member focuses its card", async () => {
  const data = response();
  data.members = [
    {
      id: "person.example_one",
      name: "Example One",
      kind: "person",
      presence: "home",
      focusable: true,
      location: { latitude: null, longitude: null, evidence: {} },
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
  value._chooseFromMap("person.example_one");
  assert.equal(
    value.shadowRoot.activeElement.dataset.focus,
    "person.example_one",
  );
  value.remove();
});
