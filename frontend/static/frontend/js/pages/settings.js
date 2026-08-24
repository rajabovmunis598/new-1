import { api } from "../api.js?v=20260822-8";
import { avatar, escapeHTML, formatDate, icon, setButtonLoading, toast } from "../ui.js?v=20260822-8";

function preference(key, fallback = true) {
  const value = localStorage.getItem(`munis_pref_${key}`);
  return value === null ? fallback : value === "true";
}

function switchRow(key, title, description, checked) {
  return `<div class="settings-row"><div class="settings-row-copy"><strong>${escapeHTML(title)}</strong><span>${escapeHTML(description)}</span></div><label class="switch"><input type="checkbox" data-preference="${escapeHTML(key)}" ${checked ? "checked" : ""}><span></span></label></div>`;
}

export async function renderSettings(app) {
  const user = app.user;
  const theme = document.documentElement.dataset.theme || "light";
  app.main.innerHTML = `<div class="page">
    <header class="page-header"><div><div class="eyebrow">Ҳисоб ва афзалиятҳо</div><h1>Танзимот</h1><p>Профил, намуди система ва огоҳиномаҳои худро идора кунед.</p></div></header>
    <div class="settings-layout">
      <nav class="card settings-nav" aria-label="Қисмҳои танзимот">
        <button class="active" type="button" data-settings-target="profile">${icon("user")} Профил</button>
        <button type="button" data-settings-target="appearance">${icon("eye")} Намуд</button>
        <button type="button" data-settings-target="notifications">${icon("bell")} Огоҳиномаҳо</button>
        <button type="button" data-settings-target="security">${icon("lock")} Амният</button>
      </nav>
      <main>
        <section class="card settings-section" id="profile">
          <header class="card-head"><div><h2>Маълумоти шахсӣ</h2><span class="muted">Профили дар интерфейс нишоншаванда</span></div>${avatar({ name: `${user.first_name} ${user.last_name}`.trim() || user.username, email: user.email })}</header>
          <div class="card-body">
            <form class="form-grid" id="profile-form">
              <div class="form-grid two">
                <label class="field"><span class="field-label">Ном</span><input class="field-input" name="first_name" maxlength="150" value="${escapeHTML(user.first_name || "")}" placeholder="Ном"></label>
                <label class="field"><span class="field-label">Насаб</span><input class="field-input" name="last_name" maxlength="150" value="${escapeHTML(user.last_name || "")}" placeholder="Насаб"></label>
              </div>
              <label class="field"><span class="field-label">Номи корбар</span><input class="field-input" name="username" maxlength="150" required value="${escapeHTML(user.username || "")}"></label>
              <label class="field"><span class="field-label">Почтаи электронӣ</span><input class="field-input" name="email" type="email" required value="${escapeHTML(user.email || "")}"></label>
              <div class="cluster"><button class="btn btn-primary" type="submit">${icon("check")} Нигоҳ доштан</button><span class="muted">Ҳисоб аз ${escapeHTML(formatDate(user.created_at))}</span></div>
            </form>
          </div>
        </section>

        <section class="card settings-section" id="appearance">
          <header class="card-head"><div><h2>Намуди интерфейс</h2><span class="muted">Реҷаи мувофиқро барои чашм интихоб кунед</span></div></header>
          <div class="card-body">
            <div class="theme-options">
              <button class="theme-option ${theme === "light" ? "active" : ""}" type="button" data-theme-choice="light"><span class="theme-preview"><span></span></span><strong>Равшан</strong></button>
              <button class="theme-option ${theme === "dark" ? "active" : ""}" type="button" data-theme-choice="dark"><span class="theme-preview dark"><span></span></span><strong>Торик</strong></button>
            </div>
          </div>
        </section>

        <section class="card settings-section" id="notifications">
          <header class="card-head"><div><h2>Огоҳиномаҳо</h2><span class="muted">Кадом рӯйдодҳоро фавран бинед</span></div></header>
          <div class="card-body">
            ${switchRow("messages", "Паёми нав", "Ҳангоми омадани паём аз муштарӣ огоҳ кунед.", preference("messages"))}
            ${switchRow("orders", "Фармоиши нав", "Дар бораи фармоишҳои нав огоҳ кунед.", preference("orders"))}
            ${switchRow("errors", "Хатои пайваст", "Ҳангоми қатъ шудани Telegram ё WhatsApp хабар диҳед.", preference("errors"))}
          </div>
        </section>

        <section class="card settings-section" id="security">
          <header class="card-head"><div><h2>Амният ва сессия</h2><span class="muted">JWT ва маълумоти махфӣ муҳофизат мешаванд</span></div></header>
          <div class="card-body">
            <div class="inline-alert success">${icon("checkCircle")}<span>Сессияи шумо фаъол аст. Калидҳои Telegram ва WhatsApp ҳеҷ гоҳ аз сервер дубора нишон дода намешаванд.</span></div>
            <div class="settings-row"><div class="settings-row-copy"><strong>Сессияи ҷорӣ</strong><span>Токенҳо танҳо дар ҳамин вкладкаи браузер нигоҳ дошта мешаванд.</span></div><span class="status-badge active">Фаъол</span></div>
            <div class="settings-row"><div class="settings-row-copy"><strong>Баромадан аз ҳисоб</strong><span>Токени refresh бекор ва маълумоти сессия тоза мешавад.</span></div><button class="btn btn-danger" type="button" data-settings-logout>${icon("logout")} Баромадан</button></div>
          </div>
        </section>
      </main>
    </div>
  </div>`;

  app.main.querySelector("#profile-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type=submit]");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setButtonLoading(button, true, "Нигоҳдорӣ...");
    try {
      app.user = await api.patch("/api/auth/me/", data);
      app.updateUser();
      toast("Профил нав шуд");
    } catch (error) { toast("Профил нав нашуд", error.message, "error"); }
    finally { setButtonLoading(button, false); }
  });

  app.main.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      app.applyTheme(button.dataset.themeChoice);
      app.main.querySelectorAll("[data-theme-choice]").forEach((item) => item.classList.toggle("active", item === button));
      toast("Намуди интерфейс тағйир ёфт");
    });
  });
  app.main.querySelectorAll("[data-preference]").forEach((input) => {
    input.addEventListener("change", () => {
      localStorage.setItem(`munis_pref_${input.dataset.preference}`, String(input.checked));
      toast("Афзалият нигоҳ дошта шуд");
    });
  });
  app.main.querySelectorAll("[data-settings-target]").forEach((button) => {
    button.addEventListener("click", () => {
      app.main.querySelectorAll("[data-settings-target]").forEach((item) => item.classList.toggle("active", item === button));
      app.main.querySelector(`#${button.dataset.settingsTarget}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  app.main.querySelector("[data-settings-logout]").addEventListener("click", () => app.logout());
}
