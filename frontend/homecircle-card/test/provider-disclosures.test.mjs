import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { openSettingsDialog } from "../src/settings-dialog.js";

const terms = [
  "https://www.apple.com/legal/internet-services/icloud/en/terms.html",
  "https://www.apple.com/legal/sla/docs/iTunes.pdf",
  "https://legal.corp.life360.com/hc/en-us/articles/42963368361239-Life360-Terms-of-Service-2026-8",
];

async function show(description) {
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
  const calls = [];
  const hass = {
    user: { is_admin: true },
    localize: (key) => (key.endsWith(".description") ? description : undefined),
    callWS: async () => [{ entry_id: "example-entry" }],
    callApi: async (method) => {
      calls.push(method);
      return {
        type: "form",
        flow_id: "example-flow",
        step_id: "findmy_add",
        data_schema: [
          {
            name: "consent",
            required: true,
            default: false,
            selector: { boolean: {} },
          },
        ],
      };
    },
  };
  await openSettingsDialog({ _hass: hass }, hass);
  return { dom, dialog: document.querySelector("dialog"), calls };
}

test("official provider terms are readable links without exposing the HA referrer", async () => {
  const { dialog, calls } = await show(
    terms.map((url) => "[Read terms](" + url + ")").join(" and "),
  );
  const links = [...dialog.querySelectorAll(".description a")];
  assert.deepEqual(
    links.map((a) => a.href),
    terms,
  );
  for (const a of links) {
    assert.equal(a.target, "_blank");
    assert.equal(a.rel, "noopener noreferrer");
    assert.equal(a.referrerPolicy, "no-referrer");
  }
  assert.equal(dialog.querySelector("ha-form").data.consent, false);
  assert.deepEqual(calls, ["POST"]);
  dialog.close();
});

test("unknown and active-content URLs stay inert plain text", async () => {
  const { dialog } = await show(
    "[bad](javascript:alert(1)) [bad](https://example.invalid/) <img src=x onerror=alert(1)>",
  );
  assert.equal(dialog.querySelectorAll(".description a").length, 0);
  assert.equal(dialog.querySelectorAll(".description img").length, 0);
  assert.match(dialog.querySelector(".description").textContent, /javascript:/);
  dialog.close();
});

test("escaped account text never becomes a legal link", async () => {
  const { dialog } = await show(
    "Account: \\[not a notice\\](" + terms[0] + ")",
  );
  assert.equal(dialog.querySelectorAll(".description a").length, 0);
  assert.match(
    dialog.querySelector(".description").textContent,
    /\[not a notice\]/,
  );
  dialog.close();
});

test("the existing People settings link remains local", async () => {
  const { dialog } = await show(
    "Open [Home Assistant People settings](/config/person).",
  );
  const a = dialog.querySelector(".description a");
  assert.equal(a.getAttribute("href"), "/config/person");
  assert.equal(a.target, "");
  dialog.close();
});
