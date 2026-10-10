export const categories = ["home", "away", "driving", "unavailable"];
export const labels = {
  home: "Home",
  away: "Away",
  driving: "Driving",
  unavailable: "Unavailable",
  overview: "Everyone",
};
const providerMessages = {
  selection_needed:
    "trackers are ready; open HomeCircle Options to choose a tracker from this account",
  starting: "connecting to the tracker service",
  discovering: "finding trackers",
  partial:
    "some trackers could not be updated; check HomeCircle Options if this continues",
  auth_required: "sign-in needs attention; open Home Assistant Repairs",
  rate_limited: "temporarily rate limited; HomeCircle will retry",
  network_error: "connection failed; HomeCircle will retry",
  api_error:
    "tracker request failed; check HomeCircle Options if this continues",
  unexpected_response:
    "tracker service response changed; check HomeCircle diagnostics",
};
export function providerAlertText(alert) {
  const message = providerMessages[alert?.state];
  return message && typeof alert.name === "string"
    ? `${alert.name}: ${message}.`
    : null;
}
export function visibleMembers(snapshot, hidden = []) {
  return (snapshot?.members || []).filter(
    (member) => !hidden.includes(member.id),
  );
}
export function selection(members, mode, focusIds) {
  const category = ["overview", ...categories].includes(mode);
  const listed = category ? new Set(focusIds?.[mode] || []) : new Set([mode]);
  return members.filter(
    (member) =>
      member.focusable &&
      member.location &&
      (member.map_visible !== false || mode !== "overview") &&
      listed.has(member.id),
  );
}
export function addressLabel(member) {
  if (member.place || !member.focusable || !member.location) return null;
  const address = member.reported_address;
  if (typeof address !== "string" || !address.trim())
    return ["away", "driving"].includes(member.presence)
      ? "Address unavailable"
      : null;
  return member.location.evidence?.freshness === "fresh"
    ? `At ${address}`
    : `Last reported: ${address}`;
}
function ageLabel(stamp, now) {
  const minutes = Math.max(0, Math.floor((now - stamp) / 60000));
  return minutes < 1
    ? "less than a minute"
    : minutes < 60
      ? `${minutes} min`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)} hour${minutes < 120 ? "" : "s"}`
        : `${Math.floor(minutes / 1440)} day${minutes < 2880 ? "" : "s"}`;
}
export function reportParts(member, now = Date.now()) {
  if (member.issues?.includes("tracker_presence_conflict"))
    return [
      { kind: "unverified", text: "HA Person and selected tracker disagree" },
      { kind: "missing", text: "Map position withheld" },
    ];
  if (!member.location)
    return [{ kind: "missing", text: "No usable map position" }];
  const proof = member.location.evidence;
  const cardSource = proof?.card_source_label ?? proof?.source_label;
  const source =
    typeof cardSource === "string" && cardSource.trim()
      ? [{ kind: "source", text: cardSource }]
      : [];
  const reported = proof?.reported_at ? Date.parse(proof.reported_at) : NaN;
  if (Number.isFinite(reported) && reported <= now + 60000)
    return [
      ...source,
      ...(proof.freshness === "stale"
        ? [{ kind: "stale", text: "Stale report" }]
        : []),
      {
        kind: "reported",
        text: `Location reported ${ageLabel(reported, now)} ago`,
      },
    ];
  const observed = proof?.observed_at ? Date.parse(proof.observed_at) : NaN;
  if (Number.isFinite(observed) && observed <= now + 60000)
    return [
      ...source,
      {
        kind: "observed",
        text: `${member.location.origin === "ha_person" ? "HA Person" : "HA tracker"} updated ${ageLabel(observed, now)} ago`,
      },
    ];
  return [...source, { kind: "unknown", text: "Update time unavailable" }];
}
export function reportLabel(member, now = Date.now()) {
  return reportParts(member, now)
    .map((part) => part.text)
    .join(" · ");
}
// Group screen-overlapping markers, independently for each map and zoom level.
export function markerGroups(members, project, distance = 42) {
  const groups = [];
  for (const member of members) {
    const point = project(member.location);
    const group = groups.find(
      (item) =>
        Math.hypot(item.point.x - point.x, item.point.y - point.y) < distance,
    );
    if (group) group.members.push(member);
    else groups.push({ point, members: [member] });
  }
  return groups;
}
// Keep positive space for Leaflet's fit calculation even in a narrow card.
export function pinFitPadding(size) {
  const scale = Math.max(
    0,
    Math.min(1, (size.x - 24) / 160, (size.y - 24) / 168),
  );
  return {
    paddingTopLeft: [Math.floor(112 * scale), Math.floor(120 * scale)],
    paddingBottomRight: [Math.floor(48 * scale), Math.floor(48 * scale)],
  };
}
export function validateConfig(config) {
  if (!config || config.type !== "custom:homecircle-card")
    throw new Error("Use the HomeCircle card type.");
  if (
    config.map_tiles &&
    !["none", "osm", "satellite"].includes(config.map_tiles)
  )
    throw new Error("Choose a supported map background.");
  if (
    config.hidden_members &&
    (!Array.isArray(config.hidden_members) ||
      config.hidden_members.some((id) => typeof id !== "string"))
  )
    throw new Error("Hidden members must be a list.");
  if (
    config.fill_screen !== undefined &&
    typeof config.fill_screen !== "boolean"
  )
    throw new Error("Fill screen must be on or off.");
  return {
    ...config,
    title: String(config.title || "HomeCircle"),
    map_tiles: config.map_tiles || "osm",
    fill_screen: config.fill_screen || false,
    hidden_members: config.hidden_members || [],
  };
}
