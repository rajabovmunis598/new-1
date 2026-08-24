import { api, results } from "./api.js?v=20260823-6";
import {
  avatar, emptyState, escapeHTML, formatRelative, icon, pageSkeleton,
  setButtonLoading, toast,
} from "./ui.js?v=20260823-6";
import { renderLanding } from "./pages/landing.js?v=20260823-6";
import { renderDashboard } from "./pages/dashboard.js?v=20260823-6";
import { renderInbox } from "./pages/inbox.js?v=20260823-6";
import { renderContacts } from "./pages/contacts.js?v=20260823-6";
import { renderOrders } from "./pages/orders.js?v=20260823-6";
import { renderIntegrations } from "./pages/integrations.js?v=20260823-6";
import { renderSettings } from "./pages/settings.js?v=20260823-6";

const routes = {
  "/dashboard": { title: "Шарҳи умумӣ", subtitle: "Имрӯз дар бизнеси шумо чӣ мегузарад", icon: "dashboard", render: renderDashboard },
  "/messages": { title: "Паёмҳо", subtitle: "Telegram, WhatsApp ва Instagram дар як ҷо", icon: "messages", render: renderInbox },
  "/contacts": { title: "Муштариён", subtitle: "Контактҳо ва таърихи муошират", icon: "contacts", render: renderContacts },
  "/orders": { title: "Фармоишҳо", subtitle: "Назорат аз қабул то анҷом", icon: "orders", render: renderOrders },
  "/integrations": { title: "Пайвастҳо", subtitle: "Каналҳои Telegram, WhatsApp ва Instagram", icon: "integrations", render: renderIntegrations },
  "/settings": { title: "Танзимот", subtitle: "Профил, намуди интерфейс ва амният", icon: "settings", render: renderSettings },
};

const mobileRoutes = ["/dashboard", "/messages", "/contacts", "/orders", "/integrations"];
const mobileRouteLabels = {
  "/dashboard": "Шарҳ",
  "/messages": "Паёмҳо",
  "/contacts": "Муштарӣ",
  "/orders": "Фармоиш",
  "/integrations": "Пайваст",
};

function internalNavigationPath(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    const path = url.pathname.replace(/\/$/, "") || "/";
    if (url.origin !== window.location.origin || !routes[path]) return null;
    return `${path}${url.search}${url.hash}`;
  } catch (_) {
    return null;
  }
}

function searchResultIcon(type) {
  return ({ contact: "contacts", conversation: "messages", message: "messages", order: "orders" })[type] || "search";
}

function brandMarkup() {
  return `<span class="brand-mark" aria-hidden="true"></span><span class="brand-copy"><span>MUNIS</span><small>Business Hub</small></span>`;
}

function authPreviewRow(name, color, active = false) {
  return `<div class="preview-row ${active ? "active" : ""}"><span class="avatar sm" style="background:${color}">${escapeHTML(name[0])}</span><span style="flex:1"><span class="preview-line"></span><span class="preview-line"></span></span>${active ? '<span class="unread-count">2</span>' : ""}</div>`;
}

class MunisApp {
  constructor() {
    this.root = document.querySelector("#app");
    this.user = null;
    this.activeRefresh = null;
    this.activeRouteCleanup = null;
    this.routeVersion = 0;
    this.returnPath = "/dashboard";
    this.socketStatus = "disconnected";
    this.commandPaletteClose = null;
  }

  get main() { return this.root.querySelector("#main-content") || this.root; }

  cleanupActiveRoute() {
    const cleanup = this.activeRouteCleanup;
    this.activeRouteCleanup = null;
    if (typeof cleanup !== "function") return;
    try { cleanup(); } catch (_) { /* Route cleanup must never block navigation. */ }
  }

  setRouteCleanup(cleanup, version = this.routeVersion) {
    if (typeof cleanup !== "function") return false;
    if (version !== this.routeVersion) {
      try { cleanup(); } catch (_) { /* A stale route cleans up immediately. */ }
      return false;
    }
    this.cleanupActiveRoute();
    this.activeRouteCleanup = cleanup;
    return true;
  }

  async start() {
    this.applyTheme(localStorage.getItem("munis_theme") || "light");
    document.addEventListener("click", (event) => {
      const commandTarget = event.target.closest("[data-command-palette]");
      if (commandTarget) {
        event.preventDefault();
        if (this.user) this.openCommandPalette(commandTarget);
        return;
      }
      const target = event.target.closest("[data-nav]");
      if (!target) return;
      event.preventDefault();
      this.navigate(target.dataset.nav);
    });
    document.addEventListener("keydown", (event) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.key.toLowerCase() !== "k") return;
      event.preventDefault();
      if (!this.user) return;
      if (this.commandPaletteClose) this.commandPaletteClose();
      else this.openCommandPalette(document.activeElement);
    });
    window.addEventListener("popstate", () => this.renderRoute());

    if (api.authenticated) {
      try { this.user = await api.get("/api/auth/me/"); }
      catch (_) { api.clearTokens(); }
    }
    await this.renderRoute();
    if (this.user) this.connectRealtime();
  }

  applyTheme(theme) {
    const safeTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = safeTheme;
    localStorage.setItem("munis_theme", safeTheme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", safeTheme === "dark" ? "#080d17" : "#111827");
  }

  async navigate(path) {
    if (!path) return;
    history.pushState({}, "", path);
    await this.renderRoute();
  }

  async renderRoute() {
    if (this.commandPaletteClose) this.commandPaletteClose({ restoreFocus: false });
    const version = ++this.routeVersion;
    this.cleanupActiveRoute();
    this.activeRefresh = null;
    const path = window.location.pathname.replace(/\/$/, "") || "/";

    if (path === "/") {
      api.disconnectSocket();
      this.root.innerHTML = "";
      renderLanding(this);
      return;
    }

    if (path === "/login" || path === "/register") {
      if (this.user) {
        history.replaceState({}, "", "/dashboard");
        return this.renderRoute();
      }
      api.disconnectSocket();
      this.renderAuth(path === "/register" ? "register" : "login");
      return;
    }

    let route = routes[path];
    if (!route) {
      history.replaceState({}, "", this.user ? "/dashboard" : "/");
      return this.renderRoute();
    }
    if (!this.user) {
      this.returnPath = `${window.location.pathname}${window.location.search}`;
      history.replaceState({}, "", "/login");
      this.renderAuth("login");
      return;
    }

    this.ensureShell();
    this.updateRouteUI(path, route);
    this.main.innerHTML = pageSkeleton();
    try {
      await route.render(this);
      if (version !== this.routeVersion) return;
      window.scrollTo({ top: 0, behavior: "auto" });
      document.title = `${route.title} · Munis Business Hub`;
    } catch (error) {
      if (version === this.routeVersion) this.renderError(error, () => this.renderRoute());
    }
    if (!api.socket && this.user) this.connectRealtime();
  }

  renderAuth(mode = "login") {
    const register = mode === "register";
    document.title = `${register ? "Сохтани ҳисоб" : "Воридшавӣ"} · Munis Business Hub`;
    this.root.innerHTML = `<main class="auth-shell">
      <section class="auth-visual" aria-label="Munis Business Hub">
        <a class="brand" href="/" data-nav="/">${brandMarkup()}</a>
        <div class="auth-copy">
          <div class="auth-kicker">Communication, бе парокандагӣ</div>
          <h1>Ҳамаи паёмҳои бизнес дар як ҷо.</h1>
          <p>Telegram, WhatsApp, Instagram, муштариён ва фармоишҳоро аз як dashboard-и равшан идора кунед.</p>
          <div class="auth-platforms"><span class="auth-platform"><i style="background:#35a8e8"></i>Telegram</span><span class="auth-platform"><i style="background:#31d069"></i>WhatsApp</span><span class="auth-platform"><i style="background:#d62976"></i>Instagram</span></div>
          <div class="auth-preview">${authPreviewRow("Али", "#6558ee", true)}${authPreviewRow("Манижа", "#16a34a")}${authPreviewRow("Фарид", "#2481cc")}</div>
        </div>
        <div class="auth-footer">© 2026 Munis Business Hub · Муоширати муназзами бизнес</div>
      </section>
      <section class="auth-panel">
        <div class="auth-card">
          <a class="brand mobile-brand" href="/" data-nav="/">${brandMarkup()}</a>
          <div class="eyebrow">${register ? "Оғози кори нав" : "Хуш омадед"}</div>
          <h2>${register ? "Ҳисоб созед" : "Ба ҳисоб ворид шавед"}</h2>
          <p>${register ? "Маълумоти худро ворид кунед — кор ҳамагӣ як дақиқа мегирад." : "Барои идома почтаи электронӣ ва рамзро ворид кунед."}</p>
          <div id="auth-alert"></div>
          ${register ? this.registerForm() : this.loginForm()}
          <div class="auth-switch">${register ? "Аллакай ҳисоб доред?" : "Ҳоло ҳисоб надоред?"} <button type="button" data-nav="${register ? "/login" : "/register"}">${register ? "Ворид шудан" : "Сохтани ҳисоб"}</button></div>
        </div>
      </section>
    </main>`;
    this.bindAuth(mode);
  }

  loginForm() {
    return `<form class="form-grid" id="auth-form">
      <label class="field"><span class="field-label">Почтаи электронӣ</span><input class="field-input" name="email" type="email" autocomplete="email" required placeholder="name@company.tj"></label>
      <label class="field"><span class="field-label">Рамз</span><span class="password-wrap"><input class="field-input" name="password" type="password" autocomplete="current-password" required placeholder="Рамзи шумо"><button class="password-toggle" type="button" data-password-toggle aria-label="Нишон додани рамз">${icon("eye")}</button></span></label>
      <button class="btn btn-primary btn-wide" type="submit">Ворид шудан ${icon("chevronRight")}</button>
      <div class="form-note">JWT-сессия танҳо дар ҳамин вкладка нигоҳ дошта мешавад ва баъди баромадан пурра тоза мегардад.</div>
    </form>`;
  }

  registerForm() {
    return `<form class="form-grid" id="auth-form">
      <div class="form-grid two"><label class="field"><span class="field-label">Ном <span class="optional">(ихтиёрӣ)</span></span><input class="field-input" name="first_name" autocomplete="given-name" maxlength="150"></label><label class="field"><span class="field-label">Насаб <span class="optional">(ихтиёрӣ)</span></span><input class="field-input" name="last_name" autocomplete="family-name" maxlength="150"></label></div>
      <label class="field"><span class="field-label">Номи корбар</span><input class="field-input" name="username" autocomplete="username" required maxlength="150" placeholder="munis_shop"></label>
      <label class="field"><span class="field-label">Почтаи электронӣ</span><input class="field-input" name="email" type="email" autocomplete="email" required placeholder="name@company.tj"></label>
      <label class="field"><span class="field-label">Рамз</span><span class="password-wrap"><input class="field-input" name="password" type="password" autocomplete="new-password" minlength="8" required placeholder="Камаш 8 аломат"><button class="password-toggle" type="button" data-password-toggle aria-label="Нишон додани рамз">${icon("eye")}</button></span></label>
      <label class="field"><span class="field-label">Такрори рамз</span><input class="field-input" name="password_confirm" type="password" autocomplete="new-password" minlength="8" required placeholder="Рамзро такрор кунед"></label>
      <button class="btn btn-primary btn-wide" type="submit">Сохтани ҳисоб ${icon("chevronRight")}</button>
      <div class="form-note">Бо сохтани ҳисоб шумо тасдиқ мекунед, ки танҳо аккаунтҳо ва маълумоти худатонро истифода мебаред.</div>
    </form>`;
  }

  bindAuth(mode) {
    this.root.querySelector("[data-password-toggle]")?.addEventListener("click", (event) => {
      const input = event.currentTarget.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
      event.currentTarget.innerHTML = icon(input.type === "password" ? "eye" : "eyeOff");
    });
    this.root.querySelector("#auth-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      const button = form.querySelector("button[type=submit]");
      const alert = this.root.querySelector("#auth-alert");
      const payload = Object.fromEntries(new FormData(form));
      alert.innerHTML = "";
      if (mode === "register" && payload.password !== payload.password_confirm) {
        alert.innerHTML = `<div class="inline-alert error" style="margin-bottom:16px">${icon("alert")}<span>Рамзҳо яксон нестанд.</span></div>`;
        return;
      }
      delete payload.password_confirm;
      Object.keys(payload).forEach((key) => { if (payload[key] === "") delete payload[key]; });
      setButtonLoading(button, true, mode === "register" ? "Сохтани ҳисоб..." : "Воридшавӣ...");
      try {
        this.user = mode === "register" ? await api.register(payload) : await api.login(payload);
        const destination = this.returnPath || "/dashboard";
        this.returnPath = "/dashboard";
        history.replaceState({}, "", destination);
        toast(mode === "register" ? "Ҳисоб омода шуд" : "Хуш омадед", `Салом, ${this.user.first_name || this.user.username}!`);
        this.connectRealtime();
        await this.renderRoute();
      } catch (error) {
        alert.innerHTML = `<div class="inline-alert error" style="margin-bottom:16px">${icon("alert")}<span>${escapeHTML(error.message)}</span></div>`;
        setButtonLoading(button, false);
      }
    });
  }

  ensureShell() {
    if (this.root.querySelector(".app-shell")) return;
    const commandKey = /Mac|iPhone|iPad/i.test(navigator.platform || "") ? "⌘ K" : "Ctrl K";
    this.root.innerHTML = `<div class="app-shell" id="app-shell">
      <div class="notification-banner" id="notification-banner" role="alert" aria-live="polite"></div>
      <aside class="sidebar">
        <a class="brand" href="/" data-nav="/">${brandMarkup()}</a>
        <div class="nav-label">Фазои корӣ</div>
        <nav class="nav-list" aria-label="Менюи асосӣ">
          ${Object.entries(routes).map(([path, route]) => `<a class="nav-item" href="${path}" data-nav="${path}" data-route-link="${path}">${icon(route.icon)}<span>${route.title}</span>${path === "/messages" ? '<span class="nav-badge hidden" data-unread-badge>0</span>' : ""}</a>`).join("")}
        </nav>
        <div class="sidebar-bottom">
          <div class="sidebar-health"><div class="live-row"><span class="live-dot" id="live-dot"></span><span id="live-label">Пайвастшавӣ...</span></div></div>
          <div class="sidebar-user" id="sidebar-user"></div>
        </div>
      </aside>
      <div class="mobile-overlay hidden" id="mobile-overlay"></div>
      <div class="main-shell">
        <header class="topbar">
          <button class="btn btn-ghost btn-icon menu-toggle" type="button" id="menu-toggle" aria-label="Меню">${icon("menu")}</button>
          <a class="brand mobile-logo" href="/" data-nav="/">${brandMarkup()}</a>
          <div class="topbar-title"><strong id="topbar-title">Dashboard</strong><span id="topbar-subtitle"></span></div>
          <button class="command-trigger" type="button" data-command-palette aria-label="Ҷустуҷӯи зуд ва фармонҳо" aria-keyshortcuts="Control+K Meta+K">${icon("search")}<span>Ҷустуҷӯ ва фармонҳо</span><kbd>${commandKey}</kbd></button>
          <button class="btn btn-ghost btn-icon topbar-action" type="button" id="notification-button" aria-label="Огоҳиномаҳо">${icon("bell")}<span class="notification-dot hidden" id="notification-count">0</span></button>
          <button class="btn btn-ghost btn-icon" type="button" data-nav="/settings" aria-label="Профил" id="topbar-avatar"></button>
        </header>
        <main id="main-content"></main>
      </div>
      <nav class="mobile-bottom-nav" aria-label="Менюи асосии мобилӣ">
        ${mobileRoutes.map((path) => `<a class="mobile-nav-item" href="${path}" data-nav="${path}" data-route-link="${path}"><span class="mobile-nav-icon">${icon(routes[path].icon)}${path === "/messages" ? '<i class="mobile-nav-badge hidden" data-unread-badge>0</i>' : ""}</span><span>${mobileRouteLabels[path]}</span></a>`).join("")}
      </nav>
    </div>`;
    this.root.querySelector("#menu-toggle").addEventListener("click", () => this.toggleSidebar(true));
    this.root.querySelector("#mobile-overlay").addEventListener("click", () => this.toggleSidebar(false));
    this.root.querySelector("#notification-button").addEventListener("click", () => this.openNotifications());
    this.updateUser();
    this.updateSocketStatus(this.socketStatus);
    this.loadShellData();
  }

  updateRouteUI(path, route) {
    this.root.querySelectorAll("[data-route-link]").forEach((link) => {
      const active = link.dataset.routeLink === path;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    this.root.querySelector(".main-shell")?.classList.toggle("inbox-route", path === "/messages");
    this.root.querySelector("#topbar-title").textContent = route.title;
    this.root.querySelector("#topbar-subtitle").textContent = route.subtitle;
    this.toggleSidebar(false);
  }

  toggleSidebar(open) {
    const shell = this.root.querySelector("#app-shell");
    if (!shell) return;
    shell.classList.toggle("sidebar-open", open);
    this.root.querySelector("#mobile-overlay")?.classList.toggle("hidden", !open);
  }

  updateUser() {
    if (!this.user || !this.root.querySelector("#sidebar-user")) return;
    const name = `${this.user.first_name || ""} ${this.user.last_name || ""}`.trim() || this.user.username;
    this.root.querySelector("#sidebar-user").innerHTML = `${avatar({ name, email: this.user.email }, "sm")}<span class="sidebar-user-copy"><strong class="truncate">${escapeHTML(name)}</strong><span class="truncate">${escapeHTML(this.user.email)}</span></span>`;
    this.root.querySelector("#topbar-avatar").innerHTML = avatar({ name, email: this.user.email }, "sm");
  }

  updateUnread(count = 0) {
    this.root.querySelectorAll("[data-unread-badge]").forEach((badge) => {
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.classList.toggle("hidden", !count);
    });
  }

  async loadShellData() {
    if (!this.user || !this.root.querySelector(".app-shell")) return;
    try {
      const [stats, notifications] = await Promise.all([
        api.get("/api/dashboard/statistics/"),
        api.get("/api/notifications/?is_read=false&page_size=1"),
      ]);
      this.updateUnread(stats.unread_messages || 0);
      const count = Number(notifications.count || 0);
      const badge = this.root.querySelector("#notification-count");
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.classList.toggle("hidden", !count);
    } catch (_) { /* Shell remains usable while status data retries later. */ }
  }

  connectRealtime() {
    if (!this.user || window.location.pathname === "/") return;
    api.connectSocket(
      (event) => {
        if (event.type === "new_message") toast("Паёми нав омад", "Рӯйхати суҳбатҳо нав карда шуд.");
        this.loadShellData();
        if (this.activeRefresh) Promise.resolve(this.activeRefresh(event)).catch(() => {});
      },
      (status) => this.updateSocketStatus(status),
    );
  }

  updateSocketStatus(status) {
    this.socketStatus = status;
    const dot = this.root.querySelector("#live-dot");
    const label = this.root.querySelector("#live-label");
    if (!dot || !label) return;
    dot.className = `live-dot ${status}`;
    label.textContent = status === "connected" ? "Навсозии зинда фаъол" : status === "reconnecting" || status === "connecting" ? "Пайвастшавӣ..." : "Навсозии зинда қатъ";
  }

  openCommandPalette(trigger = null) {
    if (this.commandPaletteClose) return;
    const portal = document.querySelector("#portal");
    if (!portal || portal.children.length) return;

    const previousFocus = trigger?.focus ? trigger : document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const shell = this.root.querySelector(".app-shell");
    const shellWasInert = Boolean(shell?.inert);
    const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    const commandKey = /Mac|iPhone|iPad/i.test(navigator.platform || "") ? "⌘ K" : "Ctrl K";
    const routeCommands = Object.entries(routes).map(([path, route]) => ({
      id: `route-${path.slice(1)}`,
      group: "Гузариш",
      title: route.title,
      subtitle: route.subtitle,
      icon: route.icon,
      trailing: path === currentPath ? "Ҳозир" : "Кушодан",
      keywords: `${route.title} ${route.subtitle} ${path}`.toLocaleLowerCase("tg-TJ"),
      action: () => this.navigate(path),
    }));
    const quickCommands = [
      {
        id: "quick-new-order", group: "Амали зуд", title: "Фармоиши нав", subtitle: "Формаи сохтани фармоишро кушоед", icon: "plus", trailing: "Нав",
        keywords: "фармоиш нав сохтан order create",
        action: async () => {
          await this.navigate("/orders");
          this.main.querySelector('[data-action="create"]')?.click();
        },
      },
      {
        id: "quick-connect", group: "Амали зуд", title: "Пайвасти нав", subtitle: "Telegram, WhatsApp ё Instagram", icon: "integrations", trailing: "Канал",
        keywords: "пайваст интегратсия telegram whatsapp instagram connect",
        action: () => this.navigate("/integrations"),
      },
      {
        id: "quick-refresh", group: "Амали зуд", title: "Навсозии саҳифа", subtitle: "Маълумоти саҳифаи ҷориро аз нав гиред", icon: "refresh", trailing: "Refresh",
        keywords: "навсозӣ refresh reload",
        action: async () => {
          if (typeof this.activeRefresh === "function") await this.activeRefresh({ type: "manual" });
          else await this.renderRoute();
          toast("Саҳифа нав шуд");
        },
      },
      {
        id: "quick-theme", group: "Амали зуд", title: document.documentElement.dataset.theme === "dark" ? "Намуди равшан" : "Намуди торик", subtitle: "Ранги интерфейсро иваз кунед", icon: "eye", trailing: "Theme",
        keywords: "ранг намуд торик равшан theme dark light",
        action: () => {
          const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
          this.applyTheme(theme);
          toast(theme === "dark" ? "Намуди торик фаъол шуд" : "Намуди равшан фаъол шуд");
        },
      },
      {
        id: "quick-notifications", group: "Амали зуд", title: "Огоҳиномаҳо", subtitle: "Хабарҳои охиринро бинед", icon: "bell", trailing: "Inbox",
        keywords: "огоҳинома хабар notification",
        action: () => this.openNotifications(),
      },
    ];

    portal.innerHTML = `<div class="command-palette-backdrop" data-command-backdrop>
      <section class="command-palette" role="dialog" aria-modal="true" aria-labelledby="command-title">
        <header class="command-search-row">
          ${icon("search")}
          <label class="sr-only" for="command-search">Ҷустуҷӯи зуд ва фармонҳо</label>
          <input id="command-search" type="search" autocomplete="off" spellcheck="false" placeholder="Саҳифа, муштарӣ, суҳбат, фармоиш ё паём..." aria-controls="command-results" aria-autocomplete="list">
          <kbd>${commandKey}</kbd>
          <button class="command-close" type="button" data-command-close aria-label="Пӯшидани ҷустуҷӯ">${icon("close")}</button>
        </header>
        <div class="command-results" id="command-results" role="listbox" aria-label="Натиҷаҳои ҷустуҷӯ"></div>
        <footer class="command-footer"><span><kbd>↑</kbd><kbd>↓</kbd> интихоб</span><span><kbd>Enter</kbd> кушодан</span><span><kbd>Esc</kbd> пӯшидан</span><output aria-live="polite" data-command-status></output></footer>
      </section>
    </div>`;
    const backdrop = portal.querySelector("[data-command-backdrop]");
    const input = portal.querySelector("#command-search");
    const list = portal.querySelector("#command-results");
    const status = portal.querySelector("[data-command-status]");
    let query = "";
    let remoteItems = [];
    let visibleItems = [];
    let activeIndex = 0;
    let searchTimer = null;
    let requestVersion = 0;
    let loading = false;
    let searchFailed = false;

    const close = ({ restoreFocus = true } = {}) => {
      if (this.commandPaletteClose !== close) return;
      if (searchTimer) window.clearTimeout(searchTimer);
      requestVersion += 1;
      this.commandPaletteClose = null;
      portal.innerHTML = "";
      document.body.style.overflow = previousOverflow;
      if (shell && "inert" in shell) shell.inert = shellWasInert;
      if (restoreFocus && previousFocus?.isConnected && typeof previousFocus.focus === "function") {
        try { previousFocus.focus({ preventScroll: true }); } catch (_) { previousFocus.focus(); }
      }
    };
    this.commandPaletteClose = close;
    document.body.style.overflow = "hidden";
    if (shell && "inert" in shell) shell.inert = true;

    const resultTypeLabel = (type) => ({ contact: "Муштарӣ", conversation: "Суҳбат", message: "Паём", order: "Фармоиш" })[type] || "Натиҷа";
    const renderResults = () => {
      const normalized = query.toLocaleLowerCase("tg-TJ");
      const localItems = normalized
        ? [...routeCommands, ...quickCommands].filter((item) => `${item.title} ${item.subtitle} ${item.keywords}`.toLocaleLowerCase("tg-TJ").includes(normalized))
        : [...routeCommands, ...quickCommands];
      visibleItems = [...localItems, ...remoteItems];
      activeIndex = visibleItems.length ? Math.min(Math.max(activeIndex, 0), visibleItems.length - 1) : -1;

      if (!visibleItems.length && !loading) {
        list.innerHTML = `<div class="command-empty">${icon(searchFailed ? "alert" : "search")}<strong>${searchFailed ? "Ҷустуҷӯ дастрас нест" : "Натиҷа ёфт нашуд"}</strong><span>${searchFailed ? "Navigation ва амалҳои зуд ҳамоно кор мекунанд." : "Калимаи дигарро санҷед."}</span></div>`;
      } else {
        let lastGroup = "";
        list.innerHTML = visibleItems.map((item, index) => {
          const group = item.group || "Натиҷаҳо";
          const heading = group !== lastGroup ? `<div class="command-group-label">${escapeHTML(group)}</div>` : "";
          lastGroup = group;
          return `${heading}<button class="command-item" id="command-option-${index}" type="button" role="option" aria-selected="${index === activeIndex}" data-command-index="${index}">
            <span class="command-item-icon">${icon(item.icon || "search")}</span>
            <span class="command-item-copy"><strong>${escapeHTML(item.title)}</strong><span>${escapeHTML(item.subtitle || "")}</span></span>
            <small>${escapeHTML(item.trailing || "")}</small>
          </button>`;
        }).join("") + (loading ? `<div class="command-loading"><span class="loading-spinner" aria-hidden="true"></span> Ҷустуҷӯ дар маълумот...</div>` : "");
      }
      const active = activeIndex >= 0 ? list.querySelector(`[data-command-index="${activeIndex}"]`) : null;
      if (active) {
        input.setAttribute("aria-activedescendant", active.id);
        active.scrollIntoView({ block: "nearest" });
      } else {
        input.removeAttribute("aria-activedescendant");
      }
      status.textContent = loading ? "Ҷустуҷӯ идома дорад" : `${visibleItems.length} натиҷа`;
    };

    const runItem = async (index) => {
      const item = visibleItems[index];
      if (!item) return;
      close({ restoreFocus: false });
      try {
        await item.action();
      } catch (error) {
        toast("Амал иҷро нашуд", error?.message || "Дубора кӯшиш кунед.", "error");
      }
    };

    const scheduleRemoteSearch = () => {
      query = input.value.trim();
      remoteItems = [];
      searchFailed = false;
      activeIndex = 0;
      requestVersion += 1;
      const version = requestVersion;
      if (searchTimer) window.clearTimeout(searchTimer);
      searchTimer = null;
      if (query.length < 2) {
        loading = false;
        renderResults();
        return;
      }
      loading = true;
      renderResults();
      searchTimer = window.setTimeout(async () => {
        try {
          const data = await api.get(`/api/search/?q=${encodeURIComponent(query)}`);
          if (version !== requestVersion || this.commandPaletteClose !== close) return;
          remoteItems = (Array.isArray(data?.results) ? data.results : []).slice(0, 20).flatMap((item, index) => {
            const path = internalNavigationPath(item.url);
            if (!path) return [];
            const detail = [item.subtitle, item.platform, item.status].filter(Boolean).join(" · ");
            return [{
              id: `search-${item.type || "result"}-${item.id ?? index}`,
              group: "Натиҷаҳо",
              title: String(item.title || "Натиҷа"),
              subtitle: detail,
              icon: searchResultIcon(item.type),
              trailing: resultTypeLabel(item.type),
              action: () => this.navigate(path),
            }];
          });
        } catch (_) {
          if (version !== requestVersion || this.commandPaletteClose !== close) return;
          searchFailed = true;
        } finally {
          if (version === requestVersion && this.commandPaletteClose === close) {
            loading = false;
            renderResults();
          }
        }
      }, 220);
    };

    input.addEventListener("input", scheduleRemoteSearch);
    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!visibleItems.length) return;
        activeIndex = (activeIndex + (event.key === "ArrowDown" ? 1 : -1) + visibleItems.length) % visibleItems.length;
        renderResults();
      } else if (event.key === "Home" && visibleItems.length) {
        event.preventDefault();
        activeIndex = 0;
        renderResults();
      } else if (event.key === "End" && visibleItems.length) {
        event.preventDefault();
        activeIndex = visibleItems.length - 1;
        renderResults();
      } else if (event.key === "Enter") {
        event.preventDefault();
        void runItem(activeIndex);
      }
    });
    list.addEventListener("click", (event) => {
      const item = event.target.closest("[data-command-index]");
      if (item) void runItem(Number(item.dataset.commandIndex));
    });
    list.addEventListener("pointermove", (event) => {
      const item = event.target.closest("[data-command-index]");
      if (!item) return;
      const next = Number(item.dataset.commandIndex);
      if (next === activeIndex) return;
      activeIndex = next;
      list.querySelectorAll("[data-command-index]").forEach((button) => button.setAttribute("aria-selected", String(Number(button.dataset.commandIndex) === activeIndex)));
      input.setAttribute("aria-activedescendant", item.id);
    });
    backdrop.addEventListener("click", (event) => { if (event.target === backdrop) close(); });
    portal.querySelector("[data-command-close]").addEventListener("click", () => close());
    backdrop.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "Tab") {
        const focusable = [...backdrop.querySelectorAll('input, button:not([disabled]), [href]')];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });

    renderResults();
    window.setTimeout(() => input.focus(), 0);
  }

  async openNotifications() {
    const portal = document.querySelector("#portal");
    portal.innerHTML = `<div class="drawer-backdrop" data-drawer-backdrop><aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="notification-title"><header class="drawer-head"><h2 id="notification-title">Огоҳиномаҳо</h2><button class="btn btn-ghost btn-sm" type="button" data-read-all>Ҳамааш хонда шуд</button><button class="btn btn-ghost btn-icon" type="button" data-drawer-close aria-label="Пӯшидан">${icon("close")}</button></header><div class="drawer-body" id="notification-list"><div class="empty-state"><span class="loading-spinner" style="color:var(--primary)"></span></div></div></aside></div>`;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event) => { if (event.key === "Escape") close(); };
    const close = () => {
      document.removeEventListener("keydown", closeOnEscape);
      portal.innerHTML = "";
      document.body.style.overflow = "";
    };
    document.addEventListener("keydown", closeOnEscape);
    portal.querySelector("[data-drawer-close]").addEventListener("click", close);
    portal.querySelector("[data-drawer-backdrop]").addEventListener("click", (event) => { if (event.target === event.currentTarget) close(); });

    const renderList = async () => {
      try {
        const data = await api.get("/api/notifications/?page_size=50");
        const notifications = results(data);
        const list = portal.querySelector("#notification-list");
        if (!list) return;
        list.innerHTML = notifications.length ? notifications.map((item) => `<button class="notification-item ${item.is_read ? "" : "unread"}" type="button" data-notification-id="${item.id}" data-notification-type="${escapeHTML(item.type)}"><span class="notification-icon">${icon(item.type === "new_order" ? "orders" : item.type === "integration_error" || item.type === "message_failed" ? "alert" : item.type === "new_message" ? "messages" : "info")}</span><span class="notification-copy"><strong>${escapeHTML(item.title)}</strong><p>${escapeHTML(item.message || "")}</p><time>${escapeHTML(formatRelative(item.created_at))}</time></span></button>`).join("") : emptyState({ iconName: "bell", title: "Огоҳиномаи нав нест", text: "Ҳамаи хабарҳо хонда шудаанд." });
        list.querySelectorAll("[data-notification-id]").forEach((button) => button.addEventListener("click", async () => {
          try { await api.post(`/api/notifications/${button.dataset.notificationId}/read/`); } catch (_) { /* Navigation still works. */ }
          const destination = button.dataset.notificationType === "new_order" ? "/orders" : button.dataset.notificationType === "integration_error" ? "/integrations" : "/messages";
          close();
          this.loadShellData();
          this.navigate(destination);
        }));
      } catch (error) {
        const list = portal.querySelector("#notification-list");
        if (list) list.innerHTML = emptyState({ iconName: "alert", title: "Огоҳиномаҳо бор нашуданд", text: error.message });
      }
    };
    portal.querySelector("[data-read-all]").addEventListener("click", async () => {
      try { await api.post("/api/notifications/read-all/"); await renderList(); await this.loadShellData(); toast("Ҳамаи огоҳиномаҳо хонда шуданд"); }
      catch (error) { toast("Амал иҷро нашуд", error.message, "error"); }
    });
    await renderList();
  }

  renderError(error, retry) {
    this.main.innerHTML = `<div class="page"><header class="page-header"><div><div class="eyebrow">Хатои муваққатӣ</div><h1>Саҳифа бор нашуд</h1><p>${escapeHTML(error?.message || "Дархост иҷро нашуд.")}</p></div></header><section class="card">${emptyState({ iconName: "alert", title: "Пайваст ё серверро санҷед", text: "Маълумоти шумо бехатар аст. Метавонед дархостро дубора иҷро кунед.", action: '<button class="btn btn-primary" type="button" data-retry-page>Дубора кӯшиш</button>' })}</section></div>`;
    this.main.querySelector("[data-retry-page]")?.addEventListener("click", retry);
  }

  async logout() {
    try { await api.logout(); }
    catch (_) { api.clearTokens(); }
    this.user = null;
    history.replaceState({}, "", "/");
    toast("Аз ҳисоб баромадед");
    await this.renderRoute();
  }
}

const app = new MunisApp();
app.start();
