export const categories = ["home", "away", "driving", "unavailable"];
export const labels = {
  home: "Home",
  away: "Away",
  driving: "Driving",
  unavailable: "Unavailable",
  overview: "Everyone",
};
export function visibleMembers(snapshot, hidden = []) {
  return (snapshot?.members || []).filter(
    (member) => !hidden.includes(member.id),
  );
}
export function selection(members, mode, focusIds) {
  const category = ["overview", ...categories].includes(mode);
  const listed = category ? new Set(focusIds?.[mode] || []) : new Set([mode]);
  return members.filter(
    (member) => member.focusable && member.location && listed.has(member.id),
  );
}
export function reportLabel(member, now = Date.now()) {
  if (!member.location) return "No usable map position";
  const proof = member.location.evidence;
  if (!proof?.reported_at) return "Location report time unknown";
  const stamp = Date.parse(proof.reported_at);
  if (!Number.isFinite(stamp) || stamp > now + 60000)
    return "Location report time unknown";
  const minutes = Math.max(0, Math.floor((now - stamp) / 60000));
  const age =
    minutes < 1
      ? "less than a minute"
      : minutes < 60
        ? `${minutes} min`
        : minutes < 1440
          ? `${Math.floor(minutes / 60)} hour${minutes < 120 ? "" : "s"}`
          : `${Math.floor(minutes / 1440)} day${minutes < 2880 ? "" : "s"}`;
  return `${proof.freshness === "stale" ? "Stale · " : ""}Reported ${age} ago`;
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
export function validateConfig(config) {
  if (!config || config.type !== "custom:homecircle-card")
    throw new Error("Use the HomeCircle card type.");
  if (config.map_tiles && !["none", "osm"].includes(config.map_tiles))
    throw new Error("Choose a supported map background.");
  if (
    config.hidden_members &&
    (!Array.isArray(config.hidden_members) ||
      config.hidden_members.some((id) => typeof id !== "string"))
  )
    throw new Error("Hidden members must be a list.");
  return {
    ...config,
    title: String(config.title || "HomeCircle"),
    map_tiles: config.map_tiles || "none",
    hidden_members: config.hidden_members || [],
  };
}
