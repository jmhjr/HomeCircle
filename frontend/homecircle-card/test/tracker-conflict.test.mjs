import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { openSettingsDialog } from "../src/settings-dialog.js";

const dom = new JSDOM("<!doctype html><body></body>", {
  url: "http://localhost/",
});
globalThis.document = dom.window.document;
dom.window.HTMLDialogElement.prototype.showModal = function () {
  this.open = true;
};
dom.window.HTMLDialogElement.prototype.close = function () {
  this.dispatchEvent(new dom.window.Event("close"));
};

test("conflict settings expose an internal Person link and cancel without saving", async () => {
  const calls = [];
  const hass = {
    user: { is_admin: true },
    localize: (key) =>
      key.endsWith(".description")
        ? "**Tracker disagreement**. [Home Assistant People settings](/config/person)."
        : undefined,
    callWS: async () => [{ entry_id: "example-entry" }],
    callApi: async (method, path) => {
      calls.push({ method, path });
      return {
        type: "form",
        flow_id: "example-flow",
        step_id: "member",
        data_schema: [],
        description_placeholders: { person_settings_path: "/config/person" },
      };
    },
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const dialog = document.querySelector("dialog");
  const link = dialog.querySelector("a");
  assert.equal(link.getAttribute("href"), "/config/person");
  assert.equal(link.textContent, "Home Assistant People settings");
  assert.equal(
    dialog.textContent.includes("[Home Assistant People settings]"),
    false,
  );
  assert.equal(dialog.textContent.includes("**"), false);
  link.addEventListener("click", (event) => event.preventDefault());
  link.click();
  assert.equal(document.querySelector("dialog"), null);
  assert.deepEqual(
    calls.map((call) => call.method),
    ["POST", "DELETE"],
  );
});

test("non-admin cannot open settings or read conflict guidance", async () => {
  const hass = {
    user: { is_admin: false },
    callWS: async () => {
      throw new Error("Must not read admin configuration");
    },
  };
  await openSettingsDialog({ _hass: hass }, hass);
  assert.equal(document.querySelector("dialog"), null);
});

for (const memberId of [null, "person.example_member"]) {
  test(`closing during initial flow creation cancels the late flow (${memberId || "household"})`, async () => {
    let resolvePost;
    const pending = new Promise((resolve) => {
      resolvePost = resolve;
    });
    const calls = [];
    const hass = {
      user: { is_admin: true },
      callWS: async () => [{ entry_id: "example-entry" }],
      callApi: async (method, path) => {
        calls.push({ method, path });
        return method === "POST" ? pending : undefined;
      },
    };
    const opening = openSettingsDialog({ _hass: hass }, hass, memberId);
    await new Promise((resolve) => setImmediate(resolve));
    document.querySelector("dialog").close();
    resolvePost({
      type: "form",
      flow_id: "late-flow",
      step_id: "member",
      data_schema: [],
    });
    await opening;
    assert.equal(document.querySelector("dialog"), null);
    assert.deepEqual(calls, [
      { method: "POST", path: "config/config_entries/options/flow" },
      {
        method: "DELETE",
        path: "config/config_entries/options/flow/late-flow",
      },
    ]);
  });
}

test("closing while translations load prevents creating an options flow", async () => {
  let resolveTranslation;
  const pending = new Promise((resolve) => {
    resolveTranslation = resolve;
  });
  const calls = [];
  const hass = {
    user: { is_admin: true },
    callWS: async () => [{ entry_id: "example-entry" }],
    loadFragmentTranslation: () => pending,
    callApi: async (...args) => {
      calls.push(args);
    },
  };
  const opening = openSettingsDialog({ _hass: hass }, hass);
  await new Promise((resolve) => setImmediate(resolve));
  document.querySelector("dialog").close();
  resolveTranslation();
  await opening;
  assert.deepEqual(calls, []);
});

test("closing during member-specific navigation cancels the known flow once", async () => {
  let resolveNavigation;
  const pending = new Promise((resolve) => {
    resolveNavigation = resolve;
  });
  const calls = [];
  const initial = {
    type: "form",
    flow_id: "member-flow",
    step_id: "init",
    data_schema: [],
  };
  const hass = {
    user: { is_admin: true },
    callWS: async () => [{ entry_id: "example-entry" }],
    callApi: async (method, path) => {
      calls.push({ method, path });
      if (method === "DELETE") return;
      return path.endsWith("/member-flow") ? pending : initial;
    },
  };
  const opening = openSettingsDialog(
    { _hass: hass },
    hass,
    "person.example_member",
  );
  await new Promise((resolve) => setImmediate(resolve));
  document.querySelector("dialog").close();
  resolveNavigation({ ...initial, step_id: "tracker_member_choice" });
  await opening;
  assert.equal(calls.filter((call) => call.method === "DELETE").length, 1);
  assert.equal(document.querySelector("dialog"), null);
});

test("rapid Back taps create one replacement and closing cancels every session", async () => {
  let releaseLookup;
  let lookups = 0;
  let created = 0;
  const calls = [];
  const hass = {
    user: { is_admin: true },
    callWS: async () => {
      lookups++;
      if (lookups > 1)
        await new Promise((resolve) => {
          releaseLookup = resolve;
        });
      return [{ entry_id: "example-entry" }];
    },
    callApi: async (method, path) => {
      calls.push({ method, path });
      if (method === "DELETE") return;
      return {
        type: "form",
        flow_id: `flow-${++created}`,
        step_id: "member",
        data_schema: [],
      };
    },
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const back = document.querySelector(".actions button");
  back.click();
  back.click();
  assert.equal(lookups, 2);
  releaseLookup();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(created, 2);
  document.querySelector("dialog").close();
  assert.deepEqual(
    calls.filter((call) => call.method === "DELETE").map((call) => call.path),
    [
      "config/config_entries/options/flow/flow-1",
      "config/config_entries/options/flow/flow-2",
    ],
  );
});

test("Back cannot replace a session while Continue is pending", async () => {
  let releaseContinue;
  let lookups = 0;
  const calls = [];
  const flow = {
    type: "form",
    flow_id: "active-flow",
    step_id: "member",
    data_schema: [],
  };
  const hass = {
    user: { is_admin: true },
    callWS: async () => {
      lookups++;
      return [{ entry_id: "example-entry" }];
    },
    callApi: async (method, path) => {
      calls.push({ method, path });
      if (method === "DELETE") return;
      if (path.endsWith("/active-flow"))
        return new Promise((resolve) => {
          releaseContinue = resolve;
        });
      return flow;
    },
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const [back, next] = document.querySelectorAll(".actions button");
  next.click();
  back.click();
  assert.equal(lookups, 1);
  releaseContinue(flow);
  await new Promise((resolve) => setImmediate(resolve));
  document.querySelector("dialog").close();
  assert.equal(calls.filter((call) => call.method === "DELETE").length, 1);
});
