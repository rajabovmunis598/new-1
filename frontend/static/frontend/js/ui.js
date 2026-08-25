const iconPaths = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  messages: '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 9h8M8 13h5"/>',
  contacts: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  orders: '<path d="M6 2h12l2 4v16H4V6z"/><path d="M4 6h16M9 10h6"/>',
  integrations: '<path d="M8 12h8M12 8v8"/><path d="M5.5 8.5 3 6l3-3 2.5 2.5M18.5 15.5 21 18l-3 3-2.5-2.5M15.5 5.5 18 3l3 3-2.5 2.5M8.5 18.5 6 21l-3-3 2.5-2.5"/>',
  facebook: '<path d="M14 8h3V4h-3c-2.8 0-5 2.2-5 5v3H6v4h3v4h4v-4h3l1-4h-4V9c0-.6.4-1 1-1z"/>',
  viber: '<path d="M20 4.5C17.5 2 7 1.5 4.2 4.3 1.8 6.7 2.1 15 5 18l-2 3 3.7-1.4c3.4 1.4 11.9.5 13.3-2.8 1-2.5 1-9.8 0-12.3z"/><path d="M8 8c1 3 3 5 6 6M9 7h2M15 13v2"/>',
  vk: '<path d="M4 7c.3 5 2.9 10 8 10h.3v-3.1c1.9.2 3.3 1.5 4 3.1H20c-.5-2-2.1-3.5-3.5-4.2 1.2-.7 2.5-2.4 3-4.8h-3.1c-.6 2.1-1.6 3.6-2.8 3.8V8H10v4.2C8.8 11.8 7.8 10.3 7.5 8H4z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.1A1.7 1.7 0 0 0 8.5 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3V9.6h.1A1.7 1.7 0 0 0 4.6 8.5a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.1A1.7 1.7 0 0 0 15.5 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.18.38.47.7.84.9.3.17.66.26 1.01.26H21v4h-.1A1.7 1.7 0 0 0 19.4 15z"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  chevronLeft: '<path d="m15 18-6-6 6-6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  instagram: '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>',
  archive: '<path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  alert: '<path d="M10.3 2.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 2.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  more: '<circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 11v5M14 11v5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  logout: '<path d="M10 17l5-5-5-5M15 12H3M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 4.2A10.8 10.8 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-2.1 3.2M6.6 6.6C3.7 8.5 2 12 2 12s3.5 8 10 8a9.8 9.8 0 0 0 4-.9"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  external: '<path d="M15 3h6v6M10 14 21 3M21 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.7 19.7 0 0 1-8.6-3.1 19.3 19.3 0 0 1-6-6A19.7 19.7 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.5 2.1L8.1 9.8a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.8 2.1z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  filter: '<path d="M4 5h16M7 12h10M10 19h4"/>',
  wifi: '<path d="M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 20h.01"/>',
  paperclip: '<path d="m21.4 11.6-8.5 8.5a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8l8.5-8.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  sparkles: '<path d="M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5z"/><path d="M19 14l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" opacity=".6"/>',
};

let modalEscapeHandler = null;

export function icon(name, className = "icon") {
  const paths = iconPaths[name] || iconPaths.info;
  return `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

export function escapeHTML(value = "") {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

export function safeUrl(value = "") {
  if (!String(value).trim()) return "#";
  try {
    const url = new URL(value, window.location.origin);
    if (["http:", "https:", "tel:", "mailto:"].includes(url.protocol)) return url.href;
  } catch (_) { /* Invalid URL. */ }
  return "#";
}

export function initials(value = "M") {
  const words = String(value).trim().split(/\s+/).filter(Boolean);
  return (words.slice(0, 2).map((word) => word[0]).join("") || "M").toLocaleUpperCase("tg-TJ");
}

export function avatar(person = {}, size = "") {
  const name = person.name || person.title || person.username || person.email || "Муштарӣ";
  const image = person.avatar_url && safeUrl(person.avatar_url) !== "#"
    ? `<img src="${escapeHTML(safeUrl(person.avatar_url))}" alt="">`
    : escapeHTML(initials(name));
  return `<span class="avatar ${size}">${image}</span>`;
}

const platformLabels = { telegram: "Telegram", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook", viber: "Viber", vk: "VK" };
const statusLabels = {
  active: "Фаъол", inactive: "Ғайрифаъол", error: "Хатогӣ", pending: "Интизорӣ",
  open: "Кушода", closed: "Пӯшида", archived: "Бойгонӣ",
  new: "Нав", processing: "Дар кор", completed: "Анҷом ёфт", cancelled: "Бекор шуд",
};

export function platformBadge(platform) {
  const safe = Object.prototype.hasOwnProperty.call(platformLabels, platform) ? platform : "unknown";
  return `<span class="platform-badge ${safe}">${platformLabels[platform] || escapeHTML(platform || "—")}</span>`;
}

export function platformLabel(platform) {
  return platformLabels[platform] || String(platform || "—");
}

export function statusBadge(status) {
  return `<span class="status-badge ${escapeHTML(status || "inactive")}">${statusLabels[status] || escapeHTML(status || "—")}</span>`;
}

export function formatDate(value, options = {}) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("tg-TJ", { day: "2-digit", month: "short", year: "numeric", ...options }).format(date);
}

export function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("tg-TJ", { hour: "2-digit", minute: "2-digit" }).format(date);
}

export function formatRelative(value) {
  if (!value) return "—";
  const date = new Date(value);
  const diff = date.getTime() - Date.now();
  const abs = Math.abs(diff);
  const formatter = new Intl.RelativeTimeFormat("tg-TJ", { numeric: "auto" });
  if (abs < 60_000) return formatter.format(Math.round(diff / 1000), "second");
  if (abs < 3_600_000) return formatter.format(Math.round(diff / 60_000), "minute");
  if (abs < 86_400_000) return formatter.format(Math.round(diff / 3_600_000), "hour");
  if (abs < 604_800_000) return formatter.format(Math.round(diff / 86_400_000), "day");
  return formatDate(value);
}

export function formatMoney(value, currency = "TJS") {
  const number = Number(value || 0);
  try {
    return new Intl.NumberFormat("tg-TJ", { style: "currency", currency: currency || "TJS", maximumFractionDigits: 2 }).format(number);
  } catch (_) {
    return `${number.toFixed(2)} ${escapeHTML(currency || "TJS")}`;
  }
}

export function debounce(callback, wait = 350) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), wait);
  };
}

export function setButtonLoading(button, loading, label = "Интизор шавед...") {
  if (!button) return;
  if (loading) {
    button.dataset.originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="loading-spinner"></span><span>${escapeHTML(label)}</span>`;
  } else {
    button.disabled = false;
    if (button.dataset.originalHtml) button.innerHTML = button.dataset.originalHtml;
  }
}

export function emptyState({ iconName = "info", title, text, action = "" }) {
  return `<div class="empty-state"><div><div class="empty-icon">${icon(iconName)}</div><h3>${escapeHTML(title)}</h3><p>${escapeHTML(text)}</p>${action}</div></div>`;
}

export function pageSkeleton() {
  return `<div class="page page-skeleton"><div class="skeleton hero"></div><div class="skeleton-grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>`;
}

export function toast(title, message = "", type = "success", timeout = 4200) {
  const region = document.querySelector("#toast-region");
  if (!region) return;
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.innerHTML = `<span class="toast-status">${icon(type === "error" ? "alert" : "checkCircle")}</span><span class="toast-copy"><strong>${escapeHTML(title)}</strong>${message ? `<span>${escapeHTML(message)}</span>` : ""}</span><button class="toast-close" type="button" aria-label="Пӯшидан">${icon("close")}</button>`;
  region.append(element);
  const close = () => element.remove();
  element.querySelector("button").addEventListener("click", close);
  window.setTimeout(close, timeout);
}

export function closeModal() {
  if (modalEscapeHandler) document.removeEventListener("keydown", modalEscapeHandler);
  modalEscapeHandler = null;
  document.dispatchEvent(new CustomEvent("munis:modal-closed"));
  document.querySelector("#portal").innerHTML = "";
  document.body.style.overflow = "";
}

export function openModal({ title, body, footer = "", wide = false, onOpen = null }) {
  const portal = document.querySelector("#portal");
  portal.innerHTML = `<div class="modal-backdrop" data-modal-backdrop><section class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header class="modal-head"><h2 id="modal-title">${escapeHTML(title)}</h2><button class="btn btn-ghost btn-icon" type="button" data-modal-close aria-label="Пӯшидан">${icon("close")}</button></header><div class="modal-body">${body}</div>${footer ? `<footer class="modal-foot">${footer}</footer>` : ""}</section></div>`;
  document.body.style.overflow = "hidden";
  const backdrop = portal.querySelector("[data-modal-backdrop]");
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) closeModal(); });
  portal.querySelectorAll("[data-modal-close]").forEach((button) => button.addEventListener("click", closeModal));
  if (modalEscapeHandler) document.removeEventListener("keydown", modalEscapeHandler);
  modalEscapeHandler = (event) => {
    if (event.key === "Escape") {
      closeModal();
    }
  };
  document.addEventListener("keydown", modalEscapeHandler);
  const first = portal.querySelector("input:not([type=hidden]), button, select, textarea");
  if (first) window.setTimeout(() => first.focus(), 0);
  if (onOpen) onOpen(portal.querySelector(".modal"));
  return portal.querySelector(".modal");
}

export function confirmAction({ title, message, confirmText = "Тасдиқ", danger = false }) {
  return new Promise((resolve) => {
    let accepted = false;
    document.addEventListener("munis:modal-closed", () => {
      if (!accepted) resolve(false);
    }, { once: true });
    const modal = openModal({
      title,
      body: `<div class="inline-alert ${danger ? "error" : "warning"}">${icon(danger ? "alert" : "info")}<span>${escapeHTML(message)}</span></div>`,
      footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button><button class="btn ${danger ? "btn-danger" : "btn-primary"}" type="button" data-confirm>${escapeHTML(confirmText)}</button>`,
    });
    modal.querySelector("[data-confirm]").addEventListener("click", () => {
      accepted = true;
      closeModal();
      resolve(true);
    });
  });
}

export function queryString(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}
