import * as L from "leaflet";
import { observedFrames, forecastFrames, frameTime } from "./weather-frames.js";
const LATEST_RADAR_URL =
  "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png";

// Only public tile coordinates are sent to IEM; no household metadata is used.
export class RadarOverlay {
  constructor(card, wrap, footer) {
    this.card = card;
    this.enabled = false;
    this.opacity = 0.4;
    this.showControls = false;
    try {
      this.showControls =
        window.localStorage.getItem(this.preferenceKey()) === "true";
    } catch {
      /* Display preferences are optional when browser storage is blocked. */
    }
    this.controls = document.createElement("div");
    this.controls.className = "radar-controls";
    this.toggle = document.createElement("button");
    this.toggle.type = "button";
    this.toggle.textContent = "Radar";
    this.toggle.title =
      "U.S. weather radar from Iowa Environmental Mesonet. Enabling sends viewed map areas to IEM.";
    this.toggle.onclick = () => {
      if (card._config.map_tiles === "none") return;
      this.enabled = !this.enabled;
      this.sync();
    };
    this.options = document.createElement("div");
    this.options.className = "radar-options";
    const label = document.createElement("label");
    label.textContent = "Opacity ";
    this.range = document.createElement("input");
    this.range.type = "range";
    this.range.min = "10";
    this.range.max = "100";
    this.range.value = String(this.opacity * 100);
    this.range.setAttribute("aria-label", "Radar opacity");
    this.value = document.createElement("output");
    this.value.textContent = `${this.range.value}%`;
    this.range.oninput = () => {
      this.opacity = Number(this.range.value) / 100;
      this.value.textContent = `${this.range.value}%`;
      this.layer?.setOpacity(this.currentFrame ? 0 : this.opacity);
      for (const frame of this.frames || [])
        frame.layer.setOpacity(frame === this.currentFrame ? this.opacity : 0);
    };
    label.append(this.range, this.value);
    const legend = document.createElement("div");
    legend.className = "radar-legend";
    legend.textContent = "Weak echoes → Strong echoes";
    this.options.append(label, legend);
    this.controls.append(this.options);
    card._mapControls.insertBefore(this.toggle, card._satelliteButton);
    this.note = document.createElement("div");
    this.note.className = "radar-note";
    this.note.setAttribute("role", "status");
    this.playback = document.createElement("div");
    this.playback.className = "radar-playback";
    this.play = document.createElement("button");
    this.play.type = "button";
    this.play.onclick = () =>
      this.playing ? this.stopPlayback() : this.startPlayback();
    this.frameLabel = document.createElement("span");
    this.timeline = document.createElement("select");
    this.timeline.setAttribute("aria-label", "Radar time range");
    for (const [value, text] of [
      ["past", "Past 30 min"],
      ["future", "Future 2 hr"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      this.timeline.append(option);
    }
    this.timeline.onchange = async () => {
      this.stopPlayback();
      if (this.timeline.value === "future") {
        if (!this.forecast) await this.loadMetadata();
        if (this.enabled && this.timeline.value === "future")
          this.startPlayback();
      }
    };
    this.playback.append(this.play, this.timeline, this.frameLabel);
    footer.append(this.playback, this.note);
    this.resetPlaybackControls();
    wrap.append(this.controls);
    this.sync();
  }
  sync() {
    const map = this.card._map;
    const privateMap = this.card._config.map_tiles === "none";
    if (privateMap) this.enabled = false;
    this.controls.hidden = privateMap;
    this.toggle.setAttribute("aria-pressed", String(this.enabled));
    this.options.hidden = !this.enabled || !this.showControls;
    this.note.hidden = this.playback.hidden = !this.enabled;
    if (!this.enabled || !map) {
      this.removeLayer();
      return;
    }
    if (this.layer) return;
    if (!map.getPane("homecircle-radar")) {
      const pane = map.createPane("homecircle-radar");
      pane.style.zIndex = "350";
      pane.style.pointerEvents = "none";
    }
    this.observed = this.forecast = this.forecastMetadata = null;
    this.metadataAt = null;
    this.resetPlaybackControls();
    const layer = L.tileLayer(LATEST_RADAR_URL, {
      pane: "homecircle-radar",
      maxNativeZoom: 12,
      maxZoom: 19,
      opacity: this.opacity,
      attribution:
        'Radar: <a href="https://mesonet.agron.iastate.edu/" target="_blank" rel="noopener">Iowa Environmental Mesonet / NEXRAD</a>',
      referrerPolicy: "no-referrer",
    });
    this.layer = layer;
    this.failed = false;
    this.note.textContent = "Loading U.S. radar…";
    layer.on("loading", () => {
      if (this.layer === layer) this.failed = false;
    });
    layer.on("tileerror", () => {
      if (this.layer !== layer) return;
      this.failed = true;
      this.note.textContent =
        "Some radar tiles unavailable. Map and people still work.";
    });
    layer.on("load", () => {
      if (this.layer !== layer || this.failed || this.playing) return;
      this.showObservedStatus();
      this.note.title =
        "Radar can be delayed. Transparent areas may mean no echoes or missing coverage. Observed times describe the mosaic, not each individual radar scan. Forecast times describe HRRR predictions.";
    });
    layer.addTo(map);
    this.loadMetadata();
    this.onResume = () => {
      if (!document.hidden && this.enabled && this.card.isConnected) {
        this.stopPlayback();
        this.loadMetadata();
        layer.redraw();
      }
    };
    document.addEventListener("visibilitychange", this.onResume);
    this.timer = setInterval(() => {
      if (this.card.isConnected && !document.hidden) {
        this.stopPlayback();
        layer.redraw();
        this.loadMetadata();
      }
    }, 300000);
  }
  resetPlaybackControls() {
    this.play.textContent = "▶";
    this.play.setAttribute("aria-label", "Animate radar");
    this.play.title = "Play the selected observed or forecast radar frames";
    this.play.setAttribute("aria-pressed", "false");
    this.frameLabel.textContent = frameTime(this.observed?.at(-1));
  }
  showObservedStatus() {
    this.note.textContent = this.observed
      ? "Observed U.S. radar · updates about every 5 min · imagery can be delayed"
      : "Observed U.S. radar · time unavailable · imagery may be delayed";
  }
  useUntimedRadar() {
    this.observed = null;
    if (!this.playing && this.layer) {
      this.layer.setUrl(LATEST_RADAR_URL);
      this.resetPlaybackControls();
      this.showObservedStatus();
    }
  }
  async loadMetadata() {
    this.metadataAbort?.abort();
    const controller = new AbortController();
    this.metadataAbort = controller;
    const timeout = setTimeout(() => {
      controller.abort();
      if (this.metadataAbort === controller && this.enabled && this.layer) {
        this.forecast = this.forecastMetadata = null;
        this.metadataAt = null;
        this.useUntimedRadar();
      }
    }, 10000);
    const options = {
      signal: controller.signal,
      referrerPolicy: "no-referrer",
      credentials: "omit",
    };
    const get = async (url) => {
      const response = await window.fetch(url, options);
      if (!response.ok) throw new Error("Weather metadata unavailable");
      return response.json();
    };
    try {
      const results = await Promise.allSettled([
        get(
          "https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.json",
        ),
        get(
          "https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_1080.json",
        ),
      ]);
      if (
        controller.signal.aborted ||
        this.metadataAbort !== controller ||
        !this.enabled ||
        !this.layer
      )
        return;
      if (results[0].status === "fulfilled") {
        try {
          this.observed = observedFrames(results[0].value);
        } catch {
          this.observed = null;
        }
      } else this.observed = null;
      if (results[1].status === "fulfilled") {
        try {
          this.forecast = forecastFrames(results[1].value);
          this.forecastMetadata = results[1].value;
        } catch {
          this.forecast = this.forecastMetadata = null;
        }
      } else this.forecast = this.forecastMetadata = null;
      this.metadataAt = Date.now();
      if (!this.playing && this.observed) {
        this.layer.setUrl(this.observed.at(-1).url);
        this.resetPlaybackControls();
        this.showObservedStatus();
      } else if (!this.observed) this.useUntimedRadar();
    } finally {
      clearTimeout(timeout);
      if (this.metadataAbort === controller) this.metadataAbort = null;
    }
  }
  async startPlayback() {
    if (!this.enabled || !this.layer || this.playing || document.hidden) return;
    if (this.metadataAt && Date.now() - this.metadataAt >= 300000) {
      const token = (this.playToken = (this.playToken || 0) + 1);
      const layer = this.layer,
        range = this.timeline.value;
      await this.loadMetadata();
      if (
        token !== this.playToken ||
        this.layer !== layer ||
        !this.enabled ||
        document.hidden ||
        this.timeline.value !== range
      )
        return;
    }
    if (this.timeline.value === "future" && this.forecastMetadata) {
      try {
        this.forecast = forecastFrames(this.forecastMetadata);
      } catch {
        this.forecast = null;
      }
    }
    const definitions =
      this.timeline.value === "future" ? this.forecast : this.observed;
    if (!definitions?.length) {
      this.note.textContent =
        this.timeline.value === "future"
          ? "Forecast unavailable. Showing latest observed radar."
          : "Radar times unavailable. Try again shortly.";
      return;
    }
    this.playing = true;
    this.frames = [];
    this.currentFrame = null;
    this.waitingSince = Date.now();
    this.play.textContent = "Ⅱ";
    this.play.setAttribute("aria-label", "Pause radar animation");
    this.play.title = "Pause and return to latest radar";
    this.play.setAttribute("aria-pressed", "true");
    this.frameLabel.textContent = "Loading animation…";
    // Keep latest imagery visible until the first historical frame is ready.
    for (const definition of definitions) {
      const layer = L.tileLayer(definition.url, {
        ...this.layer.options,
        opacity: 0,
      });
      const frame = { ...definition, layer, ready: false, failed: false };
      this.frames.push(frame);
      layer.on("loading", () => {
        frame.ready = frame.failed = false;
      });
      layer.on("tileerror", () => {
        frame.failed = true;
      });
      layer.on("load", () => {
        frame.ready = !frame.failed;
      });
      layer.addTo(this.card._map);
    }
    this.onMapMove = () => this.stopPlayback();
    this.onVisibility = () => {
      if (document.hidden) this.stopPlayback();
    };
    this.card._map.on("movestart", this.onMapMove);
    document.addEventListener("visibilitychange", this.onVisibility);
    this.animationTimer = setInterval(() => this.advanceFrame(), 900);
  }
  advanceFrame() {
    if (!this.playing) return;
    if (!this.card.isConnected || document.hidden) {
      this.stopPlayback();
      return;
    }
    if (this.frames.some((frame) => frame.failed)) {
      this.stopPlayback();
      this.note.textContent =
        "Animation unavailable. Showing latest available radar.";
      return;
    }
    const index = this.currentFrame
      ? this.frames.indexOf(this.currentFrame)
      : -1;
    const next = this.frames[(index + 1) % this.frames.length];
    if (!next.ready) {
      if (Date.now() - this.waitingSince > 20000) {
        this.stopPlayback();
        this.note.textContent =
          "Animation timed out. Showing latest observed radar.";
      }
      return;
    }
    this.waitingSince = Date.now();
    this.layer.setOpacity(0);
    this.currentFrame?.layer.setOpacity(0);
    next.layer.setOpacity(this.opacity);
    this.currentFrame = next;
    this.frameLabel.textContent = frameTime(next);
    this.note.textContent =
      next.kind === "Forecast"
        ? `HRRR prediction · model run ${frameTime({ kind: "", time: next.init }).replace(/^ · /, "")} · not observed radar`
        : "Observed radar · 5-minute steps · radar can be delayed";
  }
  stopPlayback() {
    this.playToken = (this.playToken || 0) + 1;
    clearInterval(this.animationTimer);
    this.animationTimer = null;
    if (this.onMapMove) this.card._map?.off("movestart", this.onMapMove);
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.onMapMove = this.onVisibility = null;
    for (const frame of this.frames || []) {
      frame.layer.remove();
      frame.layer.off();
    }
    this.frames = [];
    this.currentFrame = null;
    const wasPlaying = this.playing;
    this.playing = false;
    this.layer?.setOpacity(this.opacity);
    this.resetPlaybackControls();
    if (wasPlaying && !this.failed) this.showObservedStatus();
  }
  preferenceKey() {
    return `${this.card._mapPreferenceKey()}:radar-controls`;
  }
  setShowControls(show) {
    this.showControls = Boolean(show);
    try {
      window.localStorage.setItem(
        this.preferenceKey(),
        String(this.showControls),
      );
    } catch {
      /* The controls still work for this visit when storage is blocked. */
    }
    this.sync();
  }
  removeLayer() {
    this.metadataAbort?.abort();
    this.metadataAbort = null;
    document.removeEventListener("visibilitychange", this.onResume);
    this.onResume = null;
    this.stopPlayback();
    this.observed = this.forecast = this.forecastMetadata = null;
    this.metadataAt = null;
    this.resetPlaybackControls();
    clearInterval(this.timer);
    this.timer = null;
    if (this.layer) {
      // Leaflet removes its map listeners through the layer remove event.
      this.layer.remove();
      this.layer.off();
      this.layer = null;
    }
  }
  dispose() {
    this.enabled = false;
    this.removeLayer();
    this.toggle.setAttribute("aria-pressed", "false");
    this.options.hidden = this.note.hidden = this.playback.hidden = true;
  }
}
