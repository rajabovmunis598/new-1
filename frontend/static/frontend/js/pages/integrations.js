import { api, results } from "../api.js?v=20260822-8";
import {
  closeModal,
  confirmAction,
  emptyState,
  escapeHTML,
  formatDate,
  formatRelative,
  icon,
  openModal,
  pageSkeleton,
  safeUrl,
  setButtonLoading,
  statusBadge,
  toast,
} from "../ui.js?v=20260824-3";

const platformCopy = {
  telegram: {
    title: "Telegram",
    description: "Ҳисоби оддии Telegram тавассути MTProto",
    icon: "send",
  },
  whatsapp: {
    title: "WhatsApp",
    description: "WhatsApp Business тавассути Cloud API",
    icon: "phone",
  },
  instagram: {
    title: "Instagram",
    description: "Instagram Business тавассути OAuth-и расмӣ",
    icon: "instagram",
  },
  facebook: {
    title: "Facebook",
    description: "Facebook Messenger тавассути Graph API",
    icon: "facebook",
  },
  viber: {
    title: "Viber",
    description: "Viber Bot тавассути REST API",
    icon: "viber",
  },
  vk: {
    title: "VK",
    description: "VK Community тавассути Callback API",
    icon: "vk",
  },
};

const platformSoft = {
  telegram: "#e8f4fd",
  whatsapp: "#e8f8ee",
  instagram: "#fce8f3",
  facebook: "#e8f0fd",
  viber: "#efedff",
  vk: "#e6f2ff",
};

const connectDetails = {
  telegram: "Рақами телефонро тасдиқ кунед ва паёмҳоро аз ҳисоби корӣ қабул намоед.",
  whatsapp: "Маълумоти Cloud API-ро ворид кунед ва webhook-ро ба Meta илова намоед.",
  instagram: "Бо OAuth-и расмӣ ворид шавед — логин ё гузарвожаи Instagram дар Munis ворид намешавад.",
  facebook: "Бо OAuth-и расмӣ ворид шавед — логин ё гузарвожаи Facebook дар Munis ворид намешавад.",
  viber: "Bot token-и Viber-ро ворид кунед. Баъд webhook URL-и корти Viber-ро дар Viber Admin Panel сабт кунед.",
  vk: "Маълумоти Community VK-ро ворид кунед. Callback URL ва confirmation code дар танзимоти Community истифода мешаванд.",
};

function webhookUrl(integration = {}) {
  return integration.webhook_url || "";
}

function integrationName(integration) {
  return integration.name || platformCopy[integration.platform]?.title || "Пайваст";
}

function errorMessage(error, fallback) {
  const message = String(error?.message || "").trim();
  return message || fallback;
}

function setFormError(scope, message) {
  const alert = scope.querySelector("[data-form-error]");
  if (!alert) return;
  const copy = alert.querySelector("span");
  if (copy) copy.textContent = message;
  alert.classList.remove("hidden");
}

function clearFormError(scope) {
  scope.querySelector("[data-form-error]")?.classList.add("hidden");
}

function formError() {
  return `<div class="inline-alert error hidden" role="alert" data-form-error>
    ${icon("alert")}<span></span>
  </div>`;
}

function postAndForget(path, payload, inputs, keys) {
  try {
    return api.post(path, { ...payload });
  } finally {
    inputs.forEach((input) => { input.value = ""; });
    keys.forEach((key) => { payload[key] = ""; });
  }
}

async function copyText(value) {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("copy failed");
}

async function copyWebhook(integration = {}) {
  const value = webhookUrl(integration);
  if (!value) {
    toast("Callback URL дастрас нест", "Пайвасти WhatsApp-ро аз нав созед.", "error");
    return;
  }
  try {
    await copyText(value);
    toast("Нусха гирифта шуд", "Суроғаи webhook ба ҳофиза гузошта шуд.");
  } catch (_) {
    toast("Нусхабардорӣ нашуд", "Суроғаро интихоб карда, дастӣ нусха гиред.", "error");
  }
}

function connectCard(platform) {
  const copy = platformCopy[platform];
  const detail = connectDetails[platform];
  const demoButton = ["vk", "instagram", "facebook"].includes(platform)
    ? `<button class="btn btn-secondary" type="button" data-page-action="demo-${platform}">Demo барои презентатсия</button>`
    : "";
  return `<article class="card connect-card">
    <div>
      <div class="connect-card-icon" style="color:var(--${platform})">${icon(copy.icon)}</div>
      <h2>${copy.title}-ро пайваст кунед</h2>
      <p>${detail}</p>
      <button class="btn btn-primary" type="button" data-page-action="connect-${platform}">
        ${icon("plus")} Пайваст кардан
      </button>${demoButton}
    </div>
  </article>`;
}

function metaValue(value, fallback = "Таъин нашудааст") {
  return value ? escapeHTML(value) : fallback;
}

function actionButtons(integration) {
  const id = escapeHTML(integration.id);
  const platform = platformCopy[integration.platform] ? integration.platform : "telegram";
  const buttons = [];

  if (platform === "telegram" && integration.status === "pending") {
    buttons.push(`<button class="btn btn-primary btn-sm" type="button" data-integration-action="continue" data-integration-id="${id}">${icon("phone")} Идомаи тасдиқ</button>`);
  }

  if (platform === "whatsapp" && integration.status === "active") {
    buttons.push(`<button class="btn btn-soft btn-sm" type="button" data-integration-action="test" data-integration-id="${id}">${icon("wifi")} Санҷидан</button>`);
  }

  if (["inactive", "error"].includes(integration.status)) {
    buttons.push(`<button class="btn btn-primary btn-sm" type="button" data-page-action="connect-${platform}">${icon("refresh")} Пайвасти нав</button>`);
  }

  buttons.push(`<button class="btn btn-secondary btn-sm" type="button" data-integration-action="rename" data-integration-id="${id}">${icon("edit")} Номгузорӣ</button>`);

  if (integration.status !== "inactive") {
    buttons.push(`<button class="btn btn-secondary btn-sm" type="button" data-integration-action="disconnect" data-integration-id="${id}">${icon("logout")} Қатъ кардан</button>`);
  }

  buttons.push(`<button class="btn btn-ghost btn-sm danger-text" type="button" data-integration-action="delete" data-integration-id="${id}">${icon("trash")} Ҳазф</button>`);
  return buttons.join("");
}

function integrationCard(integration) {
  const platform = platformCopy[integration.platform] ? integration.platform : "telegram";
  const copy = platformCopy[platform];
  const sync = integration.last_sync_at ? formatRelative(integration.last_sync_at) : "Ҳанӯз ҳамоҳанг нашудааст";
  const created = integration.created_at ? formatDate(integration.created_at) : "-";
  const id = escapeHTML(integration.id);
  const webhook = ["whatsapp", "viber", "vk"].includes(platform) ? webhookUrl(integration) : "";

  return `<article class="card integration-card" style="--integration-soft:${platformSoft[platform] || "var(--primary-soft)"}">
    <div class="integration-card-top">
      <span class="platform-icon ${platform}">${icon(copy.icon)}</span>
      <div class="integration-copy">
        <h2>${escapeHTML(integrationName(integration))}</h2>
        <p>${copy.description}</p>
      </div>
      ${statusBadge(integration.status)}
    </div>

    <div class="integration-meta">
      <div><span>Ҳисоби беруна</span><strong>${metaValue(integration.external_account_id)}</strong></div>
      <div><span>Ҳамоҳангсозии охирин</span><strong>${escapeHTML(sync)}</strong></div>
      <div><span>Санаи пайвастшавӣ</span><strong>${escapeHTML(created)}</strong></div>
      <div><span>Муҳофизат</span><strong>Маълумоти махфӣ пинҳон аст</strong></div>
    </div>

    ${integration.last_error ? `<div class="inline-alert error" style="margin-bottom:16px">${icon("alert")}<span>${escapeHTML(integration.last_error)}</span></div>` : ""}

    ${webhook ? `<div class="webhook-box" style="margin-bottom:16px">
      ${icon("external")}
      <code>${escapeHTML(webhook)}</code>
      <button class="btn btn-ghost btn-icon btn-sm" type="button" data-integration-action="copy-webhook" data-integration-id="${id}" aria-label="Нусха гирифтани webhook">${icon("copy")}</button>
    </div>` : ""}

    <div class="integration-actions">${actionButtons(integration)}</div>
  </article>`;
}

function pageMarkup(integrations) {
  const hasTelegram = integrations.some((item) => item.platform === "telegram");
  const hasWhatsApp = integrations.some((item) => item.platform === "whatsapp");
  const hasInstagram = integrations.some((item) => item.platform === "instagram");
  const hasFacebook = integrations.some((item) => item.platform === "facebook");
  const hasViber = integrations.some((item) => item.platform === "viber");
  const hasVK = integrations.some((item) => item.platform === "vk");
  const tiles = integrations.map(integrationCard);
  if (!hasTelegram) tiles.push(connectCard("telegram"));
  if (!hasWhatsApp) tiles.push(connectCard("whatsapp"));
  if (!hasInstagram) tiles.push(connectCard("instagram"));
  if (!hasFacebook) tiles.push(connectCard("facebook"));
  if (!hasViber) tiles.push(connectCard("viber"));
  if (!hasVK) tiles.push(connectCard("vk"));

  return `<div class="page" data-integrations-page>
    <header class="page-header">
      <div>
        <div class="eyebrow">Каналҳои муошират</div>
        <h1>Интегратсияҳо</h1>
        <p>Ҳисобҳои Telegram, WhatsApp Business ва Instagram Business-ро пайваст ва ҳолати онҳоро аз як ҷой идора кунед.</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" type="button" data-page-action="connect-telegram">${icon("send")} Telegram</button>
        <button class="btn btn-secondary" type="button" data-page-action="connect-whatsapp">${icon("phone")} WhatsApp</button>
        <button class="btn btn-primary" type="button" data-page-action="connect-instagram">${icon("instagram")} Instagram</button>
        <button class="btn btn-secondary" type="button" data-page-action="connect-facebook">${icon("facebook")} Facebook</button>
        <button class="btn btn-secondary" type="button" data-page-action="connect-viber">${icon("viber")} Viber</button>
        <button class="btn btn-secondary" type="button" data-page-action="connect-vk">${icon("vk")} VK</button>
      </div>
    </header>

    <section class="integration-grid" aria-label="Рӯйхати интегратсияҳо" data-state="${integrations.length ? "ready" : "empty"}">
      ${tiles.join("")}
    </section>
  </div>`;
}

function wizardSteps(step) {
  const steps = ["Маълумот", "Рамз", "2FA"];
  return `<div class="wizard-steps" aria-label="Марҳилаҳои пайвастшавӣ">
    ${steps.map((label, index) => {
      const number = index + 1;
      const state = step === number ? "active" : step > number ? "done" : "";
      return `${index ? '<span class="wizard-line"></span>' : ""}<span class="wizard-step ${state}"><i>${number}</i><span>${label}</span></span>`;
    }).join("")}
  </div>`;
}

function maskPhone(phone) {
  const value = String(phone || "").trim();
  if (value.length < 7) return value;
  return `${value.slice(0, 4)} ••• •• ${value.slice(-2)}`;
}

function openTelegramWizard(app, pendingIntegration = null) {
  const state = {
    step: pendingIntegration ? 2 : 1,
    integrationId: pendingIntegration?.id || null,
    phoneLabel: "рақами воридшуда",
    created: false,
    completed: false,
  };
  const modal = openModal({
    title: "Пайваст кардани Telegram",
    body: '<div data-telegram-wizard></div>',
  });
  const host = modal.querySelector("[data-telegram-wizard]");
  let refreshScheduled = false;

  const refreshPendingOnClose = () => {
    if (!state.created || state.completed || refreshScheduled) return;
    refreshScheduled = true;
    window.setTimeout(() => renderIntegrations(app), 0);
  };
  modal.querySelectorAll("[data-modal-close]").forEach((button) => button.addEventListener("click", refreshPendingOnClose));
  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(() => {
      if (modal.isConnected) return;
      observer.disconnect();
      refreshPendingOnClose();
    });
    observer.observe(document.querySelector("#portal"), { childList: true });
  }

  function renderStep() {
    if (state.step === 1) {
      host.innerHTML = `${wizardSteps(1)}
        <form class="form-grid" autocomplete="off" data-telegram-start>
          <div class="credential-note">${icon("info")}<span>API ID ва API Hash-ро аз my.telegram.org гиред. API Hash махфӣ аст ва баъди фиристодан дигар намоиш дода намешавад. Ин пайвастшавӣ Bot API нест.</span></div>
          ${formError()}
          <label class="field">
            <span class="field-label">Номи пайваст</span>
            <input class="field-input" name="name" maxlength="255" value="Telegram" required>
          </label>
          <div class="form-grid two">
            <label class="field">
              <span class="field-label">Telegram API ID</span>
              <input class="field-input" name="api_id" type="text" inputmode="numeric" autocomplete="off" spellcheck="false" maxlength="20" placeholder="12345678" required>
              <span class="field-hint">Аз бахши API development tools дар my.telegram.org.</span>
            </label>
            <label class="field">
              <span class="field-label">Telegram API Hash</span>
              <input class="field-input" name="api_hash" type="password" autocomplete="new-password" spellcheck="false" minlength="32" maxlength="32" pattern="[0-9a-fA-F]{32}" required>
              <span class="field-hint">Ин калиди махфиро ба каси дигар нафиристед.</span>
            </label>
          </div>
          <label class="field">
            <span class="field-label">Рақами телефон</span>
            <input class="field-input" name="phone" type="tel" inputmode="tel" autocomplete="tel" maxlength="32" placeholder="+992 90 123 45 67" required>
            <span class="field-hint">Рақамро бо рамзи кишвар ворид кунед.</span>
          </label>
          <button class="btn btn-primary btn-wide" type="submit" data-submit>${icon("send")} Фиристодани рамз</button>
        </form>`;

      const form = host.querySelector("[data-telegram-start]");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearFormError(form);
        const name = form.elements.name.value.trim();
        const phone = form.elements.phone.value.trim();
        const apiIdInput = form.elements.api_id;
        const apiHashInput = form.elements.api_hash;
        const apiId = apiIdInput.value.trim();
        const apiHash = apiHashInput.value.trim();
        if (!name || !phone || !apiId || !apiHash) {
          setFormError(form, "Ном, API ID, API Hash ва рақами телефонро пурра ворид кунед.");
          return;
        }
        if (!/^\d+$/.test(apiId)) {
          setFormError(form, "Telegram API ID бояд танҳо аз рақамҳо иборат бошад.");
          return;
        }
        if (!/^[0-9a-fA-F]{32}$/.test(apiHash)) {
          setFormError(form, "Telegram API Hash бояд аз 32 аломати hexadecimal иборат бошад.");
          return;
        }

        const button = form.querySelector("[data-submit]");
        setButtonLoading(button, true, "Фиристода истодааст...");
        const payload = { name, phone, api_id: apiId, api_hash: apiHash };
        try {
          const request = postAndForget(
            "/api/integrations/telegram/connect/start/",
            payload,
            [apiIdInput, apiHashInput],
            ["api_id", "api_hash"],
          );
          const data = await request;
          state.integrationId = data.integration_id;
          state.phoneLabel = maskPhone(phone);
          state.created = true;
          state.step = 2;
          try { await app.loadShellData(); } catch (_) { /* The wizard can continue without shell refresh. */ }
          renderStep();
        } catch (error) {
          setFormError(form, errorMessage(error, "Фиристодани рамз муяссар нашуд. Дубора кӯшиш кунед."));
          setButtonLoading(button, false);
        }
      });
    } else if (state.step === 2) {
      host.innerHTML = `${wizardSteps(2)}
        <form class="form-grid" autocomplete="off" data-telegram-verify>
          <div class="inline-alert success">${icon("checkCircle")}<span>Рамзи Telegram ба ${escapeHTML(state.phoneLabel)} фиристода шуд.</span></div>
          ${formError()}
          <label class="field">
            <span class="field-label">Рамзи тасдиқ</span>
            <input class="field-input" name="code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="16" placeholder="12345" required>
            <span class="field-hint">Рамз танҳо барои ҳамин тасдиқ истифода мешавад ва нигоҳ дошта намешавад.</span>
          </label>
          <button class="btn btn-primary btn-wide" type="submit" data-submit>${icon("check")} Тасдиқ кардан</button>
        </form>`;

      const form = host.querySelector("[data-telegram-verify]");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearFormError(form);
        const codeInput = form.elements.code;
        const code = codeInput.value.replace(/\s+/g, "");
        if (!code) {
          setFormError(form, "Рамзи тасдиқро ворид кунед.");
          return;
        }

        const button = form.querySelector("[data-submit]");
        setButtonLoading(button, true, "Санҷида истодааст...");
        const payload = { integration_id: state.integrationId, code };
        try {
          const request = postAndForget(
            "/api/integrations/telegram/connect/verify/",
            payload,
            [codeInput],
            ["code"],
          );
          const data = await request;
          if (data.requires_2fa) {
            state.step = 3;
            renderStep();
            return;
          }
          state.completed = true;
          closeModal();
          toast("Telegram пайваст шуд", "Ҳисоб фаъол аст ва барои қабул кардани паёмҳо омода мебошад.");
          await refreshAfterMutation(app);
        } catch (error) {
          setFormError(form, errorMessage(error, "Рамз қабул нашуд. Рамзи навтаринро дубора ворид кунед."));
          setButtonLoading(button, false);
        }
      });
    } else {
      host.innerHTML = `${wizardSteps(3)}
        <form class="form-grid" autocomplete="off" data-telegram-2fa>
          <div class="credential-note">${icon("lock")}<span>Дар ҳисоби шумо муҳофизати дуқадамӣ фаъол аст. Гузарвожа танҳо ба сервер фиристода мешавад ва дар браузер нигоҳ дошта намешавад.</span></div>
          ${formError()}
          <label class="field">
            <span class="field-label">Гузарвожаи 2FA</span>
            <input class="field-input" name="password" type="password" autocomplete="new-password" spellcheck="false" required>
          </label>
          <button class="btn btn-primary btn-wide" type="submit" data-submit>${icon("lock")} Анҷом додани пайваст</button>
        </form>`;

      const form = host.querySelector("[data-telegram-2fa]");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearFormError(form);
        const passwordInput = form.elements.password;
        if (!passwordInput.value) {
          setFormError(form, "Гузарвожаи 2FA-ро ворид кунед.");
          return;
        }

        const button = form.querySelector("[data-submit]");
        setButtonLoading(button, true, "Пайваст карда истодааст...");
        const payload = { integration_id: state.integrationId, password: passwordInput.value };
        try {
          const request = postAndForget(
            "/api/integrations/telegram/connect/2fa/",
            payload,
            [passwordInput],
            ["password"],
          );
          await request;
          state.completed = true;
          closeModal();
          toast("Telegram пайваст шуд", "Тасдиқи дуқадамӣ бомуваффақият анҷом ёфт.");
          await refreshAfterMutation(app);
        } catch (error) {
          setFormError(form, errorMessage(error, "Гузарвожа қабул нашуд. Онро дубора ворид кунед."));
          setButtonLoading(button, false);
        }
      });
    }

    window.setTimeout(() => host.querySelector("input")?.focus(), 0);
  }

  renderStep();
}

function openBotChannelForm(app, platform) {
  const isViber = platform === "viber";
  const fields = isViber
    ? `<label class="field"><span class="field-label">Viber Auth Token</span><input class="field-input" name="auth_token" type="password" autocomplete="new-password" required><span class="field-hint">Аз Viber Admin Panel → Bot → Edit Info гиред.</span></label>`
    : `<div class="form-grid two"><label class="field"><span class="field-label">Group ID</span><input class="field-input" name="group_id" inputmode="numeric" required></label><label class="field"><span class="field-label">API version</span><input class="field-input" name="api_version" value="5.199"></label></div><label class="field"><span class="field-label">Community Access Token</span><input class="field-input" name="access_token" type="password" autocomplete="new-password" required></label><div class="form-grid two"><label class="field"><span class="field-label">Secret</span><input class="field-input" name="secret" type="password" autocomplete="new-password" required></label><label class="field"><span class="field-label">Confirmation code</span><input class="field-input" name="confirmation" required></label></div>`;
  const formId = `${platform}-connect-form`;
  const modal = openModal({
    title: `Пайваст кардани ${platform === "vk" ? "VK" : "Viber"}`,
    body: `<form id="${formId}" class="form-grid" autocomplete="off" data-bot-channel-form>${formError()}<label class="field"><span class="field-label">Номи пайваст</span><input class="field-input" name="name" value="${platform === "vk" ? "VK" : "Viber"}" required></label>${fields}<div class="credential-note">${icon("info")}<span>Баъд аз пайвастшавӣ webhook URL-ро дар танзимоти ${platform === "vk" ? "VK Community" : "Viber Bot"} ворид кунед.</span></div></form>`,
    footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button><button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("check")} Пайваст кардан</button>`,
  });
  const form = modal.querySelector("[data-bot-channel-form]");
  const submit = modal.querySelector("[data-submit]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    const payload = Object.fromEntries(new FormData(form).entries());
    const path = `/api/integrations/${platform}/connect/`;
    setButtonLoading(submit, true, "Пайваст шуда истодааст...");
    try {
      await api.post(path, payload);
      closeModal();
      toast(`${platform === "vk" ? "VK" : "Viber"} пайваст шуд`, "Webhook URL-ро дар панели платформа сабт кунед.");
      await refreshAfterMutation(app);
    } catch (error) {
      setFormError(form, errorMessage(error, "Пайвастшавӣ ноком шуд."));
      setButtonLoading(submit, false);
    }
  });
}

function openVKOAuth(app) {
  (async () => {
    try {
      const data = await api.post("/api/integrations/vk/oauth/start/", {});
      const url = safeUrl(data?.authorization_url || "");
      if (url === "#") throw new Error("VK OAuth URL was not returned by the server.");
      window.location.assign(url);
    } catch (error) {
      const message = errorMessage(error, "VK OAuth дар сервер танзим нашудааст.");
      if (/VK_APP_ID|OAuth/i.test(message)) {
        try {
          const demo = await api.post("/api/integrations/vk/demo/", {});
          toast("VK Demo пайваст шуд", "Паёмҳои намунавӣ барои намоиш омодаанд.");
          await app.loadShellData();
          return demo;
        } catch (demoError) {
          toast("VK пайваст нашуд", errorMessage(demoError, message), "error");
          return null;
        }
      }
      toast("VK пайваст нашуд", message, "error");
    }
  })();
}

function openDemoForm(app, platform) {
  const title = { vk: "VK Demo", instagram: "Instagram Demo", facebook: "Facebook Demo" }[platform] || "Demo";
  const formId = `demo-${platform}-form`;
  const modal = openModal({
    title: `Пайваст кардани ${title}`,
    body: `<form id="${formId}" class="form-grid" autocomplete="off">
      ${formError()}
      <label class="field"><span class="field-label">Номи аккаунт</span><input class="field-input" name="name" value="${title}" required></label>
      <label class="field"><span class="field-label">Account ID</span><input class="field-input" name="account_id" placeholder="demo-account"></label>
      <label class="field"><span class="field-label">Access Token (ихтиёрӣ барои намоиш)</span><input class="field-input" name="access_token" type="password" autocomplete="off"><span class="field-hint">Ин ҳолати Demo аст; token дар база нигоҳ дошта намешавад ва ба платформа фиристода намешавад.</span></label>
      <div class="credential-note">${icon("info")}<span>Ин пайвасти маҳаллии намоишӣ мебошад, на Instagram/Facebook-и воқеӣ.</span></div>
    </form>`,
    footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button><button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("check")} Пайваст кардан</button>`,
  });
  const form = modal.querySelector("form");
  const submit = modal.querySelector("[data-submit]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    setButtonLoading(submit, true, "Пайваст шуда истодааст...");
    try {
      await api.post(`/api/integrations/${platform}/demo/`, Object.fromEntries(new FormData(form).entries()));
      closeModal();
      toast(`${title} пайваст шуд`, "Чати намунавӣ барои презентатсия омода аст.");
      await refreshAfterMutation(app);
    } catch (error) {
      setFormError(form, errorMessage(error, "Пайвасткунии Demo иҷро нашуд."));
      setButtonLoading(submit, false);
    }
  });
}

async function consumeVKOAuth(app) {
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const state = hash.get("state");
  const tokenKey = [...hash.keys()].find((key) => /^access_token(?:_\d+)?$/.test(key));
  const token = tokenKey ? hash.get(tokenKey) : "";
  if (!state || !token) return;
  const groupMatch = tokenKey.match(/^access_token_(\d+)$/);
  try {
    const data = await api.post("/api/integrations/vk/oauth/complete/", {
      state,
      access_token: token,
      group_id: groupMatch?.[1] || "",
    });
    if (data?.next_authorization_url) {
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}`);
      window.location.assign(safeUrl(data.next_authorization_url));
      return;
    }
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}`);
    toast("VK пайваст шуд", `${data?.integration?.name || "VK Community"} ба Munis пайваст шуд.`);
    await app.loadShellData();
  } catch (error) {
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}`);
    toast("VK пайваст нашуд", errorMessage(error, "VK OAuth ноком шуд."), "error");
  }
}

function openWhatsAppForm(app) {
  const formId = "whatsapp-connect-form";
  const modal = openModal({
    title: "Пайваст кардани WhatsApp",
    wide: true,
    body: `<form id="${formId}" class="form-grid" autocomplete="off" data-whatsapp-form>
      <div class="credential-note">${icon("lock")}<span>Token ва калидҳои махфӣ рамзгузорӣ мешаванд. Баъди фиристодан онҳо дигар намоиш дода намешаванд.</span></div>
      ${formError()}
      <div class="form-grid two">
        <label class="field">
          <span class="field-label">Номи пайваст</span>
          <input class="field-input" name="name" maxlength="255" value="WhatsApp" required>
        </label>
        <label class="field">
          <span class="field-label">Phone Number ID</span>
          <input class="field-input" name="phone_number_id" inputmode="numeric" autocomplete="off" placeholder="123456789012345" required>
        </label>
        <label class="field">
          <span class="field-label">Business Account ID <span class="optional">ихтиёрӣ</span></span>
          <input class="field-input" name="business_account_id" inputmode="numeric" autocomplete="off" placeholder="123456789012345">
        </label>
        <label class="field">
          <span class="field-label">Access Token</span>
          <input class="field-input" name="access_token" type="password" autocomplete="new-password" spellcheck="false" required>
        </label>
        <label class="field">
          <span class="field-label">App Secret</span>
          <input class="field-input" name="app_secret" type="password" autocomplete="new-password" spellcheck="false" required>
        </label>
        <label class="field">
          <span class="field-label">Verify Token</span>
          <input class="field-input" name="verify_token" type="password" autocomplete="new-password" spellcheck="false" required>
        </label>
      </div>
      <div class="credential-note">${icon("info")}<span>Баъди пайвастшавӣ Callback URL-и махсуси ҳамин ҳисоб дар корти WhatsApp нишон дода мешавад. Онро дар Webhooks-и Meta ворид кунед.</span></div>
    </form>`,
    footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button>
      <button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("check")} Пайваст кардан</button>`,
  });
  const form = modal.querySelector("[data-whatsapp-form]");
  const submit = modal.querySelector("[data-submit]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    const payload = {
      name: form.elements.name.value.trim(),
      phone_number_id: form.elements.phone_number_id.value.trim(),
      business_account_id: form.elements.business_account_id.value.trim(),
      access_token: form.elements.access_token.value,
      app_secret: form.elements.app_secret.value,
      verify_token: form.elements.verify_token.value,
    };
    if (!payload.name || !payload.phone_number_id || !payload.access_token || !payload.app_secret || !payload.verify_token) {
      setFormError(form, "Ном, Phone Number ID, Access Token, App Secret ва Verify Token ҳатмӣ мебошанд.");
      return;
    }

    setButtonLoading(submit, true, "Пайваст карда истодааст...");
    try {
      const request = postAndForget(
        "/api/integrations/whatsapp/connect/",
        payload,
        [form.elements.access_token, form.elements.app_secret, form.elements.verify_token],
        ["access_token", "app_secret", "verify_token"],
      );
      await request;
      closeModal();
      toast("WhatsApp пайваст шуд", "Cloud API фаъол аст. Акнун webhook-ро дар Meta сабт кунед.");
      await refreshAfterMutation(app);
    } catch (error) {
      setFormError(form, errorMessage(error, "Пайвастшавӣ анҷом нашуд. Маълумотро санҷед ва қиматҳои махфиро дубора ворид кунед."));
      setButtonLoading(submit, false);
    }
  });
}

function openInstagramWizard(app) {
  // Instagram OAuth is configured once on the server. Users should never
  // have to copy App ID, App Secret, Verify Token, or an access token.
  // Start the official Instagram authorization flow immediately.
  (async () => {
    try {
      const data = await api.post("/api/integrations/instagram/connect/start/", {
        name: app?.name || "Instagram",
      });
      const authorizationUrl = safeUrl(data?.authorization_url || "");
      if (authorizationUrl === "#") {
        throw new Error("Instagram OAuth URL was not returned by the server.");
      }
      window.location.assign(authorizationUrl);
    } catch (error) {
      toast(
        "Instagram пайваст нашуд",
        errorMessage(
          error,
          "Instagram-ро пайваст карда натавонистем. Танзимоти серверро санҷед.",
        ),
        "error",
      );
    }
  })();
  return;

  const formId = "instagram-connect-form";
  const modal = openModal({
    title: "Пайваст кардани Instagram",
    wide: true,
    body: `<div data-instagram-wizard>
      <div class="wizard-steps" aria-label="Марҳилаҳои пайвастшавӣ">
        <span class="wizard-step active"><i>1</i><span>Роҳнамо</span></span>
        <span class="wizard-line"></span>
        <span class="wizard-step"><i>2</i><span>Калидҳо</span></span>
        <span class="wizard-line"></span>
        <span class="wizard-step"><i>3</i><span>Пайвастшавӣ</span></span>
      </div>
      <div data-instagram-step-1>
        <div style="padding:20px 0">
          <h3 style="margin:0 0 16px;font-size:18px;letter-spacing:-.02em">Чӣ тавр Instagram Business-ро пайваст кардан лозим аст</h3>
          <p style="color:var(--muted);margin:0 0 20px;line-height:1.7">Барои пайваст кардани Instagram Business ба Munis, шумо бояд App-и нав дар Meta for Developers созед. Ин 5 дақиқа вақт мегирад.</p>

          <div style="display:grid;gap:14px">
            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">1</span>
              <div>
                <strong style="font-size:14px">Meta for Developers кушоед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Ба <a href="https://developers.facebook.com" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:underline">developers.facebook.com</a> гузаред ва бо ҳисоби Facebook-и худ ворид шавед.</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">2</span>
              <div>
                <strong style="font-size:14px">App-и нав созед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Тугмаи <strong>Create App</strong> → типи <strong>Business</strong>-ро интихоб кунед. Ном ва Email-ро пурра кунед.</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">3</span>
              <div>
                <strong style="font-size:14px">Instagram Graph API илова кунед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар бахши <strong>Add Products</strong> → <strong>Instagram Graph API</strong>-ро фаъол кунед. Scopes: <code style="background:var(--surface-soft);padding:2px 6px;border-radius:4px;font-size:11px">instagram_business_basic, instagram_business_manage_messages</code></p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">4</span>
              <div>
                <strong style="font-size:14px">Калидҳоро гиред</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар бахши <strong>Basic → Settings</strong>: <strong>App ID</strong> ва <strong>App Secret</strong>-ро нусхабардорӣ кунед. <strong>App Secret</strong> танҳо як маротиба намоиш дода мешавад!</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">5</span>
              <div>
                <strong style="font-size:14px">Valid OAuth Redirect URIs илова кунед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар Instagram → <strong>Settings → Valid OAuth Redirect URIs</strong>:<br><code style="background:var(--surface-soft);padding:4px 8px;border-radius:4px;font-size:11px;display:inline-block;margin-top:4px;word-break:break-all">${window.location.origin}/api/integrations/instagram/connect/callback/</code></p>
              </div>
            </div>
          </div>

          <div style="margin-top:20px;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface-soft)">
            <p style="margin:0;font-size:12px;color:var(--muted);line-height:1.6">${icon("info")} <strong>Шахсият:</strong> Логин ё гузарвожаи Instagram дар Munis ворид намешавад. Танҳо калидҳои API истифода мешаванд ва ба сервер рамзгузорӣ мешаванд.</p>
          </div>

          <div style="margin-top:20px;display:flex;gap:10px;justify-content:flex-end">
            <button class="btn btn-secondary" type="button" data-modal-close>Бекор</button>
            <button class="btn btn-primary" type="button" data-instagram-next-step>Идома ${icon("chevronRight")}</button>
          </div>
        </div>
      </div>
      <div data-instagram-step-2 style="display:none">
        <form id="${formId}" class="form-grid" autocomplete="off" data-instagram-form>
          <div class="credential-note">${icon("lock")}<span>Калидҳо рамзгузорӣ мешаванд. Баъди фиристодан онҳо дигар намоиш дода намешаванд.</span></div>
          ${formError()}
          <label class="field">
            <span class="field-label">Номи пайваст</span>
            <input class="field-input" name="name" maxlength="255" value="Instagram" required>
          </label>
          <div class="form-grid two" style="display:none">
            <label class="field">
              <span class="field-label">App ID</span>
              <input class="field-input" name="app_id" inputmode="numeric" autocomplete="off" spellcheck="false" maxlength="64" placeholder="123456789012345">
              <span class="field-hint">Аз бахши Basic → Settings дар Meta for Developers.</span>
            </label>
            <label class="field">
              <span class="field-label">App Secret</span>
              <input class="field-input" name="app_secret" type="password" autocomplete="new-password" spellcheck="false">
              <span class="field-hint">Дар ҳамон бахш. Танҳо як маротиба намоиш дода мешавад!</span>
            </label>
          </div>
          <label class="field" style="display:none">
            <span class="field-label">Verify Token</span>
            <input class="field-input" name="verify_token" type="password" autocomplete="new-password" spellcheck="false" minlength="8" maxlength="255" placeholder="Мисол: munis_instagram_verify_2026">
            <span class="field-hint">Ҳар як калими дилхоҳ истифода баред. Ин барои тасдиқи webhook лозим аст.</span>
          </label>
          <div class="credential-note">${icon("info")}<span>Баъди пайвастшавӣ Callback URL-и махсуси ҳамин ҳисоб дар корти Instagram нишон дода мешавад. Онро дар Valid OAuth Redirect URIs ворид кунед.</span></div>
          <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
            <button class="btn btn-secondary" type="button" data-instagram-prev-step>${icon("chevronLeft")} Бозгашт</button>
            <button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("instagram")} Пайваст кардан</button>
          </div>
        </form>
      </div>
    </div>`,
  });

  const host = modal.querySelector("[data-instagram-wizard]");
  const step1 = host.querySelector("[data-instagram-step-1]");
  const step2 = host.querySelector("[data-instagram-step-2]");
  const steps = host.querySelectorAll(".wizard-step");

  host.querySelector("[data-instagram-next-step]").addEventListener("click", () => {
    step1.style.display = "none";
    step2.style.display = "block";
    steps[0].classList.remove("active");
    steps[0].classList.add("done");
    steps[1].classList.add("active");
    window.setTimeout(() => step2.querySelector("input")?.focus(), 0);
  });

  host.querySelector("[data-instagram-prev-step]").addEventListener("click", () => {
    step2.style.display = "none";
    step1.style.display = "block";
    steps[1].classList.remove("active");
    steps[0].classList.remove("done");
    steps[0].classList.add("active");
  });

  const form = host.querySelector("[data-instagram-form]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    const payload = {
      name: form.elements.name.value.trim(),
      app_id: form.elements.app_id?.value.trim() || "",
      app_secret: form.elements.app_secret?.value || "",
      verify_token: form.elements.verify_token?.value || "",
    };
    if (!payload.name) {
      setFormError(form, "Ҳамаи майдонҳоро пурра ворид кунед.");
      return;
    }
    if (payload.app_id && (payload.app_id.length < 5 || !/^\d+$/.test(payload.app_id))) {
      setFormError(form, "App ID бояд аз рақамҳо иборат бошад (камаш 5 рақам).");
      return;
    }
    if (payload.verify_token && payload.verify_token.length < 8) {
      setFormError(form, "Verify Token бояд камаш 8 аломат бошад.");
      return;
    }

    const submit = form.querySelector("[data-submit]");
    setButtonLoading(submit, true, "Ба Instagram мегузарем...");
    try {
      const data = await api.post("/api/integrations/instagram/connect/start/", payload);
      const authorizationUrl = safeUrl(data?.authorization_url || "");
      if (authorizationUrl === "#") throw new Error("Суроғаи OAuth аз сервер гирифта нашуд.");
      window.location.assign(authorizationUrl);
    } catch (error) {
      toast(
        "Instagram пайваст нашуд",
        errorMessage(error, "Оғози OAuth муяссар нашуд. Калидҳоро санҷед ва дубора кӯшиш кунед."),
        "error",
      );
      setButtonLoading(submit, false);
    }
  });
}

function consumeInstagramCallback() {
  const url = new URL(window.location.href);
  const outcome = url.searchParams.get("instagram");
  if (!["connected", "error"].includes(outcome)) return;

  url.searchParams.delete("instagram");
  history.replaceState(history.state, "", `${url.pathname}${url.search}${url.hash}`);
  if (outcome === "connected") {
    toast("Instagram пайваст шуд", "Ҳисоби Business фаъол аст ва паёмҳо дар Inbox пайдо мешаванд.");
  } else {
    toast("Instagram пайваст нашуд", "Иҷозати OAuth анҷом наёфт. Дубора кӯшиш кунед.", "error");
  }
}

function openFacebookWizard(app) {
  (async () => {
    try {
      const data = await api.post("/api/integrations/facebook/connect/start/", { name: "Facebook" });
      const authorizationUrl = safeUrl(data?.authorization_url || "");
      if (authorizationUrl === "#") throw new Error("Facebook OAuth URL was not returned by the server.");
      window.location.assign(authorizationUrl);
    } catch (error) {
      toast("Facebook пайваст нашуд", errorMessage(error, "Facebook OAuth дар сервер танзим нашудааст."), "error");
    }
  })();
  return;

  const formId = "facebook-connect-form";
  const modal = openModal({
    title: "Пайваст кардани Facebook",
    wide: true,
    body: `<div data-facebook-wizard>
      <div class="wizard-steps" aria-label="Марҳилаҳои пайвастшавӣ">
        <span class="wizard-step active"><i>1</i><span>Роҳнамо</span></span>
        <span class="wizard-line"></span>
        <span class="wizard-step"><i>2</i><span>Калидҳо</span></span>
        <span class="wizard-line"></span>
        <span class="wizard-step"><i>3</i><span>Пайвастшавӣ</span></span>
      </div>
      <div data-facebook-step-1>
        <div style="padding:20px 0">
          <h3 style="margin:0 0 16px;font-size:18px;letter-spacing:-.02em">Чӣ тавр Facebook Messenger-ро пайваст кардан лозим аст</h3>
          <p style="color:var(--muted);margin:0 0 20px;line-height:1.7">Барои пайваст кардани Facebook Messenger ба Munis, шумо бояд App-и нав дар Meta for Developers созед.</p>

          <div style="display:grid;gap:14px">
            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">1</span>
              <div>
                <strong style="font-size:14px">Meta for Developers кушоед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Ба <a href="https://developers.facebook.com" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:underline">developers.facebook.com</a> гузаред ва бо ҳисоби Facebook-и худ ворид шавед.</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">2</span>
              <div>
                <strong style="font-size:14px">App-и нав созед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Тугмаи <strong>Create App</strong> → типи <strong>Business</strong>-ро интихоб кунед. Ном ва Email-ро пурра кунед.</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">3</span>
              <div>
                <strong style="font-size:14px">Messenger Platform илова кунед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар бахши <strong>Add Products</strong> → <strong>Messenger</strong>-ро фаъол кунед. Scopes: <code style="background:var(--surface-soft);padding:2px 6px;border-radius:4px;font-size:11px">pages_messaging, pages_show_list, pages_manage_metadata</code></p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">4</span>
              <div>
                <strong style="font-size:14px">Калидҳоро гиред</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар бахши <strong>Basic → Settings</strong>: <strong>App ID</strong> ва <strong>App Secret</strong>-ро нусхабардорӣ кунед. <strong>App Secret</strong> танҳо як маротиба намоиш дода мешавад!</p>
              </div>
            </div>

            <div style="display:flex;gap:14px;align-items:start">
              <span style="min-width:32px;height:32px;display:grid;place-items:center;border-radius:10px;background:var(--primary-soft);color:var(--primary);font-size:13px;font-weight:800;flex:0 0 32px">5</span>
              <div>
                <strong style="font-size:14px">Valid OAuth Redirect URIs илова кунед</strong>
                <p style="margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.5">Дар Facebook → <strong>Settings → Valid OAuth Redirect URIs</strong>:<br><code style="background:var(--surface-soft);padding:4px 8px;border-radius:4px;font-size:11px;display:inline-block;margin-top:4px;word-break:break-all">${window.location.origin}/api/integrations/facebook/connect/callback/</code></p>
              </div>
            </div>
          </div>

          <div style="margin-top:20px;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface-soft)">
            <p style="margin:0;font-size:12px;color:var(--muted);line-height:1.6">${icon("info")} <strong>Шахсият:</strong> Логин ё гузарвожаи Facebook дар Munis ворид намешавад. Танҳо калидҳои API истифода мешаванд.</p>
          </div>

          <div style="margin-top:20px;display:flex;gap:10px;justify-content:flex-end">
            <button class="btn btn-secondary" type="button" data-modal-close>Бекор</button>
            <button class="btn btn-primary" type="button" data-facebook-next-step>Идома ${icon("chevronRight")}</button>
          </div>
        </div>
      </div>
      <div data-facebook-step-2 style="display:none">
        <form id="${formId}" class="form-grid" autocomplete="off" data-facebook-form>
          <div class="credential-note">${icon("lock")}<span>Калидҳо рамзгузорӣ мешаванд. Баъди фиристодан онҳо дигар намоиш дода намешаванд.</span></div>
          ${formError()}
          <label class="field">
            <span class="field-label">Номи пайваст</span>
            <input class="field-input" name="name" maxlength="255" value="Facebook" required>
          </label>
          <div class="form-grid two">
            <label class="field">
              <span class="field-label">App ID</span>
              <input class="field-input" name="app_id" inputmode="numeric" autocomplete="off" spellcheck="false" maxlength="64" placeholder="123456789012345" required>
              <span class="field-hint">Аз бахши Basic → Settings дар Meta for Developers.</span>
            </label>
            <label class="field">
              <span class="field-label">App Secret</span>
              <input class="field-input" name="app_secret" type="password" autocomplete="new-password" spellcheck="false" required>
              <span class="field-hint">Дар ҳамон бахш. Танҳо як маротиба намоиш дода мешавад!</span>
            </label>
          </div>
          <label class="field">
            <span class="field-label">Verify Token</span>
            <input class="field-input" name="verify_token" type="password" autocomplete="new-password" spellcheck="false" minlength="8" maxlength="255" placeholder="Мисол: munis_facebook_verify_2026" required>
            <span class="field-hint">Ҳар як калими дилхоҳ истифода баред. Ин барои тасдиқи webhook лозим аст.</span>
          </label>
          <div class="credential-note">${icon("info")}<span>Баъди пайвастшавӣ Callback URL-и махсуси ҳамин ҳисоб дар корти Facebook нишон дода мешавад. Онро дар Valid OAuth Redirect URIs ворид кунед.</span></div>
          <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
            <button class="btn btn-secondary" type="button" data-facebook-prev-step>${icon("chevronLeft")} Бозгашт</button>
            <button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("integrations")} Пайваст кардан</button>
          </div>
        </form>
      </div>
    </div>`,
  });

  const host = modal.querySelector("[data-facebook-wizard]");
  const step1 = host.querySelector("[data-facebook-step-1]");
  const step2 = host.querySelector("[data-facebook-step-2]");
  const steps = host.querySelectorAll(".wizard-step");

  host.querySelector("[data-facebook-next-step]").addEventListener("click", () => {
    step1.style.display = "none";
    step2.style.display = "block";
    steps[0].classList.remove("active");
    steps[0].classList.add("done");
    steps[1].classList.add("active");
    window.setTimeout(() => step2.querySelector("input")?.focus(), 0);
  });

  host.querySelector("[data-facebook-prev-step]").addEventListener("click", () => {
    step2.style.display = "none";
    step1.style.display = "block";
    steps[1].classList.remove("active");
    steps[0].classList.remove("done");
    steps[0].classList.add("active");
  });

  const form = host.querySelector("[data-facebook-form]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    const payload = {
      name: form.elements.name.value.trim(),
      app_id: form.elements.app_id.value.trim(),
      app_secret: form.elements.app_secret.value,
      verify_token: form.elements.verify_token.value,
    };
    if (!payload.name || !payload.app_id || !payload.app_secret || !payload.verify_token) {
      setFormError(form, "Ҳамаи майдонҳоро пурра ворид кунед.");
      return;
    }
    if (payload.app_id.length < 5 || !/^\d+$/.test(payload.app_id)) {
      setFormError(form, "App ID бояд аз рақамҳо иборат бошад (камаш 5 рақам).");
      return;
    }
    if (payload.verify_token.length < 8) {
      setFormError(form, "Verify Token бояд камаш 8 аломат бошад.");
      return;
    }

    const submit = form.querySelector("[data-submit]");
    setButtonLoading(submit, true, "Ба Facebook мегузарем...");
    try {
      const data = await api.post("/api/integrations/facebook/connect/start/", payload);
      const authorizationUrl = safeUrl(data?.authorization_url || "");
      if (authorizationUrl === "#") throw new Error("Суроғаи OAuth аз сервер гирифта нашуд.");
      window.location.assign(authorizationUrl);
    } catch (error) {
      toast(
        "Facebook пайваст нашуд",
        errorMessage(error, "Оғози OAuth муяссар нашуд. Калидҳоро санҷед ва дубора кӯшиш кунед."),
        "error",
      );
      setButtonLoading(submit, false);
    }
  });
}

function consumeFacebookCallback() {
  const url = new URL(window.location.href);
  const outcome = url.searchParams.get("facebook");
  if (!["connected", "error"].includes(outcome)) return;

  url.searchParams.delete("facebook");
  history.replaceState(history.state, "", `${url.pathname}${url.search}${url.hash}`);
  if (outcome === "connected") {
    toast("Facebook пайваст шуд", "Ҳисоби Messenger фаъол аст ва паёмҳо дар Inbox пайдо мешаванд.");
  } else {
    toast("Facebook пайваст нашуд", "Иҷозати OAuth анҷом наёфт. Дубора кӯшиш кунед.", "error");
  }
}

function openRenameForm(app, integration) {
  const formId = `rename-integration-${integration.id}`;
  const modal = openModal({
    title: "Тағйир додани ном",
    body: `<form id="${formId}" class="form-grid" data-rename-form>
      ${formError()}
      <label class="field">
        <span class="field-label">Номи пайваст</span>
        <input class="field-input" name="name" maxlength="255" value="${escapeHTML(integrationName(integration))}" required>
        <span class="field-hint">Номи кӯтоҳе интихоб кунед, ки ҳисобро зуд шинохтан мумкин бошад.</span>
      </label>
    </form>`,
    footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button>
      <button class="btn btn-primary" type="submit" form="${formId}" data-submit>${icon("check")} Сабт кардан</button>`,
  });
  const form = modal.querySelector("[data-rename-form]");
  const submit = modal.querySelector("[data-submit]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormError(form);
    const name = form.elements.name.value.trim();
    if (!name) {
      setFormError(form, "Номи пайвастро ворид кунед.");
      return;
    }

    setButtonLoading(submit, true, "Сабт шуда истодааст...");
    try {
      await api.patch(`/api/integrations/${integration.id}/`, { name });
      closeModal();
      toast("Ном нав шуд", `Пайваст акнун «${name}» ном дорад.`);
      await refreshAfterMutation(app);
    } catch (error) {
      setFormError(form, errorMessage(error, "Ном сабт нашуд. Дубора кӯшиш кунед."));
      setButtonLoading(submit, false);
    }
  });
}

async function refreshAfterMutation(app) {
  await Promise.allSettled([
    Promise.resolve().then(() => app.loadShellData()),
    renderIntegrations(app),
  ]);
}

async function disconnectIntegration(app, integration, button) {
  const accepted = await confirmAction({
    title: "Қатъ кардани пайваст",
    message: `Пайвасти «${integrationName(integration)}» ғайрифаъол мешавад. Паёмҳои қаблан сабтшуда боқӣ мемонанд.`,
    confirmText: "Қатъ кардан",
    danger: true,
  });
  if (!accepted) return;

  setButtonLoading(button, true, "Қатъ шуда истодааст...");
  try {
    await api.post(`/api/integrations/${integration.platform}/disconnect/`, { integration_id: integration.id });
    toast("Пайваст қатъ шуд", `${integrationName(integration)} дигар паёмҳои навро қабул намекунад.`);
    await refreshAfterMutation(app);
  } catch (error) {
    toast("Қатъ кардан муяссар нашуд", errorMessage(error, "Дубора кӯшиш кунед."), "error");
    setButtonLoading(button, false);
  }
}

async function deleteIntegration(app, integration, button) {
  const accepted = await confirmAction({
    title: "Ҳазфи интегратсия",
    message: `«${integrationName(integration)}» пурра ҳазф мешавад. Ин амалро баргардонидан мумкин нест.`,
    confirmText: "Ҳазф кардан",
    danger: true,
  });
  if (!accepted) return;

  setButtonLoading(button, true, "Ҳазф шуда истодааст...");
  try {
    await api.delete(`/api/integrations/${integration.id}/`);
    toast("Интегратсия ҳазф шуд", `${integrationName(integration)} аз рӯйхат хориҷ гардид.`);
    await refreshAfterMutation(app);
  } catch (error) {
    toast("Ҳазф кардан муяссар нашуд", errorMessage(error, "Дубора кӯшиш кунед."), "error");
    setButtonLoading(button, false);
  }
}

async function testWhatsApp(integration, button) {
  setButtonLoading(button, true, "Санҷида истодааст...");
  try {
    const data = await api.post("/api/integrations/whatsapp/test/", { integration_id: integration.id });
    if (data?.ok) {
      toast("Санҷиш муваффақ буд", "Маълумоти пайвастшавии WhatsApp дастрас аст.");
    } else {
      toast("Санҷиш ноком шуд", "Access Token дастрас нест. Пайвасти нав созед.", "error");
    }
  } catch (error) {
    toast("WhatsApp санҷида нашуд", errorMessage(error, "Дубора кӯшиш кунед."), "error");
  } finally {
    setButtonLoading(button, false);
  }
}

function bindPage(app, integrations) {
  const page = app.main.querySelector("[data-integrations-page]");
  if (!page) return;

  page.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || !page.contains(button)) return;

    const pageAction = button.dataset.pageAction;
    if (pageAction === "demo-vk" || pageAction === "demo-instagram" || pageAction === "demo-facebook") {
      const platform = pageAction.replace("demo-", "");
      openDemoForm(app, platform);
      return;
    }
    if (pageAction === "connect-telegram") {
      openTelegramWizard(app);
      return;
    }
    if (pageAction === "connect-whatsapp") {
      openWhatsAppForm(app);
      return;
    }
    if (pageAction === "connect-instagram") {
      openDemoForm(app, "instagram");
      return;
    }
    if (pageAction === "connect-facebook") {
      openDemoForm(app, "facebook");
      return;
    }
    if (pageAction === "connect-viber") {
      openBotChannelForm(app, "viber");
      return;
    }
    if (pageAction === "connect-vk") {
      openVKOAuth(app);
      return;
    }

    const action = button.dataset.integrationAction;
    if (!action) return;
    const integration = integrations.find((item) => String(item.id) === button.dataset.integrationId);
    if (!integration) return;

    if (action === "continue") openTelegramWizard(app, integration);
    if (action === "rename") openRenameForm(app, integration);
    if (action === "copy-webhook") void copyWebhook(integration);
    if (action === "test") void testWhatsApp(integration, button);
    if (action === "disconnect") void disconnectIntegration(app, integration, button);
    if (action === "delete") void deleteIntegration(app, integration, button);
  });
}

function renderLoadError(app, error) {
  app.main.innerHTML = `<div class="page">
    <header class="page-header">
      <div><div class="eyebrow">Каналҳои муошират</div><h1>Интегратсияҳо</h1></div>
    </header>
    <section class="card">
      ${emptyState({
        iconName: "alert",
        title: "Интегратсияҳо бор нашуданд",
        text: errorMessage(error, "Пайваст ба сервер дастрас нест. Баъдтар дубора кӯшиш кунед."),
        action: `<button class="btn btn-primary" type="button" data-retry>${icon("refresh")} Аз нав кӯшиш кардан</button>`,
      })}
    </section>
  </div>`;
  app.main.querySelector("[data-retry]")?.addEventListener("click", () => renderIntegrations(app));
}

export async function renderIntegrations(app) {
  consumeInstagramCallback();
  consumeFacebookCallback();
  await consumeVKOAuth(app);
  app.main.innerHTML = pageSkeleton();
  try {
    const data = await api.get("/api/integrations/?page_size=100&ordering=-created_at");
    const integrations = results(data);
    app.main.innerHTML = pageMarkup(integrations);
    bindPage(app, integrations);
    app.activeRefresh = () => renderIntegrations(app);
  } catch (error) {
    renderLoadError(app, error);
  }
}
