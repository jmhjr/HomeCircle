import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { openMemberDialog } from "../src/member-dialog.js";

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

for (const [status, message] of [
  ["waiting", "Waiting for a tracker report"],
  ["no_response", "No later tracker report received"],
  ["send_failed", "Home Assistant could not send the request"],
  [
    "response_unverified",
    "Response to a request before HA restarted cannot be verified",
  ],
  ["tracker_responded", "A later tracker report arrived"],
]) {
  test(`Details separates ${status} from GPS-fix evidence`, () => {
    const member = {
      id: "person.example_member",
      name: "Example",
      presence: "home",
      focusable: true,
      location: {
        origin: "active_gps",
        evidence: {
          source_label: "Tracker: Example phone",
          card_source_label: "Tracker: Home Assistant",
          reported_at: "2026-01-01T10:00:00+00:00",
          observed_at: "2026-01-01T12:00:00+00:00",
          report_status: "tracker_attribute",
          freshness: "stale",
        },
      },
      driving: { value: false },
      issues: [],
      location_request: {
        enabled: true,
        status,
        requested_at: "2026-01-01T11:59:00+00:00",
      },
    };
    const card = { _data: { members: [member] } };
    const hass = {
      user: { is_admin: false },
      callWS: () => {
        throw new Error("No real requests allowed");
      },
    };
    const dialog = openMemberDialog(card, hass, member.id);
    assert.match(dialog.textContent, new RegExp(message));
    assert.match(dialog.textContent, /Last request attempted/);
    assert.match(dialog.textContent, /Source location report/);
    assert.match(dialog.textContent, /Stale report/);
    assert.equal(dialog.textContent.includes("New GPS fix"), false);
    dialog.close();
    assert.equal(document.querySelector("dialog"), null);
  });
}
