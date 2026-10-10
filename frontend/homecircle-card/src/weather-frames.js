const MINUTE = 60000;
export const radarUrl = (name) =>
  `https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/${name}/{z}/{x}/{y}.png`;
const stamp = (time) =>
  new Date(time).toISOString().replace(/[-:T]/g, "").slice(0, 12);
export function observedFrames(metadata) {
  const time = Date.parse(metadata?.meta?.valid);
  if (!Number.isFinite(time)) throw new Error("Radar time unavailable");
  return [30, 25, 20, 15, 10, 5, 0].map((minutes) => ({
    minutes,
    time: time - minutes * MINUTE,
    kind: "Observed",
    url: radarUrl(`ridge::USCOMP-N0Q-${stamp(time - minutes * MINUTE)}`),
  }));
}
export function forecastFrames(metadata, now = Date.now()) {
  const init = Date.parse(metadata?.model_init_utc);
  if (!Number.isFinite(init) || init > now || now - init > 18 * 60 * MINUTE)
    throw new Error("Forecast time unavailable");
  const first = Math.floor((now - init) / (15 * MINUTE)) * 15 + 15;
  const frames = [];
  for (let lead = first; lead <= Math.min(first + 120, 1080); lead += 15)
    frames.push({
      minutes: lead,
      time: init + lead * MINUTE,
      kind: "Forecast",
      init,
      url: radarUrl(
        `hrrr::REFD-F${String(lead).padStart(4, "0")}-${stamp(init)}`,
      ),
    });
  if (!frames.length) throw new Error("Forecast expired");
  return frames;
}
export function frameTime(frame) {
  if (!frame?.time) return "Observed · time unavailable";
  return `${frame.kind} · ${new Date(frame.time).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  })}`;
}
