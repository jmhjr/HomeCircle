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
export function memberAvatar(member, className = "marker-avatar") {
  const avatar = document.createElement("span");
  avatar.className = className;
  avatar.textContent = initials(member.name);
  avatar.setAttribute("aria-hidden", "true");
  if (allowedPicture(member.picture)) {
    const picture = document.createElement("img");
    picture.alt = "";
    picture.referrerPolicy = "no-referrer";
    picture.src = member.picture;
    picture.addEventListener("error", () => picture.remove(), { once: true });
    avatar.append(picture);
  }
  return avatar;
}
