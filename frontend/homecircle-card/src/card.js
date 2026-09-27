import * as L from "leaflet";
import leafletCSS from "leaflet/dist/leaflet.css";
import css from "./style.css";
import {
  categories,
  labels,
  visibleMembers,
  selection,
  reportLabel,
  markerGroups,
  validateConfig,
} from "./model.js";

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

class HomeCircleCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mode = "overview";
    this._generation = 0;
  }
  static getConfigElement() {
    return document.createElement("homecircle-card-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:homecircle-card",
      title: "HomeCircle",
      map_tiles: "none",
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
    if (old?.map_tiles !== this._config.map_tiles) this._destroyMap();
    this._mode = "overview";
    this._fit = true;
    if (this.isConnected) {
      this._layout();
      this._render();
      this._load();
    }
  }
  set hass(hass) {
    const changed = this._hass?.connection !== hass.connection;
    this._hass = hass;
    if (changed) {
      clearTimeout(this._timeout);
      this._generation++;
      this._busy = false;
      this._clear("Connecting to Home Assistant…");
    }
    if (hass.connected === false) {
      clearTimeout(this._timeout);
      this._generation++;
      this._busy = false;
      this._clear("Home Assistant is disconnected.");
      return;
    }
    if (this.isConnected && (!this._data || changed)) this._load();
  }
  connectedCallback() {
    this._layout();
    this._render();
    this._load();
    clearInterval(this._timer);
    this._timer = setInterval(() => this._load(), 15000);
  }
  disconnectedCallback() {
    clearInterval(this._timer);
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
    header.append(
      brand,
      button("Everyone ↗", () => this._choose("overview"), "overview"),
    );
    this._status = el("div", "status");
    this._status.setAttribute("role", "status");
    this._status.setAttribute("aria-live", "polite");
    const wrap = el("div", "map-wrap");
    this._mapNode = el("div", "map");
    this._mapNode.setAttribute("aria-label", "Household locations");
    this._mapNote = el("div", "map-note");
    wrap.append(this._mapNode, this._mapNote);
    this._expanded = el("div", "expanded");
    this._categories = el("div", "categories");
    this._members = el("div", "members");
    this._shell.append(
      header,
      this._status,
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
        this._clear("Connection timed out. Retrying…");
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
      this._error = null;
      if (first) this._fit = true;
      if (first || signature !== this._signature) this._render();
      this._signature = signature;
    } catch (error) {
      if (generation === this._generation)
        this._clear(
          error.code === "unauthorized"
            ? "This HA user cannot view all selected household sources."
            : "HomeCircle is unavailable. Add or repair it in Settings → Devices & services.",
        );
    } finally {
      if (generation === this._generation) {
        clearTimeout(this._timeout);
        this._busy = false;
      }
    }
  }
  _clear(message) {
    this._data = null;
    this._signature = null;
    this._mode = "overview";
    this._error = message;
    this._destroyMap();
    this._render();
  }
  _choose(mode) {
    this._expandedIds = null;
    this._mode = mode;
    this._expanded?.replaceChildren();
    this._fit = true;
    this._render();
  }
  _render() {
    if (!this._shell) return;
    const focused = this.shadowRoot.activeElement?.dataset?.focus;
    this._title.textContent = this._config.title;
    this._categories.replaceChildren();
    this._members.replaceChildren();
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
    const name =
      labels[this._mode] || members.find((m) => m.id === this._mode)?.name;
    const points = selection(members, this._mode, this._data.focus_ids);
    this._status.textContent = `${name} · ${points.length} map ${points.length === 1 ? "position" : "positions"}${this._mode === "home" ? " · Primary house only" : ""}`;
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
      const node = button("", () => this._choose(member.id), "member");
      node.dataset.focus = member.id;
      node.setAttribute("aria-pressed", String(this._mode === member.id));
      const details = el("div");
      details.append(el("div", "name", member.name));
      const extra = [];
      if (member.place) extra.push(member.place);
      if (member.battery !== null)
        extra.push(
          `${member.battery}%${member.charging === true ? " · charging" : ""}`,
        );
      if (member.driving.value === true && member.driving.status !== "current")
        extra.push(
          member.driving.status === "last_reported"
            ? "Driving last reported (stale)"
            : "Driving report time unknown",
        );
      if (extra.length) details.append(el("span", "detail", extra.join(" · ")));
      const stale = member.location?.evidence?.freshness === "stale";
      node.classList.toggle("stale", stale);
      details.append(
        el(
          "span",
          stale ? "detail report stale-report" : "detail report",
          reportLabel(member),
        ),
      );
      node.append(
        el("span", "avatar", initials(member.name)),
        details,
        el(
          "span",
          `badge ${member.presence}`,
          `${member.kind === "pet" ? "Pet · " : ""}${labels[member.presence]}`,
        ),
      );
      this._members.append(node);
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
      this._map = L.map(this._mapNode, {
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: true,
      }).setView([0, 0], 2);
      this._layer = L.layerGroup().addTo(this._map);
      this._map.on("zoomend moveend", () => this._markers());
      this._resize = new ResizeObserver(() =>
        this._map?.invalidateSize({ pan: false }),
      );
      this._resize.observe(this._mapNode);
      if (this._config.map_tiles === "osm") {
        this._tiles = L.tileLayer(
          "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          {
            maxZoom: 19,
            attribution:
              '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
            referrerPolicy: "strict-origin-when-cross-origin",
          },
        ).addTo(this._map);
        this._tiles.on("loading", () => {
          this._tileCycleFailed = false;
        });
        this._tiles.on("tileerror", () => {
          this._tileCycleFailed = this._tileUnavailable = true;
          this._updateMapNote();
        });
        this._tiles.on("load", () => {
          this._tileUnavailable = Boolean(this._tileCycleFailed);
          this._updateMapNote();
        });
      }
    }
    const pointKey = JSON.stringify(
      points.map((m) => [m.id, m.location.latitude, m.location.longitude]),
    );
    if (pointKey !== this._pointKey) this._fit = true;
    this._pointKey = pointKey;
    this._points = points;
    this._updateMapNote();
    if (this._fit) {
      if (points.length)
        this._map.fitBounds(
          points.map((m) => [m.location.latitude, m.location.longitude]),
          { padding: [48, 48], maxZoom: 14, animate: false },
        );
      else this._map.setView([0, 0], 2, { animate: false });
      this._fit = false;
    }
    this._markers();
  }
  _updateMapNote() {
    if (!this._mapNote) return;
    this._mapNote.textContent = !this._points?.length
      ? "No usable map position for this selection. Presence counts are unchanged."
      : this._tileUnavailable
        ? "Street tiles unavailable. Presence and markers still work."
        : this._config.map_tiles === "osm"
          ? "Street map · select a marker or member"
          : "Private map · street tiles off · enable in card settings";
  }
  _markers() {
    if (!this._map || !this._layer) return;
    this._layer.clearLayers();
    this._expanded.replaceChildren();
    for (const group of markerGroups(this._points || [], (loc) =>
      this._map.latLngToContainerPoint([loc.latitude, loc.longitude]),
    )) {
      const list = group.members,
        first = list[0];
      const node = button(
        list.length > 1 ? String(list.length) : initials(first.name),
        () => {
          if (list.length === 1) this._choose(first.id);
          else {
            this._expandedIds = list.map((m) => m.id);
            this._showGroup(list);
            this._expanded.querySelector("button")?.focus();
          }
        },
        list.length > 1 ? "group" : "",
      );
      if (this._expandedIds?.join("|") === list.map((m) => m.id).join("|"))
        this._showGroup(list);
      node.setAttribute(
        "aria-label",
        list.length > 1
          ? `${list.length} overlapping members. Expand to choose.`
          : first.name,
      );
      const icon = L.divIcon({
        html: node,
        className: "marker",
        iconSize: [46, 46],
        iconAnchor: [23, 23],
      });
      L.marker([first.location.latitude, first.location.longitude], {
        icon,
        keyboard: false,
      }).addTo(this._layer);
    }
  }
  _showGroup(list) {
    this._expanded.replaceChildren(
      el("span", "subtle", "Choose a member at this location:"),
    );
    for (const member of list) {
      const node = button(member.name, () => this._choose(member.id));
      node.dataset.focus = "group:" + member.id;
      this._expanded.append(node);
    }
  }
  _destroyMap() {
    this._resize?.disconnect();
    this._map?.remove();
    this._map = null;
    this._layer = null;
    this._tiles = null;
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
      ["osm", "OpenStreetMap · external street tiles"],
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
        "Street tiles are optional. Enabling OpenStreetMap sends the viewed map area, your network address, and site origin to its tile service. No names or HA credentials are sent. Availability is best effort.",
      ),
    );
    const link = el("a", "", "OpenStreetMap privacy policy");
    link.href = "https://osmfoundation.org/wiki/Privacy_Policy";
    link.target = "_blank";
    link.rel = "noopener";
    root.append(link);
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
      "Household presence, residences, and a private-by-default map.",
    preview: true,
  });
