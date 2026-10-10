import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import { observedFrames, forecastFrames } from "../src/weather-frames.js";
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
test("home title is simple, custom titles survive and the version remains available", async () => {
  const manifest = JSON.parse(
    readFileSync(
      new URL(
        "../../../custom_components/homecircle/manifest.json",
        import.meta.url,
      ),
    ),
  );
  const expected = "HomeCircle";
  const value = card({ connection: {}, callWS: async () => response() });
  await tick();
  assert.equal(value._integrationVersion, manifest.version);
  assert.equal(value.shadowRoot.querySelector("h2").textContent, expected);
  value.setConfig({
    type: "custom:homecircle-card",
    title: "HomeCircle - Beta 1",
  });
  assert.equal(value.shadowRoot.querySelector("h2").textContent, expected);
  value.setConfig({ type: "custom:homecircle-card", title: "Family Map" });
  assert.equal(value.shadowRoot.querySelector("h2").textContent, "Family Map");
  value.remove();
});
test("selecting a map-hidden member focuses it and Everyone omits it", async () => {
  const fictionalOrigin = 0;
  const data = response();
  const member = (id, mapVisible) => ({
    id,
    name: id,
    kind: "person",
    presence: "home",
    primary_home: true,
    place: null,
    focusable: true,
    map_visible: mapVisible,
    location: {
      latitude: fictionalOrigin,
      longitude: fictionalOrigin,
      evidence: {},
    },
    battery: null,
    charging: null,
    driving: { value: null, status: "unknown" },
  });
  data.members = [
    member("person.example_visible", true),
    member("person.example_hidden", false),
  ];
  data.focus_ids.overview = data.members.map((item) => item.id);
  data.focus_ids.home = data.focus_ids.overview;
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  let selected;
  value._updateMap = (points) => {
    selected = points.map((item) => item.id);
  };
  await tick();
  assert.deepEqual(selected, ["person.example_visible"]);
  value.shadowRoot
    .querySelector('[data-focus="person.example_hidden"]')
    .click();
  assert.deepEqual(selected, ["person.example_hidden"]);
  assert.match(
    value.shadowRoot.querySelector(".status").textContent,
    /1 map position/,
  );
  value.shadowRoot.querySelector(".overview").click();
  assert.deepEqual(selected, ["person.example_visible"]);
  value.remove();
});
test("holding a member opens details without focusing the map", async () => {
  const exampleLatitude = 1.25;
  const exampleLongitude = -2.5;
  const exampleHome = 0;
  const prototype = dom.window.HTMLDialogElement.prototype;
  const originalShowModal = prototype.showModal;
  const originalClose = prototype.close;
  prototype.showModal = function () {
    this.open = true;
  };
  prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new window.Event("close"));
  };
  try {
    const data = response();
    data.members = [
      {
        id: "person.example_member",
        name: "Example Member",
        kind: "person",
        presence: "away",
        place: null,
        focusable: false,
        map_visible: true,
        location: null,
        battery: 52,
        charging: false,
        driving: { value: null, status: "unknown" },
        speed: { value: null, unit: null },
        location_request: {
          enabled: true,
          requested_at: "2026-01-01T01:00:00Z",
          status: "no_response",
        },
        issues: ["tracker_presence_conflict"],
        diagnostics: {
          person_entity: "person.example_member",
          person_state: "home",
          person_updated_at: "2026-01-01T01:00:00Z",
          person_position: {
            latitude: exampleHome,
            longitude: exampleHome,
            accuracy: null,
          },
          active_source: "other",
          selected_trackers: [
            {
              entity_id: "device_tracker.example_phone",
              label: "Tracker: Example Phone",
              state: "not_home",
              updated_at: "2026-01-01T01:00:00Z",
              position: {
                latitude: exampleLatitude,
                longitude: exampleLongitude,
                accuracy: 15,
              },
              active: false,
            },
          ],
        },
      },
    ];
    data.focus_ids.overview = ["person.example_member"];
    const value = card({
      connection: {},
      connected: true,
      user: { is_admin: false },
      callWS: async () => structuredClone(data),
    });
    await tick();
    const member = value.shadowRoot.querySelector(".member");
    member.dispatchEvent(
      new window.MouseEvent("pointerdown", {
        bubbles: true,
        button: 0,
        clientX: 10,
        clientY: 10,
      }),
    );
    member.dispatchEvent(
      new window.MouseEvent("pointermove", {
        bubbles: true,
        clientX: 30,
        clientY: 10,
      }),
    );
    await new Promise((resolve) => setTimeout(resolve, 625));
    assert.equal(
      document.querySelector("dialog.homecircle-member-details"),
      null,
    );
    member.dispatchEvent(
      new window.MouseEvent("pointerdown", {
        bubbles: true,
        button: 0,
        clientX: 10,
        clientY: 10,
      }),
    );
    await new Promise((resolve) => setTimeout(resolve, 625));
    member.dispatchEvent(new window.MouseEvent("pointerup", { bubbles: true }));
    member.click();
    assert.equal(value._mode, "overview");
    let dialog = document.querySelector("dialog.homecircle-member-details");
    assert.ok(dialog?.open);
    assert.match(dialog.textContent, /1\.250000, -2\.500000/);
    assert.match(dialog.textContent, /No usable map position/);
    assert.match(dialog.textContent, /Last request attempted/);
    assert.match(dialog.textContent, /No later tracker report received/);
    assert.match(dialog.textContent, /selected GPS tracker disagree/);
    const refresh = [...dialog.querySelectorAll("button")].find(
      (control) => control.textContent === "Refresh details",
    );
    refresh.click();
    assert.match(dialog.textContent, /Checking Home Assistant/);
    await tick();
    assert.match(dialog.textContent, /No tracker time available/);
    data.members[0].location = {
      latitude: exampleLatitude,
      longitude: exampleLongitude,
      evidence: { reported_at: "2026-01-01T02:00:00Z" },
    };
    refresh.click();
    await tick();
    assert.match(dialog.textContent, /Report time changed/);
    let moreInfo;
    value.addEventListener("hass-more-info", (event) => {
      moreInfo = event.detail;
    });
    [...dialog.querySelectorAll("button")]
      .find((control) => control.textContent === "View HA history")
      .click();
    assert.deepEqual(moreInfo, {
      entityId: "device_tracker.example_phone",
      view: "history",
    });
    assert.equal(
      document.querySelector("dialog.homecircle-member-details"),
      null,
    );
    assert.equal(dialog.textContent.includes("Manage member settings"), false);
    member.click();
    assert.equal(value._mode, "person.example_member");
    value.shadowRoot.querySelector(".member-details-button").click();
    dialog = document.querySelector("dialog.homecircle-member-details");
    assert.ok(dialog?.open);
    value.remove();
    assert.equal(
      document.querySelector("dialog.homecircle-member-details"),
      null,
    );
  } finally {
    prototype.showModal = originalShowModal;
    prototype.close = originalClose;
  }
});
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
test("card shows and clears a provider repair message", async () => {
  let state = "auth_required";
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => ({
      ...response(),
      provider_alerts:
        state === "connected" ? [] : [{ name: "Life360", state }],
    }),
  });
  await tick();
  assert.match(
    value.shadowRoot.textContent,
    /Life360: sign-in needs attention/,
  );
  state = "connected";
  await value._load();
  assert.doesNotMatch(value.shadowRoot.textContent, /sign-in needs attention/);
  value.remove();
});
test("card prompts to finish member selection and clears the prompt", async () => {
  let needsSelection = true;
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => ({
      ...response(),
      provider_alerts: needsSelection
        ? [{ name: "Life360", state: "selection_needed" }]
        : [],
    }),
  });
  await tick();
  assert.match(
    value.shadowRoot.textContent,
    /choose a tracker from this account/,
  );
  needsSelection = false;
  await value._load();
  assert.doesNotMatch(
    value.shadowRoot.textContent,
    /choose a tracker from this account/,
  );
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
  assert.equal(value.shadowRoot.querySelector(".member.attention"), null);
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
          source_label: "Tracker: Example Phone",
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
  assert.equal(
    member.querySelector(".report-part.source").textContent,
    "Tracker: Example Phone",
  );
  assert.match(
    member.querySelector(".report-part.observed").textContent,
    /HA tracker updated/,
  );
  assert.equal(member.querySelector(".report-part.unknown"), null);
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
  assert.match(value._mapNote.textContent, /No map position shown/);
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
  const ha = document.createElement("home-assistant");
  let shell = ha;
  for (const tag of ["home-assistant-main", "ha-panel-lovelace", "hui-root"]) {
    const child = document.createElement(tag);
    shell.attachShadow({ mode: "open" }).append(child);
    shell = child;
  }
  const viewRoot = shell.attachShadow({ mode: "open" });
  document.body.append(ha);
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
      user: { is_admin: true },
      callWS: async () => response(),
    };
    document.body.append(value);
    await tick();
    const toggle = value.shadowRoot.querySelector(".kiosk-toggle");
    const settings = value.shadowRoot.querySelector(".settings-toggle");
    assert.equal(settings.hidden, false);
    assert.equal(toggle.textContent, "");
    assert.equal(toggle.getAttribute("aria-label"), "Enter kiosk view");
    assert.equal(toggle.title, "Enter kiosk view");
    assert.equal(
      toggle.querySelector("ha-icon").getAttribute("icon"),
      "mdi:fullscreen",
    );
    toggle.click();
    assert.equal(
      new URL(window.location.href).searchParams.get("homecircle_kiosk"),
      "1",
    );
    assert.equal(toggle.textContent, "");
    assert.equal(toggle.getAttribute("aria-label"), "Exit kiosk view");
    assert.equal(toggle.title, "Exit kiosk view");
    assert.equal(
      toggle.querySelector("ha-icon").getAttribute("icon"),
      "mdi:fullscreen-exit",
    );
    assert.equal(toggle.getAttribute("aria-pressed"), "true");
    assert.equal(value.hasAttribute("kiosk"), true);
    assert.match(
      value.shadowRoot.querySelector("style").textContent,
      /:host\(\[kiosk\]\) \.settings-toggle/,
    );
    assert.match(viewRoot.querySelector("style").textContent, /padding-top: 0/);
    toggle.click();
    assert.equal(
      new URL(window.location.href).searchParams.has("homecircle_kiosk"),
      false,
    );
    assert.equal(toggle.getAttribute("aria-label"), "Enter kiosk view");
    assert.equal(
      toggle.querySelector("ha-icon").getAttribute("icon"),
      "mdi:fullscreen",
    );
    assert.equal(value.hasAttribute("kiosk"), false);
    assert.equal(viewRoot.querySelector("style"), null);
    toggle.click();
    value.remove();
    assert.equal(viewRoot.querySelector("style"), null);
    assert.deepEqual(events, [true, false, true, false]);
  } finally {
    window.history.replaceState({}, "", "http://localhost/");
    ha.remove();
    window.removeEventListener("hass-kiosk-mode", onKiosk);
    globalThis.requestAnimationFrame = originalFrame;
  }
});

test("settings cog opens task choices over the dashboard for administrators", async () => {
  const dialogPrototype = dom.window.HTMLDialogElement.prototype;
  const originalShowModal = dialogPrototype.showModal;
  const originalClose = dialogPrototype.close;
  dialogPrototype.showModal = function () {
    this.open = true;
  };
  dialogPrototype.close = function () {
    this.open = false;
    this.dispatchEvent(new window.Event("close"));
  };
  const value = card({
    connection: {},
    connected: true,
    user: { is_admin: false },
    callWS: async () => response(),
  });
  const flowCalls = [];
  const settings = value.shadowRoot.querySelector(".settings-toggle");
  assert.equal(settings.hidden, true);
  value.hass = {
    connection: value._hass.connection,
    connected: true,
    user: { is_admin: true },
    callWS: async (request) =>
      request.type === "config_entries/get"
        ? [{ entry_id: "sample-entry" }]
        : response(),
    callApi: async (method, path, data) => {
      flowCalls.push({ method, path, data });
      if (path.endsWith("/sample-flow") && data?.remove_tracker)
        return {
          type: "menu",
          flow_id: "sample-flow",
          step_id: "confirm_remove",
          menu_options: ["confirm_back_remove", "confirm_save"],
          description_placeholders: { members: "Sample tracker removed" },
        };
      if (path.endsWith("/sample-flow") && data?.setting === "remove")
        return {
          type: "form",
          flow_id: "sample-flow",
          step_id: "remove_tracker_choice",
          handler: "sample-entry",
          data_schema: [
            {
              name: "remove_tracker",
              required: true,
              selector: {
                select: { options: [{ value: "tracker", label: "Tracker" }] },
              },
            },
          ],
          errors: {},
        };
      if (path.endsWith("/sample-flow") && data?.setting === "details")
        return {
          type: "form",
          flow_id: "sample-flow",
          step_id: "member",
          handler: "sample-entry",
          data_schema: [],
          description_placeholders: {
            position_guidance:
              "Review linked devices in [Home Assistant People settings](/config/person).",
          },
          errors: {},
        };
      return path.endsWith("/sample-flow")
        ? {
            type: "form",
            flow_id: "sample-flow",
            step_id: "tracker_member_choice",
            handler: "sample-entry",
            data_schema: [
              {
                name: "member",
                required: true,
                selector: {
                  select: {
                    options: [
                      { value: "sample", label: "Sample" },
                      { value: "empty", label: "No tracker" },
                    ],
                  },
                },
              },
              {
                name: "setting",
                required: true,
                selector: {
                  select: {
                    options: [
                      {
                        value: "details",
                        label: "Details, homes, and map visibility",
                      },
                      { value: "sensors", label: "Battery and status sensors" },
                      { value: "remove", label: "Remove a tracker" },
                    ],
                  },
                },
              },
            ],
            description_placeholders: { removable_members: "sample" },
            errors: {},
          }
        : {
            type: "menu",
            flow_id: "sample-flow",
            step_id: "init",
            menu_options: ["tracker_member_choice", "household"],
          };
    },
    loadBackendTranslation: async () => {},
    localize: (key, placeholders) => {
      if (key.endsWith("step.confirm_remove.description"))
        return `Review ${placeholders.members} before saving.`;
      if (key.endsWith("step.confirm_remove.title"))
        return "Review tracker removal";
      if (key.endsWith("step.member.description"))
        return placeholders.position_guidance;
      if (key.endsWith("tracker_member_choice"))
        return "Person and tracker settings";
      if (key.endsWith("household")) return "Manage the whole household";
      return "";
    },
  };
  assert.equal(settings.hidden, false);
  try {
    const path = window.location.pathname;
    settings.click();
    await tick();
    assert.equal(window.location.pathname, path);
    assert.equal(settings.getAttribute("aria-label"), "HomeCircle settings");
    assert.equal(
      settings.querySelector("ha-icon")?.getAttribute("icon"),
      "mdi:cog",
    );
    const dialog = document.querySelector("dialog.homecircle-settings");
    assert.ok(dialog?.open);
    assert.equal(
      dialog.querySelector(".version").textContent,
      `Version ${value._integrationVersion}`,
    );
    assert.match(dialog.textContent, /Person and tracker settings/);
    const radarControls = dialog.querySelector('input[type="checkbox"]');
    assert.equal(radarControls.checked, false);
    const flowCount = flowCalls.length;
    radarControls.checked = true;
    radarControls.dispatchEvent(new window.Event("change"));
    assert.equal(value._radarController.showControls, true);
    assert.equal(flowCalls.length, flowCount);
    radarControls.checked = false;
    radarControls.dispatchEvent(new window.Event("change"));
    assert.equal(value._radarController.showControls, false);
    dialog.querySelector(".choice").click();
    await tick();
    assert.match(dialog.textContent, /HomeCircle settings/);
    assert.equal(dialog.querySelector("ha-form")?.schema?.[0]?.name, "member");
    assert.equal(dialog.querySelector("ha-form")?.data?.member, undefined);
    const choices = dialog.querySelector(".body > div[hidden]");
    assert.ok(choices);
    assert.match(choices.textContent, /Battery and status sensors/);
    dialog.querySelector("ha-form").dispatchEvent(
      new window.CustomEvent("value-changed", {
        detail: { value: { member: "sample" } },
      }),
    );
    assert.equal(choices.hidden, false);
    assert.equal(choices.querySelectorAll("button")[2].hidden, false);
    dialog.querySelector("ha-form").dispatchEvent(
      new window.CustomEvent("value-changed", {
        detail: { value: { member: "empty" } },
      }),
    );
    assert.equal(choices.querySelectorAll("button")[2].hidden, true);
    dialog.querySelector("ha-form").dispatchEvent(
      new window.CustomEvent("value-changed", {
        detail: { value: { member: "sample" } },
      }),
    );
    choices.querySelectorAll("button")[0].click();
    await tick();
    const peopleLink = dialog.querySelector('a[href="/config/person"]');
    assert.equal(peopleLink?.textContent, "Home Assistant People settings");
    dialog.querySelector(".actions button").click();
    await tick();
    choices.querySelectorAll("button")[1].click();
    await tick();
    assert.deepEqual(flowCalls.at(-1), {
      method: "POST",
      path: "config/config_entries/options/flow/sample-flow",
      data: { member: "sample", setting: "sensors" },
    });
    assert.ok(
      flowCalls.some(
        (call) =>
          call.data?.next_step_id === "tracker_member_choice" &&
          call.method === "POST",
      ),
    );
    dialog.querySelectorAll(".body .choice")[2].click();
    await tick();
    assert.equal(
      dialog.querySelector("ha-form")?.schema?.[0]?.name,
      "remove_tracker",
    );
    dialog.querySelector(".actions button").click();
    await tick();
    assert.equal(dialog.querySelector("ha-form")?.data?.member, "sample");
    assert.match(dialog.textContent, /Remove a tracker/);
    assert.equal(
      flowCalls.findLast((call) => call.method === "POST").data.next_step_id,
      "tracker_member_choice",
    );
    dialog.querySelectorAll(".body .choice")[2].click();
    await tick();
    dialog.querySelectorAll(".actions button")[1].click();
    await tick();
    assert.match(
      dialog.textContent,
      /Review Sample tracker removed before saving/,
    );
    dialog.close();
    const memberData = response();
    memberData.members = [
      {
        id: "sample",
        name: "Sample",
        kind: "person",
        presence: "home",
        focusable: false,
        location: null,
        battery: null,
        charging: null,
        driving: { value: null, status: "unknown" },
        issues: [],
      },
    ];
    value._hass.callWS = async (request) =>
      request.type === "config_entries/get"
        ? [{ entry_id: "sample-entry" }]
        : memberData;
    await value._load();
    value.shadowRoot.querySelector(".member-details-button").click();
    const memberDialog = document.querySelector(
      "dialog.homecircle-member-details",
    );
    assert.ok(memberDialog?.open);
    [...memberDialog.querySelectorAll("button")]
      .find((control) => control.textContent === "Manage member settings")
      .click();
    await tick();
    assert.equal(window.location.pathname, path);
    assert.equal(
      document.querySelector("dialog.homecircle-member-details"),
      null,
    );
    const scoped = document.querySelector("dialog.homecircle-settings");
    assert.equal(scoped.querySelector("ha-form")?.data?.member, "sample");
    scoped.querySelector(".actions button").click();
    await tick();
    assert.equal(document.querySelector("dialog.homecircle-settings"), null);
    const returned = document.querySelector("dialog.homecircle-member-details");
    assert.ok(returned?.open);
    assert.equal(returned.getAttribute("aria-label"), "Sample details");
    returned.close();
  } finally {
    dialogPrototype.showModal = originalShowModal;
    dialogPrototype.close = originalClose;
    value.remove();
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

function homeMember(id, overrides = {}) {
  const exampleCoordinate = 0;
  return {
    id: `person.example_${id}`,
    name: id,
    kind: "person",
    presence: "home",
    place: "Home",
    focusable: true,
    map_visible: true,
    primary_home: true,
    location: {
      latitude: exampleCoordinate,
      longitude: exampleCoordinate,
      evidence: { freshness: "fresh" },
    },
    battery: 65,
    charging: false,
    driving: { value: false, status: "current" },
    issues: [],
    ...overrides,
  };
}

test("map totals explain hidden and missing positions without including omitted members", async () => {
  const data = response();
  data.members = [
    homeMember("visible"),
    homeMember("hidden", { map_visible: false }),
    homeMember("missing", { location: null, focusable: false }),
    homeMember("omitted"),
  ];
  data.focus_ids.overview = data.members.map((member) => member.id);
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  value.setConfig({
    type: "custom:homecircle-card",
    hidden_members: ["person.example_omitted"],
  });
  await tick();
  const status = value.shadowRoot.querySelector(".status").textContent;
  assert.match(status, /1 of 3 members shown on map/);
  assert.match(status, /Hidden from Everyone: hidden/);
  assert.match(status, /No usable map position: missing/);
  assert.equal(status.includes("omitted"), false);
  value.remove();
});

test("low battery emphasizes bounded readings and charging clears the warning", async () => {
  let battery = 5;
  let charging = false;
  const data = response();
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => ({
      ...data,
      members: [homeMember("battery", { battery, charging })],
    }),
  });
  await tick();
  assert.match(
    value.shadowRoot.querySelector(".battery.critical").textContent,
    /Low battery 5%/,
  );
  battery = 20;
  await value._load();
  assert.ok(value.shadowRoot.querySelector(".battery.low"));
  assert.equal(value.shadowRoot.querySelector(".battery.critical"), null);
  battery = 21;
  await value._load();
  assert.equal(value.shadowRoot.querySelector(".battery.low"), null);
  battery = 0;
  await value._load();
  assert.match(
    value.shadowRoot.querySelector(".battery.critical").textContent,
    /Low battery 0%/,
  );
  charging = true;
  await value._load();
  assert.equal(value.shadowRoot.querySelector(".battery.low"), null);
  assert.match(
    value.shadowRoot.querySelector(".battery").textContent,
    /charging/,
  );
  for (const invalid of [null, undefined, NaN, -1, 101]) {
    battery = invalid;
    await value._load();
    assert.equal(value.shadowRoot.querySelector(".battery"), null);
  }
  value.remove();
});

test("cards remove generic Home repetition but retain additional residence names", async () => {
  const data = response();
  data.members = [
    homeMember("primary"),
    homeMember("secondary", {
      place: "Example Residence",
      primary_home: false,
    }),
  ];
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  const cards = value.shadowRoot.querySelectorAll(".member");
  assert.equal(cards[0].querySelector(".place"), null);
  assert.equal(cards[0].querySelector(".badge").textContent, "Home");
  assert.equal(
    cards[1].querySelector(".place").textContent,
    "At Example Residence",
  );
  value.remove();
});

test("conflict and unavailable positions retain stronger attention styling", async () => {
  const data = response();
  data.members = [
    homeMember("conflict", { issues: ["tracker_presence_conflict"] }),
    homeMember("missing", {
      location: null,
      focusable: false,
      presence: "unavailable",
    }),
    homeMember("ordinary"),
  ];
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  assert.equal(
    value.shadowRoot.querySelectorAll(".member.attention").length,
    2,
  );
  data.members[0].issues = [];
  data.members[1] = homeMember("missing");
  await value._load();
  assert.equal(value.shadowRoot.querySelector(".member.attention"), null);
  value.remove();
});

test("satellite swaps only tiles, preserves map view and remembers this browser choice", () => {
  window.localStorage.clear();
  globalThis.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  value._updateMap([]);
  const map = value._map;
  const markerLayer = value._layer;
  const center = map.getCenter();
  const zoom = map.getZoom();
  const street = value._tiles;
  value._mode = "person.example_member";
  value._satelliteButton.click();
  const satellite = value._tiles;
  assert.equal(value._map, map);
  assert.equal(value._layer, markerLayer);
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), zoom);
  assert.equal(value._mode, "person.example_member");
  assert.equal(map.hasLayer(street), false);
  assert.equal(map.hasLayer(satellite), true);
  assert.match(satellite._url, /USGSImageryOnly.*\{z\}\/\{y\}\/\{x\}/);
  assert.match(satellite.options.attribution, /USDA, USGS/);
  assert.doesNotMatch(
    value._mapNode.querySelector(".leaflet-control-attribution").textContent,
    /OpenStreetMap/,
  );
  assert.equal(satellite.options.maxNativeZoom, 16);
  assert.equal(value._satelliteButton.getAttribute("aria-pressed"), "true");
  assert.equal(value._streetButton.getAttribute("aria-pressed"), "false");
  satellite.fire("tileerror");
  assert.equal(value._tileUnavailable, true);
  value._streetButton.click();
  assert.equal(value._tileUnavailable, false);
  satellite.fire("tileerror");
  assert.equal(value._tileUnavailable, false);
  assert.equal(map.hasLayer(satellite), false);
  assert.match(value._tiles._url, /tile.openstreetmap.org/);
  value._satelliteButton.click();
  value.remove();
  const restored = document.createElement("homecircle-card");
  restored.setConfig({ type: "custom:homecircle-card" });
  assert.equal(restored._mapBackground, "satellite");
  window.localStorage.clear();
});

test("private background ignores a remembered satellite choice and cannot enable external tiles", () => {
  window.localStorage.clear();
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  window.localStorage.setItem(value._mapPreferenceKey(), "satellite");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  value._updateMap([]);
  assert.equal(value._mapControls.hidden, true);
  assert.equal(value._mapBackground, "none");
  value._satelliteButton.click();
  assert.equal(value._mapBackground, "none");
  assert.equal(value._tiles, null);
  assert.equal(value._mapNode.querySelector("img.leaflet-tile"), null);
  value.remove();
  window.localStorage.clear();
});

test("satellite default and controls work when browser storage is blocked", () => {
  const storage = window.Storage.prototype;
  const get = storage.getItem,
    set = storage.setItem;
  storage.getItem = storage.setItem = () => {
    throw new Error("Storage blocked");
  };
  try {
    const value = document.createElement("homecircle-card");
    value.setConfig({ type: "custom:homecircle-card", map_tiles: "satellite" });
    document.body.append(value);
    assert.equal(value._satelliteButton.getAttribute("aria-pressed"), "true");
    value._streetButton.click();
    assert.equal(value._streetButton.getAttribute("aria-pressed"), "true");
    value.remove();
  } finally {
    storage.getItem = get;
    storage.setItem = set;
  }
});

test("zoom buttons center rendered pins after panning and retain member selection and layers", () => {
  window.localStorage.clear();
  const fictionalOrigin = 0;
  const fictionalOffset = 1;
  const member = (id, longitude) => ({
    id,
    name: "Example Member",
    picture: null,
    location: { latitude: fictionalOrigin, longitude },
  });
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const one = member("person.example_member", fictionalOrigin);
  value._updateMap([one]);
  value._mode = one.id;
  const map = value._map,
    layer = value._layer,
    tiles = value._tiles;
  const centered = () => {
    const boxes = layer.getLayers().map((pin) => {
      const point = map.latLngToContainerPoint(pin.getLatLng());
      const [width, height] = pin.options.icon.options.iconSize;
      return {
        left: point.x - width / 2,
        right: point.x + width / 2,
        top: point.y - height,
        bottom: point.y,
      };
    });
    const x =
      (Math.min(...boxes.map((box) => box.left)) +
        Math.max(...boxes.map((box) => box.right))) /
      2;
    const y =
      (Math.min(...boxes.map((box) => box.top)) +
        Math.max(...boxes.map((box) => box.bottom))) /
      2;
    assert.ok(Math.abs(x - map.getSize().x / 2) < 1);
    assert.ok(Math.abs(y - map.getSize().y / 2) < 1);
  };
  map.panBy([120, 80], { animate: false });
  let before = map.getZoom();
  value._zoomInButton.click();
  assert.equal(map.getZoom(), before + 1);
  centered();
  assert.equal(value._mode, one.id);
  assert.equal(value._map, map);
  assert.equal(value._layer, layer);
  assert.equal(value._tiles, tiles);
  map.panBy([-80, 60], { animate: false });
  value._zoomOutButton.click();
  assert.equal(map.getZoom(), before);
  centered();
  value._updateMap([one, member("person.example_second", fictionalOrigin)]);
  value._zoomInButton.click();
  assert.equal(layer.getLayers().length, 1);
  centered();
  value._updateMap([one, member("person.example_second", fictionalOffset)]);
  value._mode = "overview";
  value._recenterButton.click();
  value._zoomInButton.click();
  assert.equal(layer.getLayers().length, 2);
  centered();
  value.remove();
});

test("zoom buttons respect limits and keep the current center without map positions", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  value._updateMap([]);
  const map = value._map;
  const center = map.getCenter();
  value._zoomInButton.click();
  assert.deepEqual(map.getCenter(), center);
  map.setZoom(map.getMaxZoom(), { animate: false });
  assert.equal(value._zoomInButton.disabled, true);
  value._zoomInButton.click();
  assert.equal(map.getZoom(), map.getMaxZoom());
  map.setZoom(map.getMinZoom(), { animate: false });
  assert.equal(value._zoomOutButton.disabled, true);
  value._zoomOutButton.click();
  assert.equal(map.getZoom(), map.getMinZoom());
  assert.equal(value._tiles, null);
  value.remove();
});

test("zoom keeps the current view when household pins are outside the viewport", () => {
  const fictionalOrigin = 0;
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const member = {
    id: "person.example_member",
    name: "Example Member",
    location: { latitude: fictionalOrigin, longitude: fictionalOrigin },
  };
  value._updateMap([member]);
  const map = value._map;
  map.panBy([2000, 2000], { animate: false });
  const center = map.getCenter(),
    zoom = map.getZoom();
  value._zoomInButton.click();
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), zoom + 1);
  value._zoomOutButton.click();
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), zoom);
  assert.equal(value._mode, "overview");
  value._mode = member.id;
  value._zoomInButton.click();
  assert.deepEqual(map.getCenter(), center);
  assert.equal(value._mode, member.id);
  value.remove();
});

function staleSelectionData() {
  const origin = 0;
  const data = response();
  data.members = [
    {
      id: "person.example_member",
      name: "Example Member",
      kind: "person",
      presence: "home",
      primary_home: true,
      focusable: true,
      map_visible: true,
      battery: null,
      charging: null,
      driving: { value: null, status: "unknown" },
      location: {
        latitude: origin,
        longitude: origin,
        evidence: {
          freshness: "stale",
          reported_at: "2026-01-01T00:00:00Z",
          source_label: "Tracker: Example Phone",
        },
      },
    },
  ];
  data.focus_ids.overview = data.focus_ids.home = [data.members[0].id];
  return data;
}

test("selecting a stale member checks only that member and leaves the stale label until newer evidence", async () => {
  const data = staleSelectionData(),
    calls = [];
  const value = card({
    connection: {},
    connected: true,
    callWS: async (request) => {
      calls.push(request);
      return request.type === "homecircle/refresh_location"
        ? { status: "checked" }
        : data;
    },
  });
  await tick();
  value._choose("home");
  value._choose("overview");
  assert.equal(
    calls.filter((item) => item.type === "homecircle/refresh_location").length,
    0,
  );
  value._choose(data.members[0].id);
  await tick();
  assert.deepEqual(
    calls.find((item) => item.type === "homecircle/refresh_location"),
    { type: "homecircle/refresh_location", member_id: data.members[0].id },
  );
  assert.match(value._locationFeedback.textContent, /No newer location report/);
  assert.match(
    value.shadowRoot.querySelector(".member").textContent,
    /Stale report/,
  );
  data.members[0].location.evidence.reported_at = "2026-01-01T01:00:00Z";
  data.members[0].location.evidence.freshness = "fresh";
  await value._load();
  assert.equal(
    value._locationFeedback.textContent,
    "Newer location report received.",
  );
  assert.doesNotMatch(
    value.shadowRoot.querySelector(".member").textContent,
    /Stale report/,
  );
  const count = calls.length;
  value._choose(data.members[0].id);
  await tick();
  assert.equal(calls.length, count);
  value.remove();
});

test("a phone request waits for evidence and a source switch never claims a confirmed newer report", async () => {
  const data = staleSelectionData();
  const value = card({
    connection: {},
    connected: true,
    callWS: async (request) =>
      request.type === "homecircle/refresh_location"
        ? { status: "requested" }
        : data,
  });
  await tick();
  value._choose(data.members[0].id);
  await tick();
  assert.match(
    value._locationFeedback.textContent,
    /Waiting for a newer report/,
  );
  value._selectionRefresh.started -= 61000;
  value._updateLocationFeedback();
  assert.equal(
    value._locationFeedback.textContent,
    "No newer location report received yet.",
  );
  data.members[0].location.evidence.reported_at = "2026-01-01T01:00:00Z";
  data.members[0].location.evidence.source_label = "Tracker: Example Other";
  await value._load();
  assert.doesNotMatch(
    value._locationFeedback.textContent,
    /Newer location report received/,
  );
  value.remove();
});

test("late selection checks cannot restore feedback after overview or disconnection", async () => {
  const data = staleSelectionData();
  let resolve,
    checks = 0;
  const value = card({
    connection: {},
    connected: true,
    callWS: async (request) => {
      if (request.type !== "homecircle/refresh_location") return data;
      checks++;
      return new Promise((done) => {
        resolve = done;
      });
    },
  });
  await tick();
  value._choose(data.members[0].id);
  value._choose(data.members[0].id);
  assert.equal(checks, 1);
  value._choose("overview");
  resolve({ status: "checked" });
  await tick();
  assert.equal(value._locationFeedback.textContent, "");
  value._choose(data.members[0].id);
  value.remove();
  resolve({ status: "checked" });
  await tick();
  assert.equal(value.shadowRoot.childElementCount, 0);
});

test("unsupported or failed selection checks show fixed feedback without provider errors", async () => {
  const data = staleSelectionData();
  const value = card({
    connection: {},
    connected: true,
    callWS: async (request) => {
      if (request.type === "homecircle/refresh_location")
        throw new Error("private failure");
      return data;
    },
  });
  await tick();
  value._choose(data.members[0].id);
  await tick();
  assert.equal(
    value._locationFeedback.textContent,
    "Location refresh is temporarily unavailable.",
  );
  assert.doesNotMatch(value.shadowRoot.textContent, /private failure/);
  value.remove();
});

test("person selection zooms three levels above the default and Everyone restores it", () => {
  const fictionalOrigin = 0;
  const fictionalOffset = 2;
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [
    homeMember("one"),
    homeMember("two", {
      location: {
        latitude: fictionalOrigin,
        longitude: fictionalOffset,
        evidence: { freshness: "fresh" },
      },
    }),
    homeMember("missing", { location: null, focusable: false }),
  ];
  data.focus_ids.overview = data.members.slice(0, 2).map((m) => m.id);
  value._data = data;
  value._render();
  const map = value._map;
  const defaultZoom = map.getZoom();
  const defaultCenter = map.getCenter();
  const select = (member) =>
    value.shadowRoot
      .querySelector(`.member[data-focus="${member.id}"]`)
      .click();
  for (const member of [data.members[0], data.members[1], data.members[1]]) {
    select(member);
    assert.equal(map.getZoom(), defaultZoom + 3);
    assert.equal(map.getCenter().lat, member.location.latitude);
    assert.equal(map.getCenter().lng, member.location.longitude);
    value._render();
    assert.equal(map.getZoom(), defaultZoom + 3);
  }
  map.setZoom(18, { animate: false });
  select(data.members[0]);
  assert.equal(map.getZoom(), defaultZoom + 3);
  select(data.members[2]);
  assert.equal(map.getZoom(), defaultZoom + 3);
  value._overview.click();
  assert.equal(map.getZoom(), defaultZoom);
  assert.deepEqual(map.getCenter(), defaultCenter);
  value.remove();
});

test("zero-count categories preserve the viewport, hide pins and restore Everyone", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [homeMember("one"), homeMember("two")];
  data.focus_ids.overview = data.members.map((member) => member.id);
  data.focus_ids.home = [...data.focus_ids.overview];
  value._data = data;
  value._render();
  const map = value._map;
  const overviewCenter = map.getCenter();
  map.panBy([160, 60], { animate: false });
  map.setZoom(12, { animate: false });
  const center = map.getCenter(),
    zoom = map.getZoom();
  for (const [category, message] of [
    ["away", "No one is away."],
    ["driving", "No one is currently reported as driving."],
    ["unavailable", "Everyone has available presence information."],
  ]) {
    value.shadowRoot
      .querySelector(`.category[data-focus="${category}"]`)
      .click();
    assert.equal(value._mode, category);
    assert.equal(
      value.shadowRoot
        .querySelector(`.category[data-focus="${category}"]`)
        .getAttribute("aria-pressed"),
      "true",
    );
    assert.deepEqual(map.getCenter(), center);
    assert.equal(map.getZoom(), zoom);
    assert.equal(value._layer.getLayers().length, 0);
    assert.equal(value._status.textContent, message);
    assert.match(value._mapNote.textContent, /Select Everyone/);
    value._render();
    assert.deepEqual(map.getCenter(), center);
    assert.equal(map.getZoom(), zoom);
  }
  value._overview.click();
  assert.equal(value._mode, "overview");
  assert.deepEqual(map.getCenter(), overviewCenter);
  assert.ok(value._layer.getLayers().length > 0);
  assert.match(value._status.textContent, /Everyone/);
  value.remove();
});

test("members without positions are not mistaken for an empty category, and new positions refit", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [
    homeMember("one"),
    homeMember("missing", {
      presence: "unavailable",
      focusable: false,
      location: null,
    }),
  ];
  data.focus_ids.overview = [data.members[0].id];
  value._data = data;
  value._render();
  const map = value._map;
  const center = map.getCenter(),
    zoom = map.getZoom();
  value._choose("unavailable");
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), zoom);
  assert.doesNotMatch(value._status.textContent, /Everyone has available/);
  assert.match(value._mapNote.textContent, /No map position shown/);
  value._choose("away");
  assert.equal(value._status.textContent, "No one is away.");
  data.members[0].presence = "away";
  data.focus_ids.away = [data.members[0].id];
  value._render();
  assert.match(value._status.textContent, /Away · 1 map position/);
  assert.ok(value._layer.getLayers().length > 0);
  value.remove();
});

test("person cards show reported addresses outside defined places and qualify old reports", async () => {
  const data = response();
  const member = homeMember("one", {
    presence: "away",
    place: null,
    reported_address: "Example street, Example city",
  });
  data.members = [member];
  data.focus_ids.overview = [member.id];
  const value = card({
    connection: {},
    connected: true,
    callWS: async () => data,
  });
  await tick();
  assert.equal(
    value.shadowRoot.querySelector(".address").textContent,
    "At Example street, Example city",
  );
  member.location.evidence.freshness = "stale";
  value._render();
  assert.equal(
    value.shadowRoot.querySelector(".address").textContent,
    "Last reported: Example street, Example city",
  );
  member.location.evidence.freshness = "unknown";
  value._render();
  assert.match(
    value.shadowRoot.querySelector(".address").textContent,
    /Last reported:/,
  );
  member.place = "Example place";
  value._render();
  assert.equal(value.shadowRoot.querySelector(".address"), null);
  assert.equal(
    value.shadowRoot.querySelector(".place").textContent,
    "At Example place",
  );
  member.place = "Home";
  member.presence = "home";
  value._render();
  assert.equal(value.shadowRoot.querySelector(".address"), null);
  assert.equal(value.shadowRoot.querySelector(".place"), null);
  member.place = null;
  member.presence = "driving";
  member.reported_address = null;
  value._render();
  assert.equal(
    value.shadowRoot.querySelector(".address").textContent,
    "Address unavailable",
  );
  member.reported_address = "<img src=x>";
  value._render();
  assert.equal(value.shadowRoot.querySelector(".address img"), null);
  member.focusable = false;
  value._render();
  assert.equal(value.shadowRoot.querySelector(".address"), null);
  value.remove();
});
test("map edge resizes, preserves selection, saves locally and cancels safely", async () => {
  window.localStorage.clear();
  const value = card({ connection: {}, callWS: async () => response() });
  await tick();
  const handle = value.shadowRoot.querySelector(".map-resize");
  value._mapNode.getBoundingClientRect = () => ({ height: 300 });
  const capture = new Set();
  handle.setPointerCapture = (id) => capture.add(id);
  handle.hasPointerCapture = (id) => capture.has(id);
  handle.releasePointerCapture = (id) => capture.delete(id);
  const fire = (type, y, id = 1) => {
    const event = new window.Event(type, { bubbles: true, cancelable: true });
    Object.assign(event, { pointerId: id, clientY: y, button: 0 });
    handle.dispatchEvent(event);
  };
  value._mode = "away";
  fire("pointerdown", 100);
  fire("pointermove", 200, 2);
  assert.equal(value._mapHeight, null);
  fire("pointermove", 180);
  assert.equal(value._mapHeight, 380);
  fire("pointerup", 180);
  assert.equal(value._mode, "away");
  assert.equal(handle.getAttribute("aria-valuenow"), "380");
  assert.equal(
    window.localStorage.getItem(value._heightPreferenceKey()),
    "380",
  );
  assert.equal(capture.size, 0);
  fire("pointerdown", 100);
  fire("pointermove", -1000);
  assert.equal(value._mapHeight, 220);
  fire("pointercancel", -1000);
  assert.equal(value._mapHeight, 380);
  handle.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "ArrowDown" }),
  );
  assert.equal(value._mapHeight, 400);
  value.remove();
  const restored = card({ connection: {}, callWS: async () => response() });
  await tick();
  assert.equal(restored._mapHeight, 400);
  const restoredHandle = restored.shadowRoot.querySelector(".map-resize");
  restoredHandle.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Home" }),
  );
  assert.equal(restored._mapHeight, null);
  assert.equal(restored._mapWrap.classList.contains("resized"), false);
  assert.equal(
    window.localStorage.getItem(restored._heightPreferenceKey()),
    null,
  );
  restored.remove();
  window.localStorage.clear();
});

test("resizing real Leaflet keeps center, zoom and layers without refitting", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({
    type: "custom:homecircle-card",
    map_tiles: "none",
    fill_screen: true,
  });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", {
    get: () => value._mapHeight ?? 300,
  });
  value._updateMap([]);
  const map = value._map;
  map.setView([0, 0], 10, { animate: false });
  const center = map.getCenter();
  const layer = value._layer;
  value._mode = "away";
  value._mapHeight = 500;
  value._applyMapHeight();
  assert.equal(map.getSize().y, 500);
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), 10);
  assert.equal(value._layer, layer);
  assert.equal(value._mode, "away");
  value._mapHeight = 10000;
  value._applyMapHeight();
  assert.equal(value._mapHeight, Math.max(220, window.innerHeight - 200));
  assert.deepEqual(map.getCenter(), center);
  value.remove();
  window.localStorage.clear();
});

test("family refresh makes one explicit request and reports same-source outcomes", async (t) => {
  let resolveRequest;
  let requests = 0;
  let state = { available: true, status: "idle", members: [] };
  const value = card({
    connection: {},
    callWS: async (message) => {
      if (message.type === "homecircle/refresh_family") {
        requests++;
        return new Promise((resolve) => {
          resolveRequest = resolve;
        });
      }
      return {
        ...response(),
        members: [
          {
            id: "person.example_member",
            name: "Example",
            presence: "home",
            location: null,
            focusable: false,
            kind: "person",
            driving: { value: null, status: "unknown" },
            trackers: [],
            battery: null,
          },
        ],
        family_refresh: state,
      };
    },
  });
  t.after(() => value.remove());
  await tick();
  const control = value.shadowRoot.querySelector(".family-refresh-button");
  assert.equal(control.closest(".family-refresh").hidden, false);
  control.click();
  control.click();
  assert.equal(requests, 1);
  assert.equal(control.disabled, true);
  state = {
    available: true,
    status: "requested",
    members: [{ id: "person.example_member", status: "waiting" }],
  };
  resolveRequest({ status: "requested" });
  await tick();
  await tick();
  assert.match(value._familyFeedback.textContent, /Example: Waiting/);
  state = {
    available: true,
    status: "complete",
    members: [{ id: "person.example_member", status: "unchanged" }],
  };
  await value._load();
  assert.match(value._familyFeedback.textContent, /Example: Unchanged/);
  assert.equal(control.disabled, false);
  assert.equal(requests, 1);
  value.remove();
});

test("failed family request feedback expires without unlocking a current limit", async (t) => {
  const retry = new Date(Date.now() + 24 * 60 * 60_000).toISOString();
  const value = card({
    connection: {},
    callWS: async (message) =>
      message.type === "homecircle/refresh_family"
        ? { status: "send_failed" }
        : {
            ...response(),
            family_refresh: {
              available: true,
              status: "idle",
              members: [],
              next_available_at: retry,
            },
          },
  });
  t.after(() => value.remove());
  await tick();
  await value._refreshFamily();
  assert.match(value._familyFeedback.textContent, /request failed/);
  const expires = value._familyMessageUntil;
  const originalNow = Date.now;
  Date.now = () => expires;
  try {
    value._updateFamilyFeedback();
    assert.doesNotMatch(value._familyFeedback.textContent, /request failed/);
    assert.match(value._familyFeedback.textContent, /Next family refresh:/);
    assert.equal(value._familyButton.disabled, true);
  } finally {
    Date.now = originalNow;
  }
});

test("family control stays hidden when the provider cannot refresh the full Circle", async () => {
  const value = card({ connection: {}, callWS: async () => response() });
  await tick();
  assert.equal(value.shadowRoot.querySelector(".family-refresh").hidden, true);
  value.remove();
});

test("manual family limit displays its exact next time and re-enables after expiry", async () => {
  const stamp = new Date(Date.now() + 5 * 60000).toISOString();
  let state = {
    available: true,
    status: "idle",
    members: [],
    next_available_at: stamp,
  };
  const value = card({
    connection: {},
    callWS: async () => ({ ...response(), family_refresh: state }),
  });
  await tick();
  assert.equal(value._familyButton.disabled, true);
  assert.match(value._familyFeedback.textContent, /Next family refresh:/);
  assert.ok(
    value._familyFeedback.textContent.includes(value._familyRetryLabel(stamp)),
  );
  value._familyRetryAt = new Date(Date.now() - 1).toISOString();
  value._familyMessage = "Previous wait has expired.";
  state = { ...state, next_available_at: null };
  await value._load();
  assert.equal(value._familyButton.disabled, false);
  assert.equal(value._familyFeedback.textContent, "");
  value.remove();
});

test("radar is opt-in and preserves selection, zoom, markers and base layers", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "osm" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [homeMember("one")];
  data.focus_ids.overview = [data.members[0].id];
  value._data = data;
  value._render();
  const map = value._map;
  const radar = value._radarController;
  assert.equal(radar.layer, undefined);
  assert.equal(radar.toggle.getAttribute("aria-pressed"), "false");
  assert.deepEqual(
    [...value._mapControls.querySelectorAll("button")].map(
      (node) => node.textContent,
    ),
    ["Street", "Radar", "Satellite"],
  );
  const center = map.getCenter(),
    zoom = map.getZoom(),
    markers = value._layer;
  radar.toggle.click();
  const overlay = radar.layer;
  assert.equal(radar.options.hidden, true);
  radar.setShowControls(true);
  assert.equal(radar.options.hidden, false);
  const preference = radar.preferenceKey();
  assert.equal(window.localStorage.getItem(preference), "true");
  radar.setShowControls(false);
  assert.equal(radar.options.hidden, true);
  assert.equal(map.hasLayer(overlay), true);
  assert.equal(map.hasLayer(overlay), true);
  assert.deepEqual(map.getCenter(), center);
  assert.equal(map.getZoom(), zoom);
  assert.equal(value._layer, markers);
  assert.equal(map.getPane("homecircle-radar").style.pointerEvents, "none");
  value._satelliteButton.click();
  assert.equal(radar.layer, overlay);
  assert.equal(map.hasLayer(overlay), true);
  value.shadowRoot
    .querySelector(`.member[data-focus="${data.members[0].id}"]`)
    .click();
  assert.equal(map.getZoom(), zoom + 3);
  assert.equal(radar.layer, overlay);
  value._overview.click();
  assert.equal(map.getZoom(), zoom);
  radar.range.value = "40";
  radar.range.dispatchEvent(new window.Event("input"));
  assert.equal(overlay.options.opacity, 0.4);
  overlay.fire("tileerror");
  assert.match(radar.note.textContent, /unavailable/);
  overlay.fire("load");
  assert.match(radar.note.textContent, /unavailable/);
  overlay.fire("loading");
  overlay.fire("load");
  assert.match(radar.note.textContent, /Observed U.S. radar/);
  radar.toggle.click();
  assert.equal(map.hasLayer(overlay), false);
  assert.equal(radar.timer, null);
  assert.equal(map.getZoom(), zoom);
  // A removed radar layer must not interrupt subsequent Leaflet zoom events.
  for (let cycle = 0; cycle < 3; cycle++) {
    assert.doesNotThrow(() => value._zoomCentered(1));
    assert.equal(value._tiles._tileZoom, Math.min(map.getZoom(), 16));
    assert.doesNotThrow(() => value._zoomCentered(-1));
    radar.toggle.click();
    radar.toggle.click();
  }
  assert.equal(
    map.attributionControl._attributions[overlay.options.attribution],
    0,
  );
  value.remove();
});

test("Private prevents radar requests and disconnection disposes enabled radar", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  document.body.append(value);
  value._updateMap([]);
  let radar = value._radarController;
  assert.equal(radar.controls.hidden, true);
  radar.toggle.click();
  assert.equal(radar.layer, undefined);
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "osm" });
  value._updateMap([]);
  radar = value._radarController;
  radar.toggle.click();
  assert.ok(radar.layer);
  assert.ok(radar.timer);
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "none" });
  value._updateMap([]);
  assert.equal(radar.layer, null);
  assert.equal(radar.timer, null);
  assert.equal(radar.controls.hidden, true);
  value.setConfig({ type: "custom:homecircle-card", map_tiles: "osm" });
  value._updateMap([]);
  radar.toggle.click();
  assert.ok(radar.layer);
  value.remove();
  assert.equal(radar.layer, null);
  assert.equal(radar.timer, null);
});

test("radar animation buffers frames, loops in order and returns to latest on map movement", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  value._updateMap([homeMember("animation")]);
  try {
    const map = value._map,
      base = value._tiles,
      markers = value._layer,
      radar = value._radarController;
    Object.defineProperty(document, "hidden", {
      value: false,
      configurable: true,
    });
    radar.toggle.click();
    const latest = radar.layer;
    radar.observed = observedFrames({
      meta: { valid: "2026-10-10T07:10:00Z" },
    });
    radar.play.click();
    const frames = [...radar.frames];
    assert.equal(frames.length, 7);
    assert.match(frames[0].layer._url, /USCOMP-N0Q-202610100640/);
    assert.match(frames[5].layer._url, /USCOMP-N0Q-202610100705/);
    assert.match(frames[6].layer._url, /USCOMP-N0Q-202610100710/);
    assert.equal(radar.options.hidden, true);
    radar.advanceFrame();
    assert.equal(radar.currentFrame, null);
    assert.equal(latest.options.opacity, 0.4);
    for (const frame of frames) frame.layer.fire("load");
    for (const minutes of [30, 25, 20, 15, 10, 5, 0, 30]) {
      radar.advanceFrame();
      assert.equal(radar.currentFrame.minutes, minutes);
      assert.equal(radar.currentFrame.layer.options.opacity, 0.4);
      assert.equal(
        frames.filter((frame) => frame.layer.options.opacity > 0).length,
        1,
      );
    }
    assert.equal(value._tiles, base);
    assert.equal(value._layer, markers);
    value._zoomCentered(1);
    assert.equal(radar.playing, false);
    assert.equal(radar.animationTimer, null);
    assert.ok(frames.every((frame) => !map.hasLayer(frame.layer)));
    assert.equal(latest.options.opacity, 0.4);
    assert.match(radar.frameLabel.textContent, /Observed.*Oct 10/);
    assert.doesNotThrow(() => value._zoomCentered(-1));
  } finally {
    delete document.hidden;
    value.remove();
  }
});

test("radar animation failure, visibility and disposal clean up all historical layers", () => {
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  value._updateMap([]);
  try {
    const radar = value._radarController,
      map = value._map;
    Object.defineProperty(document, "hidden", {
      value: false,
      configurable: true,
    });
    radar.toggle.click();
    radar.observed = observedFrames({
      meta: { valid: "2026-10-10T07:10:00Z" },
    });
    radar.play.click();
    let frames = [...radar.frames];
    frames[0].layer.fire("tileerror");
    radar.advanceFrame();
    assert.equal(radar.playing, false);
    assert.match(radar.note.textContent, /Animation unavailable/);
    assert.ok(frames.every((frame) => !map.hasLayer(frame.layer)));
    radar.play.click();
    Object.defineProperty(document, "hidden", {
      value: true,
      configurable: true,
    });
    document.dispatchEvent(new window.Event("visibilitychange"));
    assert.equal(radar.playing, false);
    delete document.hidden;
    radar.play.click();
    frames = [...radar.frames];
    value.remove();
    assert.equal(radar.animationTimer, null);
    assert.equal(radar.timer, null);
    assert.equal(radar.layer, null);
    assert.ok(frames.every((frame) => frame.layer._map === null));
  } finally {
    delete document.hidden;
    value.remove();
  }
});

test("weather metadata pins observed and forecast playback times and rejects expired forecasts", async () => {
  const originalFetch = window.fetch;
  Object.defineProperty(document, "hidden", {
    value: false,
    configurable: true,
  });
  let expired = false;
  const now = Date.now();
  const observed = new Date(Math.floor(now / 300000) * 300000).toISOString();
  window.fetch = async (url) => ({
    ok: true,
    json: async () =>
      url.includes("USCOMP")
        ? { meta: { valid: observed } }
        : {
            model_init_utc: new Date(
              now - (expired ? 24 : 2) * 3600000,
            ).toISOString(),
          },
  });
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  value._updateMap([]);
  const radar = value._radarController;
  try {
    radar.toggle.click();
    await radar.loadMetadata();
    assert.match(radar.frameLabel.textContent, /Observed/);
    assert.match(radar.layer._url, /ridge::USCOMP-N0Q-/);
    radar.timeline.value = "future";
    await radar.timeline.onchange();
    assert.equal(radar.frames.length, 9);
    assert.ok(
      radar.frames.every(
        (frame) => frame.time > now && frame.kind === "Forecast",
      ),
    );
    for (const frame of radar.frames) frame.layer.fire("load");
    radar.advanceFrame();
    assert.match(radar.frameLabel.textContent, /Forecast/);
    assert.match(radar.note.textContent, /HRRR prediction.*model run/);
    radar.range.value = "60";
    radar.range.dispatchEvent(new window.Event("input"));
    assert.equal(radar.currentFrame.layer.options.opacity, 0.6);
    radar.play.click();
    assert.equal(radar.playing, false);
    assert.match(radar.frameLabel.textContent, /Observed/);
    expired = true;
    await radar.loadMetadata();
    radar.play.click();
    assert.equal(radar.playing, false);
    assert.match(radar.note.textContent, /Forecast unavailable/);
    radar.toggle.click();
    assert.equal(radar.playback.hidden, true);
  } finally {
    value.remove();
    window.fetch = originalFetch;
    delete document.hidden;
  }
});

test("moving markers preserve the manually chosen view and radar playback; recenter remains explicit", async () => {
  const oldFetch = window.fetch;
  window.fetch = async () => {
    throw new Error("offline weather metadata");
  };
  Object.defineProperty(document, "hidden", {
    value: false,
    configurable: true,
  });
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [homeMember("moving")];
  data.focus_ids.overview = [data.members[0].id];
  value._data = data;
  value._render();
  try {
    const map = value._map,
      radar = value._radarController;
    map.panBy([150, 40], { animate: false });
    map.setZoom(10, { animate: false });
    const center = map.getCenter(),
      zoom = map.getZoom();
    radar.toggle.click();
    await tick();
    radar.observed = observedFrames({
      meta: { valid: new Date().toISOString() },
    });
    await radar.startPlayback();
    for (const frame of radar.frames) frame.layer.fire("load");
    radar.advanceFrame();
    const current = radar.currentFrame;
    const newCoordinate = 0.005;
    data.members[0].location.latitude = newCoordinate;
    value._render();
    assert.deepEqual(map.getCenter(), center);
    assert.equal(map.getZoom(), zoom);
    assert.equal(radar.playing, true);
    assert.equal(radar.currentFrame, current);
    assert.equal(value._points[0].location.latitude, newCoordinate);
    value._recenterButton.click();
    assert.equal(radar.playing, false);
    assert.notDeepEqual(map.getCenter(), center);
    assert.ok(map.getBounds().contains([newCoordinate, 0]));
    assert.equal(map.getZoom(), 14);
    value._choose(data.members[0].id);
    assert.equal(value._mode, data.members[0].id);
    assert.equal(map.getZoom(), 17);
    value._choose("overview");
    assert.equal(map.getZoom(), 14);
  } finally {
    value.remove();
    window.fetch = oldFetch;
    delete document.hidden;
  }
});

test("temporary snapshot and connection errors preserve last data, selection and enabled radar", async () => {
  const oldFetch = window.fetch;
  window.fetch = async () => {
    throw new Error("offline weather metadata");
  };
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  const data = response();
  data.members = [homeMember("recovery")];
  data.focus_ids.overview = [data.members[0].id];
  const connection = {},
    user = { id: "example-user" };
  let failure = false;
  const callWS = async () => {
    if (failure) throw { code: "not_ready" };
    return data;
  };
  value.hass = { connection, user, connected: true, callWS };
  await tick();
  try {
    value._choose(data.members[0].id);
    const map = value._map,
      radar = value._radarController;
    radar.toggle.click();
    failure = true;
    await value._load();
    assert.equal(value._map, map);
    assert.equal(value._data, data);
    assert.equal(value._mode, data.members[0].id);
    assert.equal(radar.enabled, true);
    assert.match(value._status.textContent, /starting.*last received/);
    assert.ok(value._retry);
    value.hass = { connection, user, connected: false, callWS };
    assert.equal(value._map, map);
    assert.equal(radar.enabled, true);
    failure = false;
    value.hass = { connection: {}, user, connected: true, callWS };
    await tick();
    assert.equal(value._map, map);
    assert.equal(value._mode, data.members[0].id);
    assert.equal(value._error, null);
    assert.doesNotMatch(value._status.textContent, /last received|starting/);
    value._hass.callWS = async () => {
      throw { code: "unauthorized" };
    };
    await value._load();
    assert.equal(value._data, null);
    assert.equal(value._map, null);
    assert.equal(radar.enabled, false);
  } finally {
    value.remove();
    window.fetch = oldFetch;
  }
});

test("radar resets stale labels, recovers metadata failures, and refreshes future frames on resume", async () => {
  const oldFetch = window.fetch;
  Object.defineProperty(document, "hidden", {
    value: false,
    configurable: true,
  });
  const value = document.createElement("homecircle-card");
  value.setConfig({ type: "custom:homecircle-card" });
  document.body.append(value);
  Object.defineProperty(value._mapNode, "clientWidth", { value: 640 });
  Object.defineProperty(value._mapNode, "clientHeight", { value: 300 });
  value._updateMap([homeMember("weather")]);
  let fail = false,
    calls = 0;
  window.fetch = async (url) => {
    calls++;
    if (fail) throw new Error("synthetic failure");
    return {
      ok: true,
      json: async () =>
        url.includes("USCOMP")
          ? { meta: { valid: new Date().toISOString() } }
          : {
              model_init_utc: new Date(Date.now() - 6 * 3600000).toISOString(),
            },
    };
  };
  const radar = value._radarController;
  try {
    radar.toggle.click();
    await tick();
    assert.match(radar.layer._url, /ridge::/);
    fail = true;
    await radar.loadMetadata();
    assert.match(radar.layer._url, /nexrad-n0q-900913/);
    assert.equal(radar.observed, null);
    assert.match(radar.frameLabel.textContent, /time unavailable/);
    radar.layer.fire("load");
    assert.doesNotMatch(radar.note.textContent, /Latest/);
    radar.toggle.click();
    radar.toggle.click();
    assert.match(radar.frameLabel.textContent, /time unavailable/);
    await tick();
    fail = false;
    const before = calls;
    Object.defineProperty(document, "hidden", {
      value: true,
      configurable: true,
    });
    document.dispatchEvent(new window.Event("visibilitychange"));
    Object.defineProperty(document, "hidden", {
      value: false,
      configurable: true,
    });
    document.dispatchEvent(new window.Event("visibilitychange"));
    await tick();
    assert.equal(calls, before + 2);
    radar.timeline.value = "future";
    radar.metadataAt = Date.now() - 300001;
    const refreshBefore = calls;
    await radar.startPlayback();
    assert.equal(calls, refreshBefore + 2);
    assert.ok(radar.frames.length > 0);
    assert.ok(radar.frames.every((frame) => frame.time > Date.now()));
    assert.equal(radar.layer.options.opacity, 0.4);
    radar.range.value = "60";
    radar.range.dispatchEvent(new window.Event("input"));
    assert.equal(radar.layer.options.opacity, 0.6);
    for (const frame of radar.frames) frame.layer.fire("load");
    radar.advanceFrame();
    assert.equal(radar.layer.options.opacity, 0);
    assert.equal(radar.currentFrame.layer.options.opacity, 0.6);
  } finally {
    value.remove();
    window.fetch = oldFetch;
    delete document.hidden;
  }
});
