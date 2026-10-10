const FLOW_PATH = "config/config_entries/options/flow";

function initialData(schema) {
  const data = {};
  for (const field of schema || []) {
    if (field.description?.suggested_value != null)
      data[field.name] = field.description.suggested_value;
    else if (Object.hasOwn(field, "default")) data[field.name] = field.default;
    else if (field.type === "expandable") {
      const nested = initialData(field.schema);
      if (field.required || Object.keys(nested).length)
        data[field.name] = nested;
    } else if (field.required && field.selector?.select?.options?.length) {
      const select = field.selector.select;
      const first = select.options[0];
      const value = typeof first === "string" ? first : first.value;
      data[field.name] = select.multiple ? [value] : value;
    } else if (field.required && field.selector?.boolean) {
      data[field.name] = false;
    } else if (field.required && field.selector?.["entity"]) {
      data[field.name] = field.selector["entity"].multiple ? [] : "";
    }
  }
  return data;
}

function translate(hass, key, fallback, placeholders) {
  return hass.localize?.(key, placeholders) || fallback;
}

function appendDescription(node, description) {
  description = description.replaceAll("**", "");
  const marker = "[Home Assistant People settings](/config/person)";
  const index = description.indexOf(marker);
  if (index < 0) {
    node.textContent = description;
    return;
  }
  node.append(document.createTextNode(description.slice(0, index)));
  const link = document.createElement("a");
  link.href = "/config/person";
  link.textContent = "Home Assistant People settings";
  node.append(
    link,
    document.createTextNode(description.slice(index + marker.length)),
  );
}

export async function openSettingsDialog(
  card,
  hass,
  memberId = null,
  returnToMember = null,
) {
  if (!hass?.user?.is_admin) return;
  const host =
    document.querySelector("home-assistant")?.shadowRoot || document.body;
  if (host.querySelector("dialog.homecircle-settings")) return;
  const dialog = document.createElement("dialog");
  dialog.className = "homecircle-settings";
  dialog.setAttribute("aria-label", "HomeCircle settings");
  dialog.innerHTML = `<style>
    dialog.homecircle-settings { width: min(620px, calc(100vw - 32px)); max-height: min(85vh, 850px); padding: 0; border: 0; border-radius: 22px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #222); box-shadow: 0 20px 70px #0007; }
    dialog.homecircle-settings::backdrop { background: #0009; }
    .homecircle-settings * { box-sizing: border-box; }
    .homecircle-settings header { display: flex; align-items: center; gap: 12px; padding: 20px 24px 12px; border-bottom: 1px solid var(--divider-color, #ddd); }
    .homecircle-settings h2 { flex: 1; margin: 0; font: 600 20px/1.3 system-ui, sans-serif; }
    .homecircle-settings .heading { flex: 1; min-width: 0; }
    .homecircle-settings .version { margin-top: 4px; color: var(--secondary-text-color, #666); font: 12px/1.4 system-ui, sans-serif; }
    .homecircle-settings button { font: inherit; cursor: pointer; }
    .homecircle-settings .close { border: 0; background: transparent; color: inherit; font-size: 25px; line-height: 1; min-width: 36px; min-height: 36px; }
    .homecircle-settings .body { padding: 16px 24px 22px; overflow-y: auto; max-height: calc(min(85vh, 850px) - 75px); }
    .homecircle-settings .choice { display: block; width: 100%; padding: 15px 12px; margin: 4px 0; border: 0; border-radius: 10px; background: transparent; color: inherit; text-align: left; }
    .homecircle-settings .choice[hidden] { display: none; }
    .homecircle-settings .choice:hover, .homecircle-settings .choice:focus-visible { background: var(--secondary-background-color, #eee); }
    .homecircle-settings .choice::after { content: "›"; float: right; font-size: 22px; line-height: 18px; }
    .homecircle-settings .description { margin: 0 0 18px; color: var(--secondary-text-color, #666); white-space: pre-line; }
    .homecircle-settings .settings-label { margin: 20px 0 8px; font: 600 15px/1.4 system-ui, sans-serif; }
    .homecircle-settings ha-form { display: block; width: 100%; }
    .homecircle-settings .error { color: var(--error-color, #b3261e); }
    .homecircle-settings .actions { display: flex; justify-content: flex-end; gap: 10px; padding-top: 18px; }
    .homecircle-settings .actions button { padding: 9px 15px; border-radius: 9px; border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color, #fff); color: inherit; }
    .homecircle-settings .actions .primary { background: var(--primary-color, #03a9f4); color: white; border-color: transparent; }
  </style><header><div class="heading"><h2></h2><div class="version"></div></div><button type="button" class="close" aria-label="Close">×</button></header><div class="body"></div>`;
  host.append(dialog);
  dialog.querySelector(".version").textContent = card._integrationVersion
    ? `Version ${card._integrationVersion}`
    : "";
  const title = dialog.querySelector("h2");
  const body = dialog.querySelector(".body");
  let step;
  let busy = false;
  let selectedMember = memberId;
  const cancelledFlows = new Set();
  const cancelFlow = (flow) => {
    if (
      !flow?.flow_id ||
      ["create_entry", "abort"].includes(flow.type) ||
      cancelledFlows.has(flow.flow_id)
    )
      return;
    cancelledFlows.add(flow.flow_id);
    hass.callApi("DELETE", `${FLOW_PATH}/${flow.flow_id}`).catch(() => {});
  };
  const receiveFlow = (flow) => {
    if (!dialog.isConnected) {
      cancelFlow(flow);
      return false;
    }
    step = flow;
    return true;
  };
  const close = () => dialog.close();
  dialog.querySelector(".close").addEventListener("click", close);
  dialog.addEventListener("close", () => {
    cancelFlow(step);
    dialog.remove();
    card._settingsButton?.focus();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target.closest?.('a[href="/config/person"]')) close();
  });
  dialog.showModal();

  const message = (text, error = false) => {
    title.textContent = "HomeCircle settings";
    body.replaceChildren();
    const p = document.createElement("p");
    p.className = error ? "error" : "description";
    p.textContent = text;
    body.append(p);
  };
  const text = (key, fallback, placeholders = step?.description_placeholders) =>
    translate(
      card._hass || hass,
      `component.homecircle.options.${key}`,
      fallback,
      placeholders,
    );

  const advance = async (data) => {
    if (busy || !step || !dialog.isConnected) return;
    busy = true;
    try {
      const next = await hass.callApi(
        "POST",
        `${FLOW_PATH}/${step.flow_id}`,
        data,
      );
      render(next);
    } catch {
      message(
        "Could not update HomeCircle settings. Close this dialog and try again.",
        true,
      );
    } finally {
      busy = false;
    }
  };
  const action = (label, onClick, primary = false) => {
    const control = document.createElement("button");
    control.type = "button";
    control.textContent = label;
    if (primary) control.className = "primary";
    control.addEventListener("click", onClick);
    return control;
  };
  const restartFlow = async (targetStep) => {
    if (busy || !dialog.isConnected) return;
    busy = true;
    try {
      const entries = await hass.callWS({
        type: "config_entries/get",
        domain: "homecircle",
      });
      if (!dialog.isConnected || !entries?.length) return;
      const oldStep = step;
      const initial = await hass.callApi("POST", FLOW_PATH, {
        handler: entries[0].entry_id,
      });
      cancelFlow(oldStep);
      if (!receiveFlow(initial)) return;
      render(
        targetStep
          ? await hass.callApi("POST", `${FLOW_PATH}/${initial.flow_id}`, {
              next_step_id: targetStep,
            })
          : initial,
      );
    } catch {
      if (dialog.isConnected)
        message("Could not return to settings choices.", true);
    } finally {
      busy = false;
    }
  };
  const render = (next) => {
    if (!receiveFlow(next)) return;
    body.replaceChildren();
    if (next.type === "create_entry") {
      close();
      card._load();
      return;
    }
    if (next.type === "abort") {
      message(text(`abort.${next.reason}`, "Setup was stopped."));
      return;
    }
    if (next.type === "menu") {
      title.textContent = text(
        `step.${next.step_id}.title`,
        "What would you like to change?",
      );
      const description = text(`step.${next.step_id}.description`, "");
      if (description) {
        const p = document.createElement("p");
        p.className = "description";
        p.textContent = description.replaceAll("**", "");
        body.append(p);
      }
      if (!memberId && card._radarController) {
        const label = document.createElement("label");
        label.style.cssText =
          "display:flex;align-items:center;gap:10px;padding:12px";
        const check = document.createElement("input");
        check.type = "checkbox";
        check.checked = card._radarController.showControls;
        check.addEventListener("change", () =>
          card._radarController.setShowControls(check.checked),
        );
        label.append(
          check,
          document.createTextNode("Show radar opacity and color guide"),
        );
        const hint = document.createElement("p");
        hint.className = "description";
        hint.textContent =
          "For this browser. Controls appear on the map when Radar is on.";
        body.append(label, hint);
      }
      const options = Array.isArray(next.menu_options)
        ? next.menu_options.map((key) => [
            key,
            text(`step.${next.step_id}.menu_options.${key}`, key),
          ])
        : Object.entries(next.menu_options);
      for (const [key, label] of options) {
        const control = action(label, () => advance({ next_step_id: key }));
        control.className = "choice";
        body.append(control);
      }
      return;
    }
    if (next.type === "form") {
      title.textContent = text(
        `step.${next.step_id}.title`,
        "HomeCircle settings",
      );
      const description = text(`step.${next.step_id}.description`, "");
      if (description) {
        const p = document.createElement("p");
        p.className = "description";
        appendDescription(p, description);
        body.append(p);
      }
      if (next.errors?.base) {
        const p = document.createElement("p");
        p.className = "error";
        p.textContent = text(`error.${next.errors.base}`, next.errors.base);
        body.append(p);
      }
      const form = document.createElement("ha-form");
      const trackerChoice = next.step_id === "tracker_member_choice";
      const settingField = next.data_schema?.find(
        (field) => field.name === "setting",
      );
      form.hass = card._hass || hass;
      form.schema = trackerChoice
        ? next.data_schema?.filter((field) => field.name === "member") || []
        : next.data_schema || [];
      const memberOptions = form.schema[0]?.selector?.select?.options || [];
      const restoreMember =
        trackerChoice &&
        memberOptions.some((option) => option.value === selectedMember);
      form.data = trackerChoice
        ? restoreMember
          ? { member: selectedMember }
          : {}
        : initialData(form.schema);
      form.error = next.errors || {};
      form.context = { handler: next.handler, domain: "homecircle" };
      form.computeLabel = (field) =>
        text(`step.${next.step_id}.data.${field.name}`, field.name);
      form.computeHelper = (field) =>
        text(`step.${next.step_id}.data_description.${field.name}`, "");
      form.computeError = (error) => text(`error.${error}`, error);
      form.localizeValue = (key) =>
        translate(
          card._hass || hass,
          `component.homecircle.selector.${key}`,
          key,
        );
      const choices = document.createElement("div");
      choices.hidden = !form.data?.member;
      const removableMembers = new Set(
        (next.description_placeholders?.removable_members || "")
          .split(",")
          .filter(Boolean),
      );
      let removeControl;
      if (trackerChoice) {
        const label = document.createElement("h3");
        label.className = "settings-label";
        label.textContent = text(
          `step.${next.step_id}.data.setting`,
          "Available settings",
        );
        choices.append(label);
        for (const option of settingField?.selector?.select?.options || []) {
          const control = action(option.label, () =>
            advance({ member: form.data.member, setting: option.value }),
          );
          control.className = "choice";
          if (option.value === "remove")
            control.hidden = !removableMembers.has(form.data?.member);
          choices.append(control);
          if (option.value === "remove") removeControl = control;
        }
      }
      form.addEventListener("value-changed", (event) => {
        form.data = event.detail.value;
        if (trackerChoice) {
          selectedMember = form.data?.member;
          choices.hidden = !selectedMember;
        }
        if (removeControl)
          removeControl.hidden = !removableMembers.has(form.data?.member);
      });
      body.append(form);
      if (trackerChoice) body.append(choices);
      const buttons = document.createElement("div");
      buttons.className = "actions";
      buttons.append(
        action("Back", () => {
          if (trackerChoice && memberId && returnToMember) {
            close();
            returnToMember(selectedMember || memberId);
            return;
          }
          restartFlow(
            next.step_id === "add_tracker_assign"
              ? "add_tracker_choice"
              : !!selectedMember &&
                  ["remove_tracker_choice", "member", "supporting"].includes(
                    next.step_id,
                  )
                ? "tracker_member_choice"
                : undefined,
          );
        }),
        ...(trackerChoice
          ? []
          : [action("Continue", () => advance(form.data || {}), true)]),
      );
      body.append(buttons);
      return;
    }
    message("Continue this setup from the HomeCircle integration page.", true);
  };

  message("Opening settings…");
  try {
    const entries = await hass.callWS({
      type: "config_entries/get",
      domain: "homecircle",
    });
    if (!dialog.isConnected) return;
    if (!entries?.length) {
      message("Add the HomeCircle integration before changing settings.", true);
      return;
    }
    await Promise.all([
      hass.loadFragmentTranslation?.("config"),
      hass.loadBackendTranslation?.("options", "homecircle"),
      hass.loadBackendTranslation?.("selector", "homecircle"),
    ]);
    if (!dialog.isConnected) return;
    const initial = await hass.callApi("POST", FLOW_PATH, {
      handler: entries[0].entry_id,
    });
    if (!receiveFlow(initial)) return;
    render(
      memberId
        ? await hass.callApi("POST", `${FLOW_PATH}/${initial.flow_id}`, {
            next_step_id: "tracker_member_choice",
          })
        : initial,
    );
  } catch {
    if (dialog.isConnected)
      message(
        "Could not open HomeCircle settings. Try again in a moment.",
        true,
      );
  }
}
