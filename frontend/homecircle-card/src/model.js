export const categories = ["home", "away", "driving", "unavailable"];
export const labels = {
  home: "Home",
  away: "Away",
  driving: "Driving",
  unavailable: "Unavailable",
  overview: "Everyone",
  items: "Items",
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
  const category = ["overview", "items", ...categories].includes(mode);
  const listed = category ? new Set(focusIds?.[mode] || []) : new Set([mode]);
  return members.filter(
    (member) =>
      member.focusable &&
      member.location &&
      (member.map_visible !== false || mode !== "overview") &&
      listed.has(member.id),
  );
}
// Keep provider-reported text local; do not infer a city from coordinates.
const stateNames = new Set(
  `Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia|Puerto Rico`
    .toLowerCase()
    .split("|"),
);
const stateCodes = new Set(
  "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split(
    " ",
  ),
);
function isState(value) {
  const region = value.replace(/\s+\d{5}(?:-\d{4})?$/, "").trim();
  return (
    stateNames.has(region.toLowerCase()) || stateCodes.has(region.toUpperCase())
  );
}
export function streetCityAddress(value, verifiedCity = null) {
  if (typeof value !== "string") return null;
  const parts = value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  if (typeof verifiedCity === "string" && verifiedCity) {
    if (parts.length === 1 && parts[0] === verifiedCity) return verifiedCity;
    if (parts[1] === verifiedCity) return `${parts[0]}, ${verifiedCity}`;
  }
  const ambiguousCities = new Set(["new york", "washington"]);
  if (
    !parts.length ||
    (isState(parts[0]) && !ambiguousCities.has(parts[0].toLowerCase()))
  )
    return null;
  const street = parts[0];
  let city = parts[1];
  if (
    !city ||
    (isState(city) &&
      !ambiguousCities.has(city.toLowerCase()) &&
      !(parts.length > 2 && isState(parts[2])))
  )
    return street;
  // Some providers combine city and state code in the second component.
  city = city.replace(/\s+\d{5}(?:-\d{4})?$/, "").trim();
  const match = city.match(/^(.*)\s+([A-Z]{2})$/);
  if (match && stateCodes.has(match[2])) city = match[1].trim();
  return city ? `${street}, ${city}` : street;
}
export function addressLabel(member) {
  if (member.place || !member.focusable || !member.location) return null;
  const address = streetCityAddress(
    member.reported_address,
    member.reported_city,
  );
  if (typeof address !== "string" || !address.trim())
    return ["away", "driving"].includes(member.presence)
      ? "Address unavailable"
      : null;
  return member.location.evidence?.freshness === "fresh"
    ? `At ${address}`
    : `Last reported: ${address}`;
}
// HA state transitions describe arrival at a named place, not GPS report freshness.
export function locationSince(member, states = {}, timeZone, now = Date.now()) {
  const unknown = {
    text: "Since unknown",
    title: "No reliable arrival time for this location.",
  };
  if (
    (!member.place &&
      !(member.arrival?.source === "tracker" && member.reported_address)) ||
    !member.focusable ||
    !member.location ||
    member.presence === "driving"
  )
    return unknown;
  let stamp;
  if (member.arrival) {
    stamp =
      typeof member.arrival.since === "string"
        ? Date.parse(member.arrival.since)
        : NaN;
  } else {
    const state = states[member.id];
    const place = member.place.trim().toLowerCase();
    const statePlace =
      typeof state?.state === "string" ? state.state.trim().toLowerCase() : "";
    if (
      !statePlace ||
      ["unknown", "unavailable", "not_home"].includes(statePlace)
    )
      return unknown;
    if (
      !(
        statePlace === place ||
        (statePlace === "home" && member.primary_home === true)
      )
    )
      return unknown;
    if (member.issues?.includes("gps_inside_zone_ha_pending")) return unknown;
    stamp =
      typeof state.last_changed === "string" &&
      /(?:Z|[+-]\d{2}:\d{2})$/.test(state.last_changed)
        ? Date.parse(state.last_changed)
        : NaN;
    if (!Number.isFinite(stamp) || stamp > now) return unknown;
    // Startup re-creates HA states; do not present that timestamp as an arrival.
    const starts = (member.activity?.events || [])
      .filter((event) => event.kind === "started")
      .map((event) => Date.parse(event.observed_at))
      .filter(Number.isFinite);
    const started = starts.length ? Math.max(...starts) : NaN;
    if (!Number.isFinite(started) || stamp <= started + 5000) return unknown;
  }
  if (!Number.isFinite(stamp) || stamp > now) return unknown;

  const options = timeZone ? { timeZone } : {};
  try {
    const day = (value) =>
      new Intl.DateTimeFormat(undefined, {
        ...options,
        year: "numeric",
        month: "numeric",
        day: "numeric",
      }).format(value);
    const sameDay = day(stamp) === day(now);
    const formatted = new Intl.DateTimeFormat(undefined, {
      ...options,
      hour: "numeric",
      minute: "2-digit",
      ...(sameDay ? {} : { month: "short", day: "numeric", year: "numeric" }),
    }).format(stamp);
    return {
      text: `Since ${formatted}`,
      title:
        (member.arrival?.source === "tracker"
          ? "Arrival time reported by the selected tracker."
          : "HomeCircle observed this arrival; detection may follow the actual arrival.") +
        (member.arrival?.continuity_unconfirmed
          ? " Saved across an observation gap; uninterrupted presence is unconfirmed."
          : "") +
        (member.arrival?.persistent === false
          ? " Persistence is unavailable; this time may be lost after restart."
          : ""),
    };
  } catch {
    return unknown;
  }
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

export function batteryStatusLabel(member) {
  const value = {
    full: "Full",
    medium: "Medium",
    low: "Low",
    very_low: "Very Low",
  }[member.battery_status?.value];
  return value ? `${value} (last report)` : "Unknown";
}
