import { labels, reportParts } from "./model.js";
import { openSettingsDialog } from "./settings-dialog.js";

const issueMessages = {
  tracker_presence_conflict:
    "The HA Person and a selected GPS tracker disagree about Home or Away. Check which trackers are linked to the HA Person and when each last updated.",
  person_tracker_location_conflict:
    "The HA Person and its active GPS tracker have different positions. The map position is withheld until they agree.",
  active_source_unavailable:
    "The HA Person's active tracker is unavailable. Check the tracker integration and its last update.",
  active_source_locationless:
    "The active tracker has no usable GPS position. Presence may still be available.",
  ambiguous_gps_sources:
    "More than one selected GPS tracker could supply the position. Review tracker selection.",
  location_source_unverified:
    "The map position's source could not be verified against the selected trackers.",
  location_report_source_mismatch:
    "The configured report-time sensor belongs to a different source. Review this person's report-time settings.",
  residence_zone_unavailable:
    "A configured residence zone is unavailable. Check the zone in Home Assistant.",
  person_unavailable:
    "The HA Person is unavailable. Check the Person and its linked trackers in Home Assistant.",
  tracker_unavailable:
    "The selected tracker is unavailable. Check its integration in Home Assistant.",
  ambiguous_zone_name:
    "More than one HA zone has this name. Review the configured places.",
  unresolved_place:
    "This HA place could not be matched to a configured HomeCircle place.",
  legacy_home_membership:
    "HA reported Home without a zone ID. HomeCircle used the primary Home zone.",
  legacy_zone_name:
    "HA reported a place name without a zone ID. HomeCircle matched the unique configured zone.",
  gps_inside_zone_ha_pending:
    "A recent GPS report is well inside this configured place, but HA still says Away. HA may not have reassessed a newly added zone yet.",
};

function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = String(value);
  return node;
}

function timestamp(value, precise = false) {
  if (!value) return "Unknown";
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: precise ? "medium" : "short",
      }).format(date)
    : "Unknown";
}

function position(value) {
  if (
    !value ||
    !Number.isFinite(value.latitude) ||
    !Number.isFinite(value.longitude)
  )
    return "Unknown";
  const coordinates = `${value.latitude.toFixed(6)}, ${value.longitude.toFixed(6)}`;
  return value.accuracy == null
    ? coordinates
    : `${coordinates} · accuracy ${value.accuracy} m`;
}

function row(parent, label, value) {
  const item = element("div", "detail-row");
  item.append(element("dt", null, label), element("dd", null, value));
  parent.append(item);
}

function section(body, title) {
  const wrapper = element("section");
  wrapper.append(element("h3", null, title));
  body.append(wrapper);
  return wrapper;
}

function trackerName(label) {
  return label
    ?.replace(/^Tracker: /, "")
    .replace(/ · Mobile App$/, " · Home Assistant");
}

function details(body, member, card) {
  const olderOpen = body.querySelector(".older-activity")?.open || false;
  const technicalOpen = body.querySelector(".technical-details")?.open || false;
  body.replaceChildren();
  const proof = member.location?.evidence;
  const diagnostic = member.diagnostics || {};
  const issues = member.issues || [];
  const summary = section(body, "Current status");
  const current = element("dl");
  row(current, "Status", labels[member.presence] || "Unknown");
  row(current, "Place", member.place || "No named place");
  row(
    current,
    "Map",
    !member.focusable
      ? "Position unavailable or withheld"
      : member.map_visible === false
        ? "Hidden from Everyone; selectable on the map"
        : "Shown on the map",
  );
  row(
    current,
    "Battery",
    member.battery == null
      ? "Unknown"
      : `${member.battery}%${member.charging === true ? " · charging" : ""}`,
  );
  row(
    current,
    "Driving",
    member.driving?.value === true
      ? member.driving.status === "current"
        ? "Current report"
        : "Last reported or unverified"
      : member.driving?.value === false
        ? "Not reported as driving"
        : "Unknown",
  );
  if (member.speed?.value != null)
    row(current, "Speed", `${member.speed.value} ${member.speed.unit || ""}`);
  summary.append(current);

  if (issues.length) {
    const attention = section(body, "Needs attention");
    attention.className = "detail-attention";
    const list = element("ul");
    for (const issue of issues)
      list.append(element("li", null, issueMessages[issue] || issue));
    attention.append(list);
  }

  const location = section(body, "Location report");
  const report = reportParts(member)
    .filter((part) => part.kind !== "source")
    .map((part) => part.text)
    .join(" · ");
  location.append(element("p", "report-summary", report));
  const evidence = element("dl");
  row(
    evidence,
    "Tracker used for map",
    trackerName(proof?.source_label) || "No usable map position",
  );
  if (member.location) {
    row(
      evidence,
      "Source location report",
      proof?.reported_at
        ? timestamp(proof.reported_at)
        : "Not provided by this tracker",
    );
    row(
      evidence,
      member.location.origin === "ha_person"
        ? "Home Assistant Person updated"
        : "Home Assistant tracker updated",
      timestamp(proof?.observed_at),
    );
  }
  location.append(evidence);
  const note = element(
    "p",
    "detail-note",
    member.location
      ? "A Home Assistant update may not mean a new GPS fix. An older location report can still show the correct position while stationary."
      : "Open tracker diagnostics below to check the selected trackers and their last recorded positions.",
  );
  location.append(note);
  const request = member.location_request;
  if (request?.enabled) {
    const requests = section(body, "Location requests");
    const requestRows = element("dl");
    row(
      requestRows,
      "Automatic requests",
      "Enabled for the selected Home Assistant phone tracker after 15 quiet minutes",
    );
    row(
      requestRows,
      "Last request attempted",
      request.requested_at ? timestamp(request.requested_at) : "None yet",
    );
    row(
      requestRows,
      "Request status",
      {
        tracker_responded: "A later tracker report arrived",
        waiting: "Waiting for a tracker report",
        no_response: "No later tracker report received",
        response_unverified:
          "Response to a request before HA restarted cannot be verified",
        send_failed: "Home Assistant could not send the request",
        quiet_pending: "Waiting for 15 quiet minutes",
        request_pending: "Request will be sent on the next check",
        unsupported: "No Home Assistant phone notification target is available",
        not_selected:
          "The Home Assistant phone tracker is not the current map source",
        no_position: "No current map position is available",
        unavailable: "Automatic requests are temporarily unavailable",
      }[request.status] || "Unknown",
    );
    if (request.next_request_at) {
      row(
        requestRows,
        "Request limit",
        "50 requests used in the last 24 hours",
      );
      row(
        requestRows,
        "Next request allowed",
        timestamp(request.next_request_at),
      );
    }
    requests.append(requestRows);
    requests.append(
      element(
        "p",
        "detail-note",
        "A request does not guarantee delivery or a new GPS fix. Attempts are at least one minute apart, with up to 50 in a rolling 24 hours.",
      ),
    );
  }

  const activity = section(body, "Recent activity");
  activity.className = "recent-activity";
  activity.append(
    element(
      "p",
      "detail-note",
      "Observed by HomeCircle; gaps and restarts do not confirm a journey. Up to 100 events per person, kept for seven days. Freshness changes are limited to 25 entries to preserve arrivals, departures and request results. No coordinates or routes are stored.",
    ),
  );
  const events = member.activity?.events || [];
  if (member.activity?.persistent === false)
    activity.append(
      element(
        "p",
        "detail-note",
        "Activity storage is unavailable. Events are kept only while HomeCircle is running.",
      ),
    );
  if (!events.length)
    activity.append(
      element(
        "p",
        "detail-note",
        "No activity recorded yet. History begins when this feature starts.",
      ),
    );
  const eventText = (event) => {
    if (event.kind === "started") return "Observation started or resumed";
    if (event.kind === "presence")
      return `Status observed: ${labels[event.value] || "Unknown"}`;
    if (event.kind === "source")
      return `Map source observed: ${trackerName(event.value) || "No usable map source"}`;
    if (event.kind === "freshness")
      return (
        {
          fresh: "Location report observed: fresh",
          stale: "Location report observed: stale",
          unknown: "Location report freshness is unknown",
          unavailable: "Location report unavailable",
        }[event.value] || "Location report changed"
      );
    if (event.kind === "automatic_refresh")
      return event.value === "requested"
        ? "Automatic location update requested; delivery unconfirmed"
        : "Automatic location update request could not be sent";
    if (event.kind === "refresh")
      return (
        {
          requested: "Location update requested; delivery unconfirmed",
          checked: "Cloud reports checked",
          cooldown: "Refresh skipped: request cooldown",
          busy: "Refresh skipped: check already in progress",
          limited: "Refresh skipped: daily request limit",
          disabled: "Refresh skipped: phone requests disabled",
          not_allowed: "Refresh skipped: control permission required",
          unsupported: "Refresh unavailable for this tracker",
          no_position: "Refresh skipped: no usable position",
          fresh: "Refresh skipped: report already fresh",
          send_failed: "Location update request could not be sent",
          unavailable: "Location check unavailable",
        }[event.value] || "Location check completed"
      );
    return "Activity observed";
  };
  const eventList = (items) => {
    const list = element("ol", "activity-list");
    for (const event of items) {
      const item = element("li");
      const time = element("time", null, timestamp(event.observed_at, true));
      time.dateTime = event.observed_at;
      item.append(time, element("span", null, eventText(event)));
      if (event.reported_at)
        item.append(
          element(
            "small",
            null,
            `Tracker report: ${timestamp(event.reported_at)}`,
          ),
        );
      list.append(item);
    }
    return list;
  };
  if (events.length) activity.append(eventList(events.slice(0, 5)));
  if (events.length > 5) {
    const older = element("details", "older-activity");
    older.open = olderOpen;
    older.append(
      element("summary", null, `Show ${events.length - 5} older events`),
      eventList(events.slice(5)),
    );
    activity.append(older);
  }

  const technical = element("details", "technical-details");
  technical.open = technicalOpen;
  technical.append(
    element("summary", null, "Tracker diagnostics and coordinates"),
  );
  const technicalBody = element("div", "technical-body");
  technical.append(technicalBody);
  body.append(technical);
  const map = section(technicalBody, "Map evidence");
  const mapRows = element("dl");
  row(mapRows, "Map coordinates", position(member.location));
  row(
    mapRows,
    "Time source",
    !member.location
      ? "No usable map position"
      : proof?.reported_at
        ? proof.report_status === "explicit_sensor"
          ? "Configured report-time sensor"
          : "Tracker supplied a location report time"
        : "Home Assistant state or attribute update; GPS report time unavailable",
  );
  map.append(mapRows);
  const sources = section(technicalBody, "Home Assistant sources");
  const sourceList = element("dl");
  if (diagnostic.person_entity) {
    row(sourceList, "HA Person", diagnostic.person_entity);
    row(sourceList, "Person state", diagnostic.person_state || "Unavailable");
    row(sourceList, "Person updated", timestamp(diagnostic.person_updated_at));
    row(
      sourceList,
      "HA Person coordinates",
      position(diagnostic.person_position),
    );
  }
  row(
    sourceList,
    "Active HA source",
    diagnostic.active_source === "other"
      ? "Another HA tracker, outside this person's HomeCircle selection"
      : trackerName(
          diagnostic.selected_trackers?.find(
            (tracker) => tracker.entity_id === diagnostic.active_source,
          )?.label,
        ) ||
          diagnostic.active_source ||
          "Unknown",
  );
  sources.append(sourceList);
  const trackers = diagnostic.selected_trackers || [];
  if (trackers.length) {
    sources.append(element("h4", null, "Selected trackers"));
    for (const tracker of trackers) {
      const entry = element("div", "tracker-detail");
      entry.append(
        element(
          "strong",
          null,
          trackerName(tracker.label) || tracker.entity_id,
        ),
        element("span", null, tracker.entity_id),
        element(
          "span",
          null,
          `State: ${tracker.state || "Unavailable"}${tracker.active ? " · active HA source" : ""}`,
        ),
        element("span", null, `HA update: ${timestamp(tracker.updated_at)}`),
        element("span", null, `Coordinates: ${position(tracker.position)}`),
      );
      const history = element("button", "history-button", "View HA history");
      history.type = "button";
      history.addEventListener("click", () => {
        body.closest("dialog")?.close();
        card.dispatchEvent(
          new CustomEvent("hass-more-info", {
            bubbles: true,
            composed: true,
            detail: { entityId: tracker.entity_id, view: "history" },
          }),
        );
      });
      entry.append(history);
      sources.append(entry);
    }
    sources.append(
      element(
        "p",
        "detail-note",
        "HA history shows recorded samples when Recorder has them. Gaps do not show the exact route traveled.",
      ),
    );
  } else sources.append(element("p", "detail-note", "No trackers selected."));

  if (!issues.length)
    location.append(
      element("p", "detail-note", "No HomeCircle conflicts detected."),
    );
}

export function openMemberDialog(card, hass, memberId, trigger) {
  const host =
    document.querySelector("home-assistant")?.shadowRoot || document.body;
  if (host.querySelector("dialog.homecircle-member-details")) return;
  const member = card._data?.members?.find((item) => item.id === memberId);
  if (!member) return;
  const dialog = element("dialog", "homecircle-member-details");
  dialog.setAttribute("aria-label", `${member.name} details`);
  const style = element("style");
  style.textContent = `
    dialog.homecircle-member-details { width: min(620px, calc(100vw - 24px)); max-height: min(88dvh, 850px); padding: 0; border: 0; border-radius: 20px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #222); box-shadow: 0 20px 70px #0008; }
    dialog.homecircle-member-details::backdrop { background: #000a; }
    dialog.homecircle-member-details[open] { display: flex; flex-direction: column; overflow: hidden; font: 14px/1.5 system-ui, sans-serif; }
    .homecircle-member-details * { box-sizing: border-box; }
    .homecircle-member-details header { display: flex; align-items: center; gap: 12px; padding: 18px 22px; border-bottom: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details h2 { flex: 1; margin: 0; font: 650 21px/1.3 system-ui, sans-serif; }
    .homecircle-member-details h3 { margin: 0 0 10px; font: 650 16px/1.3 system-ui, sans-serif; }
    .homecircle-member-details h4 { margin: 14px 0 6px; font: 600 14px/1.3 system-ui, sans-serif; }
    .homecircle-member-details header, .homecircle-member-details footer { flex-shrink: 0; }
    .homecircle-member-details .body { padding: 16px 22px; overflow-y: auto; min-height: 0; }
    .homecircle-member-details section + section { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details dl { margin: 0; }
    .homecircle-member-details .report-summary { margin: 0 0 10px; font-weight: 600; }
    .homecircle-member-details .detail-attention { border-left: 3px solid var(--warning-color, #c77700); padding-left: 12px; }
    .homecircle-member-details .technical-details { margin-top: 20px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details summary { padding: 12px 0; min-height: 44px; cursor: pointer; font-weight: 600; }
    .homecircle-member-details summary:focus-visible { outline: 3px solid var(--primary-color, #03a9f4); }
    .homecircle-member-details .technical-body { padding-top: 6px; }
    .homecircle-member-details .detail-row { display: grid; grid-template-columns: minmax(130px, 40%) minmax(0, 1fr); gap: 8px; padding: 5px 0; }
    .homecircle-member-details dt { color: var(--secondary-text-color, #666); }
    .homecircle-member-details dd { margin: 0; overflow-wrap: anywhere; }
    .homecircle-member-details .tracker-detail { display: grid; gap: 3px; margin: 10px 0; padding: 10px; border-radius: 9px; background: var(--secondary-background-color, #eee); overflow-wrap: anywhere; }
    .homecircle-member-details .tracker-detail span, .homecircle-member-details .detail-note { color: var(--secondary-text-color, #666); font-size: 13px; }
    .homecircle-member-details .activity-list { list-style: none; padding: 0; margin: 0; }
    .homecircle-member-details .activity-list li { display: grid; gap: 3px; padding: 9px 0; border-bottom: 1px solid var(--divider-color, #ddd); overflow-wrap: anywhere; }
    .homecircle-member-details .activity-list time, .homecircle-member-details .activity-list small { color: var(--secondary-text-color, #666); font-size: 12px; }
    .homecircle-member-details .history-button { color: var(--primary-color, #03a9f4); }
    .homecircle-member-details ul { margin: 0; padding-left: 20px; }
    .homecircle-member-details li + li { margin-top: 8px; }
    .homecircle-member-details footer { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; padding: 12px 22px 18px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details .refresh-feedback { flex: 1 1 100%; min-height: 18px; margin: 0; color: var(--secondary-text-color, #666); font-size: 13px; }
    .homecircle-member-details button { min-height: 44px; padding: 8px 12px; border: 1px solid var(--divider-color, #ccc); border-radius: 9px; background: var(--card-background-color, #fff); color: inherit; font: inherit; cursor: pointer; }
    .homecircle-member-details button:focus-visible { outline: 3px solid var(--primary-color, #03a9f4); }
    @media (max-width: 420px) {
      .homecircle-member-details header, .homecircle-member-details .body, .homecircle-member-details footer { padding-left: 14px; padding-right: 14px; }
      .homecircle-member-details .detail-row { grid-template-columns: minmax(96px, 36%) minmax(0, 1fr); padding: 6px 0; }
      .homecircle-member-details footer button { flex: 1 1 auto; }
    }
  `;
  const header = element("header");
  const heading = element("h2", null, member.name);
  heading.tabIndex = -1;
  header.append(heading);
  const closeButton = element("button", null, "Close");
  closeButton.type = "button";
  closeButton.addEventListener("click", () => dialog.close());
  const body = element("div", "body");
  details(body, member, card);
  const footer = element("footer");
  const feedback = element("p", "refresh-feedback");
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  feedback.textContent = "Refresh checks Home Assistant's saved data.";
  const refresh = element("button", null, "Refresh details");
  refresh.type = "button";
  refresh.addEventListener("click", async () => {
    if (card._hass?.connected === false || hass.connected === false) {
      feedback.textContent =
        "Home Assistant is disconnected. Try again when it reconnects.";
      return;
    }
    if (card._busy) {
      feedback.textContent =
        "An update is already in progress. Try again shortly.";
      return;
    }
    refresh.disabled = true;
    refresh.textContent = "Checking…";
    feedback.textContent = "Checking Home Assistant for updated details…";
    const before = card._data?.members?.find((item) => item.id === memberId);
    try {
      await card._load();
      if (!dialog.isConnected) return;
      const current = card._data?.members?.find((item) => item.id === memberId);
      if (!current) {
        feedback.textContent = "Could not refresh details. Try again.";
        return;
      }
      details(body, current, card);
      const previousReport =
        before?.location?.evidence?.reported_at ||
        before?.location?.evidence?.observed_at;
      const currentReport =
        current.location?.evidence?.reported_at ||
        current.location?.evidence?.observed_at;
      const checkedAt = new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date());
      const sourceChanged =
        before?.location?.evidence?.source_label !==
          current.location?.evidence?.source_label ||
        before?.location?.origin !== current.location?.origin;
      feedback.textContent = sourceChanged
        ? `Map source changed. Checked at ${checkedAt}.`
        : currentReport && currentReport !== previousReport
          ? `Report time changed. Checked at ${checkedAt}.`
          : currentReport
            ? `Checked at ${checkedAt}. No newer tracker time.`
            : `Checked at ${checkedAt}. No tracker time available.`;
    } catch {
      if (dialog.isConnected)
        feedback.textContent = "Could not refresh details. Try again.";
    } finally {
      refresh.disabled = false;
      refresh.textContent = "Refresh details";
    }
  });
  footer.append(feedback, refresh);
  if (hass.user?.is_admin === true) {
    const manage = element("button", null, "Manage member settings");
    manage.type = "button";
    manage.addEventListener("click", () => {
      dialog.close();
      openSettingsDialog(card, card._hass || hass, memberId, (selectedMember) =>
        openMemberDialog(card, card._hass || hass, selectedMember, trigger),
      );
    });
    footer.append(manage);
  }
  footer.append(closeButton);
  dialog.append(style, header, body, footer);
  host.append(dialog);
  card._memberDialog = dialog;
  dialog.addEventListener("close", () => {
    dialog.remove();
    if (card._memberDialog === dialog) card._memberDialog = null;
    if (trigger?.isConnected) trigger.focus({ preventScroll: true });
  });
  dialog.showModal();
  heading.focus({ preventScroll: true });
  body.scrollTop = 0;
  return dialog;
}
