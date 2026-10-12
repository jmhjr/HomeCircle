// The same source rectangle drives the preview and the uploaded square image.
export function cropRectangle(width, height, zoom = 1, x = 0, y = 0) {
  const side = Math.max(width, height) / Math.max(0.5, zoom);
  const position = (value) =>
    (Math.max(-100, Math.min(100, value)) + 100) / 200;
  return {
    x: (width - side) * position(x),
    y: (height - side) * position(y),
    side,
  };
}

export function createPictureCrop(onChange) {
  const panel = document.createElement("div");
  panel.hidden = true;
  const help = document.createElement("p");
  help.textContent =
    "Drag the picture or use the sliders to position it. The circle shows how it will appear on the card.";
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 512;
  canvas.setAttribute("aria-label", "Cropped picture preview");
  canvas.style.cssText =
    "display:block;width:min(256px,100%);aspect-ratio:1;margin:12px auto;border-radius:50%;touch-action:none;cursor:grab";
  const controls = {};
  for (const [name, min, max, step, value] of [
    ["Zoom", 0.5, 8, 0.05, 1],
    ["Horizontal position", -100, 100, 1, 0],
    ["Vertical position", -100, 100, 1, 0],
  ]) {
    const label = document.createElement("label");
    label.textContent = name;
    label.style.cssText = "display:block;margin:12px 0";
    const input = document.createElement("input");
    input.type = "range";
    Object.assign(input, {
      min: String(min),
      max: String(max),
      step: String(step),
      value: String(value),
    });
    input.setAttribute("aria-label", name);
    input.style.cssText = "display:block;width:100%";
    input.addEventListener("input", draw);
    controls[name] = input;
    label.append(input);
    panel.append(label);
  }
  let image = null,
    generation = 0,
    drag = null;
  const rect = () =>
    cropRectangle(
      image.naturalWidth,
      image.naturalHeight,
      Number(controls.Zoom.value),
      Number(controls["Horizontal position"].value),
      Number(controls["Vertical position"].value),
    );
  function draw() {
    if (!image) return;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Picture editing is unavailable");
    const crop = rect();
    context.fillStyle = "white";
    context.fillRect(0, 0, 512, 512);
    context.drawImage(
      image,
      crop.x,
      crop.y,
      crop.side,
      crop.side,
      0,
      0,
      512,
      512,
    );
  }
  const reset = document.createElement("button");
  reset.type = "button";
  reset.textContent = "Reset crop";
  reset.addEventListener("click", () => {
    controls.Zoom.value = "1";
    controls["Horizontal position"].value = controls[
      "Vertical position"
    ].value = "0";
    draw();
  });
  canvas.addEventListener("pointerdown", (event) => {
    if (!image) return;
    drag = { x: event.clientX, y: event.clientY };
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!drag || !image) return;
    const crop = rect(),
      size = canvas.getBoundingClientRect().width;
    if (!size) return;
    for (const [label, delta, available] of [
      [
        "Horizontal position",
        event.clientX - drag.x,
        image.naturalWidth - crop.side,
      ],
      [
        "Vertical position",
        event.clientY - drag.y,
        image.naturalHeight - crop.side,
      ],
    ]) {
      if (available !== 0)
        controls[label].value = String(
          Math.max(
            -100,
            Math.min(
              100,
              Number(controls[label].value) -
                ((delta * crop.side) / size / available) * 200,
            ),
          ),
        );
    }
    drag = { x: event.clientX, y: event.clientY };
    draw();
  });
  const endDrag = () => {
    drag = null;
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  panel.prepend(help, canvas);
  panel.append(reset);
  function clear() {
    generation++;
    image = null;
    panel.hidden = true;
    drag = null;
    onChange(false);
  }
  return {
    panel,
    get active() {
      return !!image;
    },
    clear,
    async load(file) {
      clear();
      const current = generation;
      const url = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Cannot read picture"));
        reader.readAsDataURL(file);
      });
      const decoded = await new Promise((resolve, reject) => {
        const candidate = new Image();
        candidate.onload = () => resolve(candidate);
        candidate.onerror = () => reject(new Error("Cannot decode picture"));
        candidate.src = url;
      });
      if (current !== generation || !panel.isConnected) return;
      image = decoded;
      controls.Zoom.value = "1";
      controls["Horizontal position"].value = controls[
        "Vertical position"
      ].value = "0";
      draw();
      panel.hidden = false;
      onChange(true);
    },
    async file() {
      if (!image) throw new Error("No picture selected");
      draw();
      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.92),
      );
      if (!blob) throw new Error("Cannot crop picture");
      return new File([blob], "homecircle-picture.jpg", { type: "image/jpeg" });
    },
  };
}
