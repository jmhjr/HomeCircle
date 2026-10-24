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
const base = {
  user: { is_admin: true },
  callWS: async () => [{ entry_id: "example-entry" }],
};

test("Find My settings renders only supported native account actions", async () => {
  const hass = {
    ...base,
    callApi: async () => ({
      type: "menu",
      flow_id: "example-flow",
      step_id: "findmy_account_actions",
      menu_options: [
        "findmy_saved_items",
        "findmy_reconnect",
        "findmy_edit_items",
        "findmy_disconnect",
      ],
    }),
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const dialog = document.querySelector("dialog");
  const actions = [...dialog.querySelectorAll("button")]
    .filter((control) => control.classList.contains("choice"))
    .map((control) => control.textContent);
  assert.deepEqual(actions, [
    "findmy_saved_items",
    "findmy_reconnect",
    "findmy_edit_items",
    "findmy_disconnect",
  ]);
  assert.ok(!dialog.textContent.includes("migration"));
  dialog.close();
});

test("Find My item picker starts empty and supports select all and clear", async () => {
  const hass = {
    ...base,
    callApi: async () => ({
      type: "form",
      flow_id: "example-flow",
      step_id: "findmy_select",
      data_schema: [
        {
          name: "items",
          default: [],
          selector: {
            select: {
              multiple: true,
              options: [
                { value: "example-a", label: "Example first" },
                { value: "example-b", label: "Example second" },
              ],
            },
          },
        },
      ],
    }),
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const dialog = document.querySelector("dialog");
  const form = dialog.querySelector("ha-form");
  assert.deepEqual(form.data.items, []);
  [...dialog.querySelectorAll("button")]
    .find((control) => control.textContent === "Select all")
    .click();
  assert.deepEqual(form.data.items, ["example-a", "example-b"]);
  [...dialog.querySelectorAll("button")]
    .find((control) => control.textContent === "Clear selection")
    .click();
  assert.deepEqual(form.data.items, []);
  assert.equal(
    dialog.querySelector('input[type="search"]').getAttribute("aria-label"),
    "Search Find My items",
  );
  dialog.close();
});

for (const progressType of ["progress", "progress_done"])
  test(`Apple ${progressType} reads the current form without submitting empty credentials`, async () => {
    const calls = [];
    const hass = {
      ...base,
      callApi: async (method, path, data) => {
        calls.push({ method, path, data });
        if (method === "POST")
          return {
            type: progressType,
            flow_id: "example-flow",
            step_id: "findmy_wait",
            progress_action: "findmy_connecting",
          };
        if (method === "GET")
          return {
            type: "form",
            flow_id: "example-flow",
            step_id: "findmy_device",
            data_schema: [],
          };
      },
    };
    await openSettingsDialog({ _hass: hass }, hass);
    await new Promise((resolve) => setTimeout(resolve, 2100));
    assert.deepEqual(
      calls.map((call) => call.method),
      ["POST", "GET"],
    );
    assert.ok(document.querySelector("ha-form"));
    document.querySelector("dialog").close();
    assert.equal(calls.at(-1).method, "DELETE");
  });

test("existing Find My choices stay preselected until deliberately cleared", async () => {
  const hass = {
    ...base,
    callApi: async () => ({
      type: "form",
      flow_id: "example-existing-flow",
      step_id: "findmy_select",
      data_schema: [
        {
          name: "items",
          default: ["example-existing"],
          selector: {
            select: {
              multiple: true,
              options: [
                { value: "example-existing", label: "Existing item" },
                { value: "example-new", label: "New item" },
              ],
            },
          },
        },
      ],
    }),
  };
  await openSettingsDialog({ _hass: hass }, hass);
  const dialog = document.querySelector("dialog");
  const form = dialog.querySelector("ha-form");
  assert.deepEqual(form.data.items, ["example-existing"]);
  [...dialog.querySelectorAll("button")]
    .find((control) => control.textContent === "Clear selection")
    .click();
  assert.deepEqual(form.data.items, []);
  dialog.close();
});
