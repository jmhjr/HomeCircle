import * as L from "leaflet";
import leafletCSS from "leaflet/dist/leaflet.css";
import css from "./style.css";
import integrationManifest from "../../../custom_components/homecircle/manifest.json";
import { openSettingsDialog } from "./settings-dialog.js";
import { openMemberDialog } from "./member-dialog.js";
import { RadarOverlay } from "./radar.js";
import {
  categories,
  labels,
  visibleMembers,
  selection,
  reportParts,
  addressLabel,
  markerGroups,
  pinFitPadding,
  validateConfig,
  providerAlertText,
} from "./model.js";

const releaseTitle = "HomeCircle";
const displayedTitle = (title) =>
  title === "HomeCircle" || /^HomeCircle - Beta \d+$/.test(title)
    ? releaseTitle
    : title;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, action, className) {
  const node = el("button", className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function initials(name) {
  return name
    .split(/\s+/)
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
function allowedPicture(value) {
  if (typeof value !== "string" || /[\x00-\x1f\\]/.test(value)) return false;
  if (value.includes("/../") || /%2e/i.test(value)) return false;
  if (value.startsWith("/api/image/serve/") || value.startsWith("/local/"))
    return true;
  try {
    const url = new URL(value);
    const path = decodeURIComponent(url.pathname);
    if (path.split("/").some((part) => part === "." || part === ".."))
      return false;
    const life360Image =
      (url.host === "www.life360.com" &&
        path.startsWith("/img/user_images/")) ||
      (url.host === "life360-images-pub.life360.com" &&
        /\.(jpeg|jpg|png|webp)$/.test(path));
    return url.protocol === "https:" && life360Image && !url.hash;
  } catch {
    return false;
  }
}
function memberAvatar(member, className = "marker-avatar") {
  const avatar = el("span", className, initials(member.name));
  avatar.setAttribute("aria-hidden", "true");
  if (allowedPicture(member.picture)) {
    const picture = el("img");
    picture.alt = "";
    picture.referrerPolicy = "no-referrer";
    picture.src = member.picture;
    picture.addEventListener("error", () => picture.remove(), { once: true });
    avatar.append(picture);
  }
  return avatar;
}

class HomeCircleCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mode = "overview";
    this._generation = 0;
    this._refreshToken = 0;
    this._integrationVersion = integrationManifest.version;
  }
  static getConfigElement() {
    return document.createElement("homecircle-card-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:homecircle-card",
      title: releaseTitle,
      map_tiles: "osm",
    };
  }
  getCardSize() {
    return 8;
  }
  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }
  setConfig(config) {
    const old = this._config;
    this._config = validateConfig(config);
    this.toggleAttribute("fill-screen", this._config.fill_screen);
    if (!this._config.fill_screen) this._setKiosk(false);
    if (
      old?.map_tiles !== this._config.map_tiles ||
      old?.title !== this._config.title
    ) {
      this._mapBackground = this._config.map_tiles;
      if (this._config.map_tiles !== "none") {
        try {
          const saved = window.localStorage.getItem(this._mapPreferenceKey());
          if (["osm", "satellite"].includes(saved)) this._mapBackground = saved;
        } catch {
          /* Storage can be unavailable on shared displays. */
        }
      }
      this._destroyMap();
    }
    if (!old || old.title !== this._config.title) {
      this._mapHeight = null;
      try {
        const saved = Number(
          window.localStorage.getItem(this._heightPreferenceKey()),
        );
        if (Number.isFinite(saved) && saved >= 220) this._mapHeight = saved;
      } catch {
        /* Browser storage is optional. */
      }
    }
    this._applyMapHeight();
    this._syncMapControls();
    this._cancelSelectionRefresh();
    this._mode = "overview";
    this._fit = true;
    if (this.isConnected) {
      this._layout();
      this._fitScreen();
      this._render();
      this._load();
    }
  }
  set hass(hass) {
    const changed = this._hass?.connection !== hass.connection;
    const reconnected =
      this._hass?.connected === false && hass.connected !== false;
    const sameUser =
      this._hass?.user?.id && this._hass.user.id === hass.user?.id;
    this._hass = hass;
    this._syncSettingsVisibility();
    if (changed) {
      clearTimeout(this._timeout);
      this._generation++;
      this._busy = false;
      if (sameUser && this._data)
        this._temporaryFailure(
          "Reconnecting to Home Assistant… Showing last received locations.",
        );
      else this._clear("Connecting to Home Assistant…");
    }
    if (hass.connected === false) {
      clearTimeout(this._timeout);
      this._generation++;
      this._busy = false;
      this._temporaryFailure(
        "Home Assistant is disconnected. Showing last received locations.",
      );
      return;
    }
    if (this.isConnected && (changed || reconnected)) this._load();
  }
  connectedCallback() {
    this._layout();
    if (
      this._config?.fill_screen &&
      new URLSearchParams(window.location.search).get("homecircle_kiosk") ===
        "1"
    )
      this._setKiosk(true);
    this._onWindowResize ||= () => this._fitScreen();
    window.addEventListener("resize", this._onWindowResize);
    this._fitScreen();
    this._render();
    this._load();
    clearInterval(this._timer);
    this._timer = setInterval(() => this._load(), 15000);
  }
  disconnectedCallback() {
    this._finishMapResize(false);
    this._cancelSelectionRefresh();
    this._memberDialog?.close();
    this._setKiosk(false);
    window.removeEventListener("resize", this._onWindowResize);
    clearInterval(this._timer);
    clearTimeout(this._retry);
    clearTimeout(this._timeout);
    this._generation++;
    this._busy = false;
    this._data = null;
    this._signature = null;
    this._mode = "overview";
    this._destroyMap();
    this.shadowRoot.replaceChildren();
    this._shell = null;
  }
  _fitScreen() {
    this._applyMapHeight();
    if (!this._config?.fill_screen || !this.isConnected) return;
    const available = Math.max(
      480,
      Math.round(
        window.innerHeight -
          (this._kioskEnabled ? 0 : this.getBoundingClientRect().top + 8),
      ),
    );
    this.style.setProperty("--homecircle-screen-height", `${available}px`);
    this._map?.invalidateSize({ pan: false });
  }
  _setKiosk(enabled) {
    if (Boolean(this._kioskEnabled) === enabled) return;
    this._kioskEnabled = enabled;
    this.toggleAttribute("kiosk", enabled);
    this._syncKioskChrome(enabled);
    window.dispatchEvent(
      new CustomEvent("hass-kiosk-mode", { detail: { enable: enabled } }),
    );
    this._syncKioskButton();
    requestAnimationFrame(() => requestAnimationFrame(() => this._fitScreen()));
  }
  _syncKioskButton() {
    if (!this._kioskButton) return;
    const enabled = Boolean(this._kioskEnabled);
    const label = enabled ? "Exit kiosk view" : "Enter kiosk view";
    this._kioskButton.setAttribute("aria-label", label);
    this._kioskButton.title = label;
    this._kioskButton.setAttribute("aria-pressed", String(enabled));
    this._kioskIcon.setAttribute(
      "icon",
      enabled ? "mdi:fullscreen-exit" : "mdi:fullscreen",
    );
  }
  _syncKioskChrome(enabled) {
    this._kioskChromeStyle?.remove();
    this._kioskChromeStyle = null;
    if (!enabled) return;
    const root = document
      .querySelector("home-assistant")
      ?.shadowRoot?.querySelector("home-assistant-main")
      ?.shadowRoot?.querySelector("ha-panel-lovelace")
      ?.shadowRoot?.querySelector("hui-root")?.shadowRoot;
    if (!root) return;
    const style = document.createElement("style");
    style.textContent =
      ".header { display: none !important; } hui-view-container { padding-top: 0 !important; }";
    root.append(style);
    this._kioskChromeStyle = style;
  }
  _toggleKiosk() {
    const enabled = !this._kioskEnabled;
    const url = new URL(window.location.href);
    if (enabled) url.searchParams.set("homecircle_kiosk", "1");
    else url.searchParams.delete("homecircle_kiosk");
    window.history.replaceState(window.history.state, "", url);
    this._setKiosk(enabled);
  }
  _syncSettingsVisibility() {
    if (this._settingsButton)
      this._settingsButton.hidden = this._hass?.user?.is_admin !== true;
  }
  _openSettings() {
    if (this._hass?.user?.is_admin === true)
      openSettingsDialog(this, this._hass);
  }
  _layout() {
    if (this._shell || !this._config) return;
    const style = el("style");
    style.textContent = leafletCSS + css;
    this._shell = el("ha-card");
    const header = el("header"),
      brand = el("div");
    brand.append(el("div", "eyebrow", "HOME · TOGETHER"));
    this._title = el("h2");
    brand.append(this._title);
    this._overview = button(
      "Everyone ↗",
      () => this._choose("overview"),
      "overview",
    );
    const actions = el("div", "header-actions");
    this._kioskButton = button("", () => this._toggleKiosk(), "kiosk-toggle");
    this._kioskIcon = el("ha-icon");
    this._kioskIcon.setAttribute("aria-hidden", "true");
    this._kioskButton.append(this._kioskIcon);
    this._syncKioskButton();
    this._settingsButton = button(
      "",
      () => this._openSettings(),
      "settings-toggle",
    );
    const settingsIcon = el("ha-icon");
    settingsIcon.setAttribute("icon", "mdi:cog");
    settingsIcon.setAttribute("aria-hidden", "true");
    this._settingsButton.append(settingsIcon);
    this._settingsButton.setAttribute("aria-label", "HomeCircle settings");
    this._settingsButton.title = "HomeCircle settings";
    this._syncSettingsVisibility();
    actions.append(this._kioskButton, this._settingsButton, this._overview);
    header.append(brand, actions);
    this._status = el("div", "status");
    this._status.setAttribute("role", "status");
    this._status.setAttribute("aria-live", "polite");
    this._locationFeedback = el("div", "location-feedback");
    this._locationFeedback.setAttribute("role", "status");
    this._locationFeedback.setAttribute("aria-live", "polite");
    this._providerAlerts = el("div", "provider-alerts");
    const wrap = el("div", "map-wrap");
    this._mapNode = el("div", "map");
    this._mapNode.setAttribute("aria-label", "Household locations");
    this._mapNote = el("div", "map-note");
    const footer = el("div", "map-footer");
    this._mapControls = el("div", "map-controls");
    this._mapControls.setAttribute("role", "group");
    this._mapControls.setAttribute("aria-label", "Map view");
    this._streetButton = button("Street", () => this._setMapBackground("osm"));
    this._satelliteButton = button("Satellite", () =>
      this._setMapBackground("satellite"),
    );
    this._satelliteButton.title =
      "USGS imagery · detailed coverage in the U.S.";
    this._mapControls.append(this._streetButton, this._satelliteButton);
    this._syncMapControls();
    footer.append(this._mapNote);
    this._mapWrap = wrap;
    this._resizeHandle = el("div", "map-resize");
    this._resizeHandle.tabIndex = 0;
    this._resizeHandle.setAttribute("role", "separator");
    this._resizeHandle.setAttribute("aria-orientation", "horizontal");
    this._resizeHandle.setAttribute("aria-label", "Resize map height");
    this._resizeHandle.title =
      "Drag to resize map. Arrow keys adjust height; Home resets.";
    this._resizeHandle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || this._mapDrag) return;
      event.preventDefault();
      this._resizeHandle.focus({ preventScroll: true });
      this._mapDrag = {
        id: event.pointerId,
        y: event.clientY,
        height: this._mapNode.getBoundingClientRect().height,
        previous: this._mapHeight,
      };
      this._resizeHandle.setPointerCapture?.(event.pointerId);
    });
    this._resizeHandle.addEventListener("pointermove", (event) => {
      if (this._mapDrag?.id !== event.pointerId) return;
      this._mapHeight = this._mapDrag.height + event.clientY - this._mapDrag.y;
      this._applyMapHeight();
    });
    this._resizeHandle.addEventListener("pointerup", (event) => {
      if (this._mapDrag?.id === event.pointerId) this._finishMapResize(true);
    });
    this._resizeHandle.addEventListener("pointercancel", () =>
      this._finishMapResize(false),
    );
    this._resizeHandle.addEventListener("lostpointercapture", () =>
      this._finishMapResize(true),
    );
    this._resizeHandle.addEventListener("keydown", (event) => {
      if (!["ArrowUp", "ArrowDown", "Home"].includes(event.key)) return;
      event.preventDefault();
      this._mapHeight =
        event.key === "Home"
          ? null
          : (this._mapHeight ?? this._mapNode.getBoundingClientRect().height) +
            (event.key === "ArrowDown" ? 20 : -20);
      this._applyMapHeight();
      this._saveMapHeight();
    });
    wrap.append(this._mapNode, this._mapControls, footer, this._resizeHandle);
    this._radarController = new RadarOverlay(this, wrap, footer);
    this._applyMapHeight();
    this._expanded = el("div", "expanded");
    this._categories = el("div", "categories");
    this._members = el("div", "members");
    this._familyBar = el("div", "family-refresh");
    this._familyButton = button(
      "Refresh family locations",
      () => this._refreshFamily(),
      "family-refresh-button",
    );
    this._familyButton.title =
      "Requests reports from all selected Life360 family members. Once every minute; up to 50 requests per rolling 24 hours.";
    this._familyFeedback = el("div", "family-refresh-feedback");
    this._familyFeedback.setAttribute("role", "status");
    this._familyFeedback.setAttribute("aria-live", "polite");
    this._familyBar.append(this._familyButton, this._familyFeedback);
    this._shell.append(
      header,
      this._status,
      this._locationFeedback,
      this._familyBar,
      this._providerAlerts,
      wrap,
      this._expanded,
      this._categories,
      this._members,
    );
    this.shadowRoot.append(style, this._shell);
  }
  async _load() {
    if (
      !this._hass ||
      !this._config ||
      !this.isConnected ||
      this._busy ||
      this._hass.connected === false
    )
      return;
    this._busy = true;
    const generation = ++this._generation;
    this._timeout = setTimeout(() => {
      if (generation === this._generation) {
        this._generation++;
        this._busy = false;
        this._temporaryFailure(
          "Connection timed out. Showing last received locations; retrying…",
        );
      }
    }, 10000);
    try {
      const data = await this._hass.callWS({ type: "homecircle/snapshot" });
      if (generation !== this._generation || !this.isConnected) return;
      if (data.schema_version !== 1)
        throw new Error("Unsupported household data version.");
      const first = !this._data;
      const signature = JSON.stringify(data) + Math.floor(Date.now() / 60000);
      this._data = data;
      const recovering = Boolean(this._error);
      this._error = null;
      clearTimeout(this._retry);
      if (first) this._fit = true;
      if (first || recovering || signature !== this._signature) this._render();
      this._signature = signature;
    } catch (error) {
      if (generation === this._generation) {
        if (
          error.code === "unauthorized" ||
          error.message === "Unsupported household data version."
        )
          this._clear(
            error.code === "unauthorized"
              ? "This HA user cannot view all selected household sources."
              : error.message,
          );
        else
          this._temporaryFailure(
            error.code === "not_ready"
              ? "HomeCircle is starting… Showing last received locations; retrying…"
              : "Connection interrupted. Showing last received locations; retrying…",
          );
      }
    } finally {
      if (generation === this._generation) {
        clearTimeout(this._timeout);
        this._busy = false;
      }
    }
  }
  _temporaryFailure(message) {
    this._error = message;
    this._render();
    clearTimeout(this._retry);
    if (this.isConnected && this._hass?.connected !== false)
      this._retry = setTimeout(() => this._load(), 2000);
  }
  _clear(message) {
    clearTimeout(this._retry);
    this._cancelSelectionRefresh();
    this._memberDialog?.close();
    this._data = null;
    this._signature = null;
    this._mode = "overview";
    this._error = message;
    this._destroyMap();
    this._render();
  }
  _choose(mode) {
    if (this._mode === mode && this._selectionRefresh?.status === "checking")
      return;
    this._cancelSelectionRefresh();
    this._expandedIds = null;
    this._mode = mode;
    this._expanded?.replaceChildren();
    this._fit = true;
    this._render();
    this._refreshSelectedLocation(mode);
  }
  _cancelSelectionRefresh() {
    this._refreshToken++;
    clearTimeout(this._selectionTimeout);
    this._selectionRefresh = null;
    if (this._locationFeedback) this._locationFeedback.textContent = "";
  }
  async _refreshSelectedLocation(id) {
    const member = this._data?.members.find((item) => item.id === id);
    if (
      !member ||
      member.location?.evidence?.freshness !== "stale" ||
      !this.isConnected ||
      this._hass?.connected === false
    )
      return;
    const token = ++this._refreshToken;
    const evidence = member.location.evidence;
    this._selectionRefresh = {
      id,
      status: "checking",
      reportedAt: evidence.reported_at,
      source: evidence.source_label,
      started: Date.now(),
    };
    this._updateLocationFeedback();
    let timeout;
    try {
      const result = await Promise.race([
        this._hass.callWS({
          type: "homecircle/refresh_location",
          member_id: id,
        }),
        new Promise((_, reject) => {
          timeout = this._selectionTimeout = setTimeout(
            () => reject(new Error("Check timed out")),
            15000,
          );
        }),
      ]);
      clearTimeout(timeout);
      if (
        token !== this._refreshToken ||
        this._mode !== id ||
        !this.isConnected
      )
        return;
      this._selectionRefresh.status = result.status;
      await this._load();
    } catch {
      clearTimeout(timeout);
      if (
        token !== this._refreshToken ||
        this._mode !== id ||
        !this.isConnected
      )
        return;
      this._selectionRefresh.status = "unavailable";
    }
    this._updateLocationFeedback();
  }
  _updateLocationFeedback() {
    if (!this._locationFeedback) return;
    const request = this._selectionRefresh;
    const member =
      request && this._data?.members.find((item) => item.id === request.id);
    if (!request || this._mode !== request.id || !member) {
      this._locationFeedback.textContent = "";
      return;
    }
    const evidence = member.location?.evidence;
    const newer =
      evidence?.source_label === request.source &&
      request.reportedAt &&
      Date.parse(evidence?.reported_at) > Date.parse(request.reportedAt);
    if (newer) {
      this._locationFeedback.textContent =
        evidence.freshness === "stale"
          ? "Newer report received; it is still stale."
          : "Newer location report received.";
      return;
    }
    this._locationFeedback.textContent =
      {
        checking: "Checking for a newer location report…",
        requested:
          Date.now() - request.started < 60000
            ? "Location update requested. Waiting for a newer report…"
            : "No newer location report received yet.",
        checked: "Checked cloud reports. No newer location report available.",
        cooldown:
          "A recent location check is on cooldown. No new request sent.",
        busy: "A location check is already in progress.",
        limited: "Location request limit reached. No new request sent.",
        disabled: "Phone location requests are off for this member.",
        not_allowed: "This HA user cannot request a location update.",
        unsupported:
          "This tracker does not support requesting a location update.",
        no_position: "No usable selected tracker position to refresh.",
        fresh: "The selected tracker report is already fresh.",
        send_failed: "Home Assistant could not send the location request.",
        unavailable: "Location refresh is temporarily unavailable.",
      }[request.status] || "Location refresh is temporarily unavailable.";
  }
  _openMemberDetails(memberId, trigger) {
    openMemberDialog(this, this._hass, memberId, trigger);
  }
  _chooseFromMap(id, event) {
    this._choose(id);
    [...this._members.querySelectorAll("[data-focus]")]
      .find((node) => node.dataset.focus === id)
      ?.focus(event?.detail ? { preventScroll: true } : undefined);
  }
  async _refreshFamily() {
    if (
      this._familyBusy ||
      !this._data?.family_refresh?.available ||
      this._hass?.connected === false
    )
      return;
    const connection = this._hass.connection;
    this._familyBusy = true;
    this._familyMessageUntil = null;
    this._familyMessage = "Sending family refresh request…";
    this._updateFamilyFeedback();
    try {
      const result = await this._hass.callWS({
        type: "homecircle/refresh_family",
      });
      if (!this.isConnected || connection !== this._hass.connection) return;
      this._familyMessage =
        {
          requested: "Request accepted. Watching for newer reports…",
          cooldown: "Family refresh is resting between requests.",
          limited: "The family refresh limit has been reached.",
          not_allowed:
            "You do not have permission to refresh every family member.",
          unsupported:
            "Family refresh is unavailable for the current tracker selection.",
          send_failed: "The family request failed. No refresh is confirmed.",
          unavailable: "Family refresh is temporarily unavailable.",
        }[result.status] || "Family refresh is temporarily unavailable.";
      this._familyRetryAt = result.retry_at || null;
      if (result.retry_at)
        this._familyMessage += ` Next available ${this._familyRetryLabel(result.retry_at)}.`;
      if (result.status === "requested") this._familyMessage = "";
      this._signature = null;
      this._load();
    } catch {
      if (this.isConnected && connection === this._hass.connection)
        this._familyMessage = "Family refresh is temporarily unavailable.";
    } finally {
      this._familyMessageUntil = Date.now() + 5 * 60_000;
      this._familyBusy = false;
      this._updateFamilyFeedback();
    }
  }
  _familyRetryLabel(stamp) {
    return new Date(stamp).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  }
  _updateFamilyFeedback() {
    if (!this._familyBar) return;
    if (
      (this._familyMessageUntil && Date.now() >= this._familyMessageUntil) ||
      (this._familyRetryAt && Date.now() >= Date.parse(this._familyRetryAt))
    ) {
      this._familyMessage = "";
      this._familyRetryAt = null;
    }
    const state = this._data?.family_refresh;
    this._familyBar.hidden = !state?.available;
    this._familyButton.disabled = Boolean(
      this._familyBusy ||
        Boolean(state?.next_available_at) ||
        state?.status === "checking" ||
        state?.status === "requested",
    );
    const messages = [];
    if (state?.next_available_at && !this._familyBusy)
      messages.push(
        `Next family refresh: ${this._familyRetryLabel(state.next_available_at)}.`,
      );
    if (this._familyMessage) messages.push(this._familyMessage);
    else if (state?.status === "checking")
      messages.push("Sending family refresh request…");
    else if (state?.status === "requested")
      messages.push(
        "Request accepted. Watching for newer reports for two minutes…",
      );
    else if (state?.status === "complete")
      messages.push("Family refresh check finished.");
    else if (state?.status === "send_failed")
      messages.push("The family request failed. No refresh is confirmed.");
    const names = new Map(
      (this._data?.members || []).map((m) => [m.id, m.name]),
    );
    const labels = {
      updated: "Updated",
      unchanged: "Unchanged",
      waiting: "Waiting",
      source_changed: "Tracker changed",
    };
    for (const member of state?.members || []) {
      if (names.has(member.id))
        messages.push(
          `${names.get(member.id)}: ${labels[member.status] || "Unchanged"}`,
        );
    }
    this._familyFeedback.textContent = messages.join(" · ");
  }
  _render() {
    if (!this._shell) return;
    this._updateFamilyFeedback();
    this._updateLocationFeedback();
    const focused = this.shadowRoot.activeElement?.dataset?.focus;
    this._title.textContent = displayedTitle(this._config.title);
    this._overview.setAttribute(
      "aria-pressed",
      String(this._mode === "overview"),
    );
    this._categories.replaceChildren();
    this._members.replaceChildren();
    this._providerAlerts.replaceChildren();
    if (!this._data) {
      this._status.textContent = this._error || "Connecting to HomeCircle…";
      this._mapNote.textContent =
        "Household details appear after an authenticated connection.";
      this._expanded.replaceChildren();
      return;
    }
    const members = visibleMembers(this._data, this._config.hidden_members);
    if (
      !["overview", ...categories].includes(this._mode) &&
      !members.some((m) => m.id === this._mode)
    )
      this._mode = "overview";
    this._overview.setAttribute(
      "aria-pressed",
      String(this._mode === "overview"),
    );
    const name =
      labels[this._mode] || members.find((m) => m.id === this._mode)?.name;
    const points = selection(members, this._mode, this._data.focus_ids);
    this._status.replaceChildren(
      el(
        "div",
        null,
        this._emptyCategoryMessage() ||
          (this._mode === "overview"
            ? `Everyone · ${points.length} of ${members.length} members shown on map`
            : `${name} · ${points.length} map ${points.length === 1 ? "position" : "positions"}${this._mode === "home" ? " · Primary house only" : ""}`),
      ),
    );
    if (this._error)
      this._status.prepend(el("div", "connection-warning", this._error));
    if (this._mode === "overview") {
      const hidden = members.filter(
        (member) =>
          member.map_visible === false && member.focusable && member.location,
      );
      const missing = members.filter(
        (member) => !member.focusable || !member.location,
      );
      if (hidden.length)
        this._status.append(
          el(
            "div",
            "map-visibility-note",
            `Hidden from Everyone: ${hidden.map((member) => member.name).join(", ")}`,
          ),
        );
      if (missing.length)
        this._status.append(
          el(
            "div",
            "map-visibility-note",
            `No usable map position: ${missing.map((member) => member.name).join(", ")}`,
          ),
        );
    }
    for (const alert of this._data.provider_alerts || []) {
      const message = providerAlertText(alert);
      if (message)
        this._providerAlerts.append(el("div", "provider-alert", message));
    }
    for (const category of categories) {
      const node = button("", () => this._choose(category), "category");
      node.dataset.focus = category;
      node.setAttribute("aria-pressed", String(this._mode === category));
      const count = members.filter((m) => m.presence === category).length;
      node.setAttribute("aria-label", `${labels[category]}: ${count}`);
      node.append(
        el("span", "count", count),
        el("span", "label", labels[category]),
      );
      this._categories.append(node);
    }
    for (const member of members) {
      const entry = el("div", "member-entry");
      const node = el("button", "member");
      node.type = "button";
      node.setAttribute(
        "aria-description",
        "Tap to focus on map. Press and hold for details.",
      );
      let hold;
      let startX;
      let startY;
      let suppressClick = false;
      const cancelHold = () => {
        clearTimeout(hold);
        hold = null;
      };
      node.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) return;
        startX = event.clientX;
        startY = event.clientY;
        cancelHold();
        hold = setTimeout(() => {
          hold = null;
          if (!node.isConnected) return;
          suppressClick = true;
          this._openMemberDetails(member.id, node);
          setTimeout(() => {
            suppressClick = false;
          }, 1000);
        }, 600);
      });
      node.addEventListener("pointermove", (event) => {
        if (Math.hypot(event.clientX - startX, event.clientY - startY) > 12)
          cancelHold();
      });
      for (const eventName of ["pointerup", "pointercancel", "pointerleave"])
        node.addEventListener(eventName, cancelHold);
      node.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        cancelHold();
        suppressClick = true;
        this._openMemberDetails(member.id, node);
        setTimeout(() => {
          suppressClick = false;
        }, 1000);
      });
      node.addEventListener("click", (event) => {
        if (suppressClick) {
          suppressClick = false;
          event.preventDefault();
          return;
        }
        this._choose(member.id);
      });
      node.dataset.focus = member.id;
      node.setAttribute("aria-pressed", String(this._mode === member.id));
      const details = el("div");
      const heading = el("div", "member-heading");
      heading.append(
        el("div", "name", member.name),
        el(
          "span",
          `badge ${member.presence}`,
          `${member.kind === "pet" ? "Pet · " : ""}${labels[member.presence]}`,
        ),
      );
      details.append(heading);
      const facts = el("div", "member-facts");
      if (
        member.place &&
        !(member.presence === "home" && member.place.toLowerCase() === "home")
      )
        facts.append(el("span", "place", `At ${member.place}`));
      const address = addressLabel(member);
      if (address) facts.append(el("span", "place address", address));
      if (
        Number.isFinite(member.battery) &&
        member.battery >= 0 &&
        member.battery <= 100
      ) {
        const low = member.battery <= 20 && member.charging !== true;
        facts.append(
          el(
            "span",
            `battery${low ? (member.battery <= 10 ? " low critical" : " low") : ""}`,
            `${low ? "Low battery" : "Battery"} ${member.battery}%${member.charging === true ? " · charging" : ""}`,
          ),
        );
      }
      if (facts.childElementCount) details.append(facts);
      if (member.driving.value === true && member.driving.status !== "current")
        details.append(
          el(
            "span",
            "driving-note",
            member.driving.status === "last_reported"
              ? "Driving last reported (stale)"
              : "Driving report time unknown",
          ),
        );
      const stale = member.location?.evidence?.freshness === "stale";
      node.classList.toggle("stale", stale);
      node.classList.toggle(
        "attention",
        member.presence === "unavailable" ||
          !member.location ||
          member.issues?.some((issue) => issue.includes("conflict")) === true,
      );
      const report = el("div", "report-lines");
      for (const part of reportParts(member))
        report.append(el("span", `report-part ${part.kind}`, part.text));
      details.append(report);
      node.append(memberAvatar(member, "avatar"), details);
      const detailsButton = button(
        "ⓘ",
        () => this._openMemberDetails(member.id, detailsButton),
        "member-details-button",
      );
      detailsButton.setAttribute("aria-label", `Details for ${member.name}`);
      detailsButton.title = `Details for ${member.name}`;
      entry.append(node, detailsButton);
      this._members.append(entry);
    }
    if (!members.length)
      this._members.append(
        el("div", "empty", "No members selected for this card."),
      );
    this._updateMap(points);
    if (focused)
      [...this.shadowRoot.querySelectorAll("button[data-focus]")]
        .find((n) => n.dataset.focus === focused)
        ?.focus({ preventScroll: true });
  }
  _updateMap(points) {
    if (!this._map) {
      this._hasMapView = false;
      this._map = L.map(this._mapNode, {
        zoomControl: false,
        minZoom: 0,
        maxZoom: 19,
        scrollWheelZoom: false,
        attributionControl: true,
      }).setView([0, 0], 2);
      const zoom = new L.Control({ position: "topleft" });
      zoom.onAdd = () => {
        const controls = el("div", "leaflet-control-zoom leaflet-bar");
        this._zoomInButton = button(
          "+",
          () => this._zoomCentered(1),
          "leaflet-control-zoom-in",
        );
        this._zoomOutButton = button(
          "−",
          () => this._zoomCentered(-1),
          "leaflet-control-zoom-out",
        );
        this._zoomInButton.setAttribute("aria-label", "Zoom in");
        this._zoomOutButton.setAttribute("aria-label", "Zoom out");
        this._zoomInButton.title = "Zoom in and center markers";
        this._zoomOutButton.title = "Zoom out and center markers";
        this._recenterButton = button(
          "",
          () => {
            this._fit = true;
            this._updateMap(this._points || []);
          },
          "map-recenter",
        );
        const icon = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "svg",
        );
        icon.setAttribute("viewBox", "0 0 24 24");
        icon.setAttribute("aria-hidden", "true");
        const path = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "path",
        );
        path.setAttribute(
          "d",
          "M12 2v4m0 12v4M2 12h4m12 0h4M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
        );
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", "currentColor");
        path.setAttribute("stroke-width", "2");
        icon.append(path);
        this._recenterButton.append(icon);
        this._recenterButton.setAttribute(
          "aria-label",
          "Recenter selected locations",
        );
        this._recenterButton.title = "Recenter selected locations";
        controls.append(this._zoomInButton, this._zoomOutButton);
        L.DomEvent.disableClickPropagation(controls);
        L.DomEvent.disableScrollPropagation(controls);
        return controls;
      };
      zoom.addTo(this._map);
      const recenter = new L.Control({ position: "topleft" });
      recenter.onAdd = () => {
        L.DomEvent.disableClickPropagation(this._recenterButton);
        L.DomEvent.disableScrollPropagation(this._recenterButton);
        return this._recenterButton;
      };
      recenter.addTo(this._map);
      this._map.on("zoomend zoomlevelschange", () => this._syncZoomControls());
      this._syncZoomControls();
      this._layer = L.layerGroup().addTo(this._map);
      this._map.on("zoomend moveend", () => this._markers());
      this._resize = new ResizeObserver(() => {
        this._resizeHandle?.setAttribute(
          "aria-valuenow",
          String(Math.round(this._mapNode.getBoundingClientRect().height)),
        );
        this._map?.invalidateSize({ pan: false });
        if (this._fit && this._points?.length) this._updateMap(this._points);
      });
      this._resize.observe(this._mapNode);
      this._updateTiles();
      this._radarController?.sync();
    }
    // Updates move markers; only selection changes or recentering fit the view.
    if (points.length && !this._hasMapView) this._fit = true;
    if (this._recenterButton) this._recenterButton.disabled = !points.length;
    this._points = points;
    this._updateMapNote();
    if (this._fit) {
      const size = this._map.getSize();
      if (size.x > 24 && size.y > 24) {
        if (
          points.length &&
          this._data &&
          !["overview", ...categories].includes(this._mode)
        ) {
          const overview = selection(
            visibleMembers(this._data, this._config.hidden_members),
            "overview",
            this._data.focus_ids,
          );
          const padding = pinFitPadding(size);
          const defaultZoom = overview.length
            ? Math.min(
                14,
                this._map.getBoundsZoom(
                  L.latLngBounds(
                    overview.map((m) => [
                      m.location.latitude,
                      m.location.longitude,
                    ]),
                  ),
                  false,
                  L.point(padding.paddingTopLeft).add(
                    padding.paddingBottomRight,
                  ),
                ),
              )
            : 14;
          const location = points[0].location;
          this._map.setView(
            [location.latitude, location.longitude],
            Math.min(this._map.getMaxZoom(), defaultZoom + 3),
            { animate: false },
          );
        } else if (points.length)
          this._map.fitBounds(
            points.map((m) => [m.location.latitude, m.location.longitude]),
            { ...pinFitPadding(size), maxZoom: 14, animate: false },
          );
        this._fit = false;
        if (points.length) this._hasMapView = true;
      }
    }
    this._markers();
  }
  _syncZoomControls() {
    if (!this._map || !this._zoomInButton) return;
    this._zoomInButton.disabled = this._map.getZoom() >= this._map.getMaxZoom();
    this._zoomOutButton.disabled =
      this._map.getZoom() <= this._map.getMinZoom();
  }
  _zoomCentered(delta) {
    if (!this._map) return;
    const map = this._map;
    const zoom = Math.max(
      map.getMinZoom(),
      Math.min(map.getMaxZoom(), map.getZoom() + delta),
    );
    if (zoom === map.getZoom()) return;
    let center = map.getCenter();
    const size = map.getSize();
    const visiblePoints = markerGroups(this._points || [], (loc) =>
      map.latLngToContainerPoint([loc.latitude, loc.longitude]),
    )
      .filter((group) => {
        const [width, height] = group.members.length > 1 ? [90, 108] : [54, 68];
        return (
          group.point.x + width / 2 > 0 &&
          group.point.x - width / 2 < size.x &&
          group.point.y > 0 &&
          group.point.y - height < size.y
        );
      })
      .flatMap((group) => group.members);
    if (visiblePoints.length) {
      // Center the visible pin bodies, accounting for their bottom anchors.
      const groups = markerGroups(visiblePoints, (loc) =>
        map.project([loc.latitude, loc.longitude], zoom),
      );
      const boxes = groups.map((group) => {
        const point = map.project(
          [
            group.members[0].location.latitude,
            group.members[0].location.longitude,
          ],
          zoom,
        );
        const [width, height] = group.members.length > 1 ? [90, 108] : [54, 68];
        return {
          left: point.x - width / 2,
          right: point.x + width / 2,
          top: point.y - height,
          bottom: point.y,
        };
      });
      center = map.unproject(
        [
          (Math.min(...boxes.map((box) => box.left)) +
            Math.max(...boxes.map((box) => box.right))) /
            2,
          (Math.min(...boxes.map((box) => box.top)) +
            Math.max(...boxes.map((box) => box.bottom))) /
            2,
        ],
        zoom,
      );
    }
    this._fit = false;
    map.setView(center, zoom, { animate: false });
  }
  _heightPreferenceKey() {
    return `homecircle-height:${window.location.pathname}:${this._config.title}`;
  }
  _applyMapHeight() {
    if (!this._mapWrap) return;
    const maximum = Math.max(220, window.innerHeight - 200);
    if (this._mapHeight !== null && this._mapHeight !== undefined)
      this._mapHeight = Math.round(
        Math.max(220, Math.min(maximum, this._mapHeight)),
      );
    this._mapWrap.classList.toggle("resized", this._mapHeight != null);
    if (this._mapHeight == null)
      this._mapWrap.style.removeProperty("--map-height");
    else
      this._mapWrap.style.setProperty("--map-height", `${this._mapHeight}px`);
    this._resizeHandle?.setAttribute("aria-valuemin", "220");
    this._resizeHandle?.setAttribute("aria-valuemax", String(maximum));
    this._resizeHandle?.setAttribute(
      "aria-valuenow",
      String(
        this._mapHeight ??
          Math.round(this._mapNode.getBoundingClientRect().height),
      ),
    );
    // Leaflet's default pan preserves the geographic center as its size changes.
    this._map?.invalidateSize({ animate: false, debounceMoveend: true });
  }
  _saveMapHeight() {
    try {
      if (this._mapHeight == null)
        window.localStorage.removeItem(this._heightPreferenceKey());
      else
        window.localStorage.setItem(
          this._heightPreferenceKey(),
          String(this._mapHeight),
        );
    } catch {
      /* Resizing works when browser storage is blocked. */
    }
  }
  _finishMapResize(save) {
    const drag = this._mapDrag;
    if (!drag) return;
    this._mapDrag = null;
    if (!save) {
      this._mapHeight = drag.previous;
      this._applyMapHeight();
    } else this._saveMapHeight();
    if (this._resizeHandle?.hasPointerCapture?.(drag.id))
      this._resizeHandle.releasePointerCapture(drag.id);
  }
  _mapPreferenceKey() {
    return `homecircle-map:${window.location.pathname}:${this._config.title}:${this._config.map_tiles}`;
  }
  _syncMapControls() {
    if (!this._mapControls) return;
    this._mapControls.hidden = this._config.map_tiles === "none";
    this._streetButton.setAttribute(
      "aria-pressed",
      String(this._mapBackground === "osm"),
    );
    this._satelliteButton.setAttribute(
      "aria-pressed",
      String(this._mapBackground === "satellite"),
    );
  }
  _setMapBackground(background) {
    if (
      this._config.map_tiles === "none" ||
      !["osm", "satellite"].includes(background) ||
      background === this._mapBackground
    )
      return;
    this._mapBackground = background;
    try {
      window.localStorage.setItem(this._mapPreferenceKey(), background);
    } catch {
      /* The current view still works without storage. */
    }
    this._syncMapControls();
    this._updateTiles();
    this._updateMapNote();
  }
  _updateTiles() {
    if (!this._map) return;
    if (this._tiles) {
      this._map.removeLayer(this._tiles);
      this._tiles.off();
      this._tiles = null;
    }
    this._tileCycleFailed = this._tileUnavailable = false;
    if (this._config.map_tiles === "none") return;
    const satellite = this._mapBackground === "satellite";
    const layer = L.tileLayer(
      satellite
        ? "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
        : "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        // USGS describes detailed imagery through zoom 16; enlarge it above that.
        maxNativeZoom: satellite ? 16 : 19,
        attribution: satellite
          ? '<a href="https://www.usgs.gov/the-national-map-data-delivery" target="_blank" rel="noopener">USDA, USGS The National Map: Orthoimagery</a>'
          : '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        referrerPolicy: "strict-origin-when-cross-origin",
      },
    );
    this._tiles = layer;
    layer.on("loading", () => {
      if (this._tiles === layer) this._tileCycleFailed = false;
    });
    layer.on("tileerror", () => {
      if (this._tiles !== layer) return;
      this._tileCycleFailed = this._tileUnavailable = true;
      this._updateMapNote();
    });
    layer.on("load", () => {
      if (this._tiles !== layer) return;
      this._tileUnavailable = Boolean(this._tileCycleFailed);
      this._updateMapNote();
    });
    layer.addTo(this._map);
  }
  _emptyCategoryMessage() {
    const messages = {
      away: "No one is away.",
      driving: "No one is currently reported as driving.",
      unavailable: "Everyone has available presence information.",
    };
    if (!messages[this._mode] || !this._data) return null;
    const members = visibleMembers(this._data, this._config.hidden_members);
    return members.some((member) => member.presence === this._mode)
      ? null
      : messages[this._mode];
  }
  _updateMapNote() {
    if (!this._mapNote) return;
    this._mapNote.textContent = this._emptyCategoryMessage()
      ? "Select Everyone to restore the household overview."
      : !this._points?.length
        ? "No map position shown for this selection. Presence counts are unchanged."
        : this._tileUnavailable
          ? `${this._mapBackground === "satellite" ? "Satellite" : "Street"} tiles unavailable. Presence and markers still work.`
          : this._config.map_tiles !== "none"
            ? this._mapBackground === "satellite"
              ? "Satellite · USGS imagery · U.S. detail; limited elsewhere"
              : "Street map · select a marker or member"
            : "Private map · external tiles off · enable in card settings";
  }
  _markers() {
    if (!this._map || !this._layer) return;
    const focused = this.shadowRoot.activeElement?.dataset?.focus;
    this._layer.clearLayers();
    this._expanded.replaceChildren();
    for (const group of markerGroups(this._points || [], (loc) =>
      this._map.latLngToContainerPoint([loc.latitude, loc.longitude]),
    )) {
      const list = group.members,
        first = list[0];
      const node = button(
        "",
        (event) => {
          if (list.length === 1) this._chooseFromMap(first.id, event);
          else {
            this._expandedIds = list.map((m) => m.id);
            for (const cluster of this._mapNode.querySelectorAll(
              '[data-focus^="cluster:"]',
            ))
              cluster.setAttribute("aria-expanded", String(cluster === node));
            this._showGroup(list);
            this._expanded.querySelector("button")?.focus();
          }
        },
        list.length > 1 ? "group" : "",
      );
      if (list.length > 1) {
        const portraits = el(
          "span",
          `marker-portraits count-${Math.min(list.length, 4)}`,
        );
        for (const member of list.slice(0, 4))
          portraits.append(memberAvatar(member));
        if (list.length > 4)
          portraits.append(
            el("span", "marker-overflow", `+${list.length - 4}`),
          );
        node.append(portraits);
      } else node.append(memberAvatar(first));
      const groupKey = list.map((member) => member.id).join("|");
      if (list.length > 1) {
        node.dataset.focus = `cluster:${groupKey}`;
        node.setAttribute(
          "aria-expanded",
          String(this._expandedIds?.join("|") === groupKey),
        );
      } else {
        node.dataset.focus = `marker:${first.id}`;
        node.setAttribute("aria-pressed", String(this._mode === first.id));
      }
      if (this._expandedIds?.join("|") === groupKey) this._showGroup(list);
      node.setAttribute(
        "aria-label",
        list.length > 1
          ? `${list.map((member) => member.name).join(", ")} at this location. Expand to choose.`
          : first.name,
      );
      const size = list.length > 1 ? [90, 108] : [54, 68];
      const icon = L.divIcon({
        html: node,
        className: "marker",
        iconSize: size,
        iconAnchor: [size[0] / 2, size[1]],
      });
      L.marker([first.location.latitude, first.location.longitude], {
        icon,
        keyboard: false,
      }).addTo(this._layer);
    }
    if (
      focused?.startsWith("marker:") ||
      focused?.startsWith("group:") ||
      focused?.startsWith("cluster:")
    ) {
      const controls = [
        ...this._mapNode.querySelectorAll("[data-focus]"),
        ...this._expanded.querySelectorAll("[data-focus]"),
        ...this._members.querySelectorAll("[data-focus]"),
      ];
      const memberIds = focused.slice(focused.indexOf(":") + 1).split("|");
      const target =
        controls.find((node) => node.dataset.focus === focused) ||
        controls.find(
          (node) =>
            node.dataset.focus?.startsWith("cluster:") &&
            memberIds.some((id) =>
              node.dataset.focus.slice(8).split("|").includes(id),
            ),
        ) ||
        controls.find((node) =>
          memberIds.some((id) => node.dataset.focus === `marker:${id}`),
        ) ||
        controls.find((node) => memberIds.includes(node.dataset.focus));
      target?.focus({ preventScroll: true });
    }
  }
  _showGroup(list) {
    this._expanded.replaceChildren(
      el("span", "subtle", "Choose a member at this location:"),
    );
    for (const member of list) {
      const node = button(member.name, (event) =>
        this._chooseFromMap(member.id, event),
      );
      node.dataset.focus = "group:" + member.id;
      this._expanded.append(node);
    }
  }
  _destroyMap() {
    this._radarController?.dispose();
    this._resize?.disconnect();
    this._map?.remove();
    this._map = null;
    this._layer = null;
    this._tiles = null;
    this._zoomInButton = this._zoomOutButton = null;
    this._tileCycleFailed = this._tileUnavailable = false;
    this._points = [];
    this._pointKey = null;
    this._expandedIds = null;
  }
}

class HomeCircleEditor extends HTMLElement {
  constructor() {
    super();
    this._generation = 0;
    this._refreshToken = 0;
    this.attachShadow({ mode: "open" });
  }
  setConfig(config) {
    this._config = validateConfig(config);
    this._render();
  }
  disconnectedCallback() {
    this._generation++;
    this._members = null;
    this._loaded = false;
    this.shadowRoot.replaceChildren();
  }
  set hass(hass) {
    if (this._connection !== hass.connection || hass.connected === false) {
      this._generation++;
      this._loaded = false;
      this._members = null;
      this._connection = hass.connection;
      this._render();
    }
    if (!this._loaded && hass.connected !== false) {
      this._loaded = true;
      const generation = ++this._generation;
      hass
        .callWS({ type: "homecircle/snapshot" })
        .then((data) => {
          if (generation !== this._generation || !this.isConnected) return;
          this._members = data.members.map((member) => ({
            id: member.id,
            name: member.name,
          }));
          this._render();
        })
        .catch(() => {
          if (generation === this._generation) {
            this._loaded = false;
            this._members = null;
            this._render();
          }
        });
    }
  }
  _change(patch) {
    this._config = { ...this._config, ...patch };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }
  _render() {
    if (!this._config) return;
    this.shadowRoot.replaceChildren();
    const style = el("style");
    style.textContent = css;
    const root = el("div", "editor");
    const label = el("label", "", "Title");
    const input = el("input");
    input.type = "text";
    input.value = this._config.title;
    input.addEventListener("change", () =>
      this._change({ title: input.value }),
    );
    label.append(input);
    root.append(label);
    const mapLabel = el("label", "", "Map background");
    const select = el("select");
    for (const [value, text] of [
      ["none", "Private · no external tiles"],
      ["osm", "Street · OpenStreetMap"],
      ["satellite", "Satellite · USGS imagery (U.S. detail)"],
    ]) {
      const option = el("option", "", text);
      option.value = value;
      select.append(option);
    }
    select.value = this._config.map_tiles;
    select.addEventListener("change", () =>
      this._change({ map_tiles: select.value }),
    );
    mapLabel.append(select);
    root.append(mapLabel);
    root.append(
      el(
        "p",
        "",
        "Street is the default. Satellite uses USGS aerial and satellite imagery, with detailed coverage in the U.S. and limited detail elsewhere. Images are historical, not live. Tile requests send the viewed map area, your network address, and site origin to the selected service. No names or HA credentials are sent. Choose Private to turn external tiles off. Availability is best effort.",
      ),
    );
    const link = el("a", "", "OpenStreetMap privacy policy");
    link.href = "https://osmfoundation.org/wiki/Privacy_Policy";
    link.target = "_blank";
    link.rel = "noopener";
    root.append(link);
    const imageryLink = el("a", "", "USGS imagery information");
    imageryLink.href = "https://www.usgs.gov/the-national-map-data-delivery";
    imageryLink.target = "_blank";
    imageryLink.rel = "noopener";
    root.append(imageryLink);
    const fill = el("label", "check");
    const fillCheck = el("input");
    fillCheck.type = "checkbox";
    fillCheck.checked = this._config.fill_screen;
    fillCheck.addEventListener("change", () =>
      this._change({ fill_screen: fillCheck.checked }),
    );
    fill.append(fillCheck, el("span", "", "Fill wall display height"));
    root.append(fill);
    root.append(
      el(
        "p",
        "",
        "Use with a dedicated full-width dashboard view. The map expands to use the space below this card's top edge.",
      ),
    );
    const field = el("fieldset");
    field.append(el("legend", "", "Visible members"));
    for (const member of this._members || []) {
      const row = el("label", "check");
      const check = el("input");
      check.type = "checkbox";
      check.checked = !this._config.hidden_members.includes(member.id);
      check.addEventListener("change", () => {
        const hidden = new Set(this._config.hidden_members);
        check.checked ? hidden.delete(member.id) : hidden.add(member.id);
        this._change({ hidden_members: [...hidden] });
      });
      row.append(check, el("span", "", member.name));
      field.append(row);
    }
    root.append(
      field,
      el(
        "p",
        "",
        "Visibility applies to this card only. HA user permissions control access. Configure household sources in Settings → Devices & services → HomeCircle.",
      ),
    );
    this.shadowRoot.append(style, root);
  }
}
if (!customElements.get("homecircle-card"))
  customElements.define("homecircle-card", HomeCircleCard);
if (!customElements.get("homecircle-card-editor"))
  customElements.define("homecircle-card-editor", HomeCircleEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "homecircle-card"))
  window.customCards.push({
    type: "homecircle-card",
    name: "HomeCircle",
    description:
      "Household presence and map controls, with a Private background option.",
    preview: true,
  });
