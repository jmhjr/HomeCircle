import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
test("default card title follows the integration beta release", async () => {
  const manifest = JSON.parse(
    readFileSync(
      new URL(
        "../../../custom_components/homecircle/manifest.json",
        import.meta.url,
      ),
    ),
  );
  const beta = /-beta\.(\d+)$/.exec(manifest.version)?.[1];
  assert.ok(beta);
  const expected = `HomeCircle - Beta ${beta}`;
  const value = card({ connection: {}, callWS: async () => response() });
  await tick();
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
    assert.equal(toggle.textContent, "Kiosk view");
    toggle.click();
    assert.equal(
      new URL(window.location.href).searchParams.get("homecircle_kiosk"),
      "1",
    );
    assert.equal(toggle.textContent, "Exit kiosk");
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
    assert.equal(toggle.textContent, "Kiosk view");
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
    assert.match(dialog.textContent, /Person and tracker settings/);
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
    choices.querySelectorAll("button")[1].click();
    await tick();
    assert.deepEqual(flowCalls[2], {
      method: "POST",
      path: "config/config_entries/options/flow/sample-flow",
      data: { member: "sample", setting: "sensors" },
    });
    assert.deepEqual(flowCalls[1], {
      method: "POST",
      path: "config/config_entries/options/flow/sample-flow",
      data: { next_step_id: "tracker_member_choice" },
    });
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
    assert.equal(flowCalls.at(-2).data.next_step_id, "tracker_member_choice");
    dialog.querySelectorAll(".body .choice")[2].click();
    await tick();
    dialog.querySelectorAll(".actions button")[1].click();
    await tick();
    assert.match(
      dialog.textContent,
      /Review Sample tracker removed before saving/,
    );
    dialog.close();
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
