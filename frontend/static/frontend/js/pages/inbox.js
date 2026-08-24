import { api, results } from "../api.js?v=20260823-6";
import {
  avatar, debounce, emptyState, escapeHTML, formatDate, formatTime, icon,
  platformBadge, queryString, safeUrl, setButtonLoading, statusBadge, toast,
} from "../ui.js?v=20260823-6";

const state = {
  page: 1,
  search: "",
  platform: "",
  status: "",
  selectedId: null,
  selectedConversation: null,
  conversations: [],
  response: null,
  drafts: new Map(),
  threadRequestVersion: 0,
};

function contactName(conversation) {
  const contact = conversation?.contact_detail || {};
  return contact.name || conversation?.title || contact.username || contact.phone || "Муштарӣ";
}

function draftKey(conversationId) {
  return String(conversationId || "");
}

function conversationDraft(conversationId) {
  return state.drafts.get(draftKey(conversationId)) || "";
}

function saveConversationDraft(conversationId, value) {
  const key = draftKey(conversationId);
  if (!key) return;
  if (value) state.drafts.set(key, value);
  else state.drafts.delete(key);
}

function selectedComposer(app, conversationId = state.selectedId) {
  const form = app.main.querySelector("#message-form");
  if (!form || Number(form.dataset.conversationId) !== Number(conversationId)) return null;
  return form.querySelector("#message-text");
}

function shouldPreserveSelectedThread(app) {
  const textarea = selectedComposer(app);
  if (!textarea) return false;
  saveConversationDraft(state.selectedId, textarea.value);
  return document.activeElement === textarea || Boolean(textarea.value || conversationDraft(state.selectedId));
}

function conversationRows() {
  if (!state.conversations.length) {
    return emptyState({
      iconName: "messages",
      title: "Суҳбат ёфт нашуд",
      text: state.search || state.platform || state.status
        ? "Филтрҳоро тағйир диҳед ва дубора ҷустуҷӯ кунед."
        : "Баъди омадани паём суҳбатҳо дар ин ҷо пайдо мешаванд.",
    });
  }
  return state.conversations.map((conversation) => {
    const contact = conversation.contact_detail || {};
    const name = contactName(conversation);
    const selected = Number(state.selectedId) === Number(conversation.id);
    return `<button class="conversation-row ${selected ? "active" : ""}" type="button" data-conversation-id="${conversation.id}">
      ${avatar({ ...contact, name })}
      <span class="conversation-copy"><span class="conversation-name"><span class="truncate">${escapeHTML(name)}</span>${platformBadge(conversation.platform)}</span><p>${escapeHTML(conversation.title || contact.phone || contact.username || "Суҳбати муштарӣ")}</p></span>
      <span class="conversation-meta"><time>${escapeHTML(formatTime(conversation.last_message_at || conversation.updated_at))}</time>${conversation.unread_count ? `<span class="unread-count">${conversation.unread_count}</span>` : statusBadge(conversation.status)}</span>
    </button>`;
  }).join("");
}

function paginationMarkup() {
  const count = Number(state.response?.count || 0);
  const pages = Math.max(1, Math.ceil(count / 20));
  return `<span>${count.toLocaleString("tg-TJ")} суҳбат</span><span class="cluster"><button class="btn btn-ghost btn-icon btn-sm" type="button" data-page="prev" ${state.response?.previous ? "" : "disabled"} aria-label="Қаблӣ">${icon("chevronLeft")}</button><span>${state.page} / ${pages}</span><button class="btn btn-ghost btn-icon btn-sm" type="button" data-page="next" ${state.response?.next ? "" : "disabled"} aria-label="Баъдӣ">${icon("chevronRight")}</button></span>`;
}

function mediaMarkup(message) {
  const url = safeUrl(message.media_url || "");
  if (url === "#") return "";
  if (message.message_type === "image" || message.message_type === "sticker") {
    return `<div class="message-media"><img src="${escapeHTML(url)}" alt="Тасвири фиристодашуда" loading="lazy"></div>`;
  }
  if (message.message_type === "video") return `<div class="message-media"><video src="${escapeHTML(url)}" controls preload="metadata"></video></div>`;
  if (message.message_type === "audio") return `<div class="message-media"><audio src="${escapeHTML(url)}" controls preload="metadata"></audio></div>`;
  return `<div class="message-media"><a class="btn btn-secondary btn-sm" href="${escapeHTML(url)}" target="_blank" rel="noopener">${icon("download")} Кушодани файл</a></div>`;
}

function messageMarkup(message) {
  const sender = ["business", "system"].includes(message.sender_type) ? message.sender_type : "customer";
  const delivery = message.metadata?.delivery_status;
  const aiButton = sender === "customer" && message.text
    ? `<button class="ai-reply-trigger" type="button" data-ai-reply="${message.id}" data-msg-text="${escapeHTML(message.text)}">${icon("sparkles")} AI</button>`
    : "";
  return `<article class="message ${sender}" data-message-id="${message.id}"><div class="message-bubble">
    ${mediaMarkup(message)}
    ${message.text ? `<p>${escapeHTML(message.text)}</p>` : (!message.media_url ? "<p>Паёми бе матн</p>" : "")}
    <div class="message-meta"><time>${escapeHTML(formatTime(message.external_created_at || message.created_at))}</time>${delivery ? `<span>· ${escapeHTML(delivery)}</span>` : ""}${sender !== "system" ? `<button class="btn btn-ghost btn-icon btn-sm" type="button" data-external-message="${message.id}" aria-label="Кушодан дар платформа">${icon("external")}</button>` : ""}</div>
  </div>${aiButton}</article>`;
}

function appendMessageToOpenThread(app, conversationId, message) {
  if (!message || Number(state.selectedId) !== Number(conversationId)) return false;
  const form = app.main.querySelector("#message-form");
  if (!form || Number(form.dataset.conversationId) !== Number(conversationId)) return false;
  const scroll = app.main.querySelector("#messages-scroll");
  if (!scroll) return false;
  if (message.id && scroll.querySelector(`[data-message-id="${message.id}"]`)) return true;

  if (!scroll.querySelector(".message")) {
    scroll.innerHTML = `<div class="message-day">${escapeHTML(formatDate(message.created_at || new Date().toISOString()))}</div>`;
  }
  scroll.insertAdjacentHTML("beforeend", messageMarkup(message));
  scroll.scrollTop = scroll.scrollHeight;
  return true;
}

async function markConversationRead(app, conversation, requestIsCurrent) {
  if (document.visibilityState !== "visible") return;
  try {
    await api.post(`/api/conversations/${conversation.id}/read/`);
    if (!requestIsCurrent()) return;
    conversation.unread_count = 0;
    const row = app.main.querySelector(`[data-conversation-id="${conversation.id}"] .unread-count`);
    if (row) row.remove();
    await app.loadShellData();
  } catch (_) { /* Reading and replying remain available if the marker fails. */ }
}

function emptyThread() {
  return `<div class="thread-empty"><div class="thread-empty-inner"><div class="thread-empty-icon">${icon("messages", "icon")}</div><h2>Суҳбатро интихоб кунед</h2><p>Аз рӯйхати чап муштариро интихоб кунед, то таърихи паёмҳоро бинед ва ҷавоб диҳед.</p></div></div>`;
}

function shellMarkup() {
  return `<div class="page inbox-page">
    <section class="inbox-layout" id="inbox-layout">
      <aside class="conversation-panel">
        <header class="panel-title"><div><div class="eyebrow">Маркази муошират</div><h1>Паёмҳо</h1></div><button class="btn btn-soft btn-icon" type="button" data-refresh-conversations aria-label="Навсозӣ">${icon("refresh")}</button></header>
        <div class="inbox-filters">
          <label class="search-field"><span class="sr-only">Ҷустуҷӯ</span>${icon("search")}<input class="field-input" id="conversation-search" type="search" value="${escapeHTML(state.search)}" placeholder="Ном, рақам ё паём..."></label>
          <div class="inbox-filter-row">
            <select class="field-select" id="platform-filter" aria-label="Платформа"><option value="">Ҳамаи каналҳо</option><option value="telegram" ${state.platform === "telegram" ? "selected" : ""}>Telegram</option><option value="whatsapp" ${state.platform === "whatsapp" ? "selected" : ""}>WhatsApp</option><option value="instagram" ${state.platform === "instagram" ? "selected" : ""}>Instagram</option></select>
            <select class="field-select" id="status-filter" aria-label="Ҳолати суҳбат"><option value="">Ҳамаи ҳолатҳо</option><option value="open" ${state.status === "open" ? "selected" : ""}>Кушода</option><option value="closed" ${state.status === "closed" ? "selected" : ""}>Пӯшида</option><option value="archived" ${state.status === "archived" ? "selected" : ""}>Бойгонӣ</option></select>
          </div>
        </div>
        <div class="conversation-list" id="conversation-list"><div class="empty-state"><span class="loading-spinner" style="color:var(--primary)"></span></div></div>
        <footer class="panel-pagination" id="conversation-pagination"></footer>
      </aside>
      <section class="thread-panel" id="thread-panel">${emptyThread()}</section>
    </section>
  </div>`;
}

async function loadConversationList(app, { selectFirst = false, silent = false } = {}) {
  const data = await api.get(`/api/conversations/${queryString({
    page: state.page,
    page_size: 20,
    search: state.search,
    platform: state.platform,
    status: state.status,
    ordering: "-last_message_at",
  })}`);
  const newConversations = results(data);
  const prevIds = state.conversations.map((c) => c.id).join(",");
  const newIds = newConversations.map((c) => c.id).join(",");
  const prevCounts = state.conversations.map((c) => `${c.id}:${c.unread_count}:${c.last_message_at}`).join(",");
  const newCounts = newConversations.map((c) => `${c.id}:${c.unread_count}:${c.last_message_at}`).join(",");
  state.response = data;
  state.conversations = newConversations;
  if (!silent || prevIds !== newIds || prevCounts !== newCounts) {
    const list = app.main.querySelector("#conversation-list");
    const scrollEl = list?.parentElement;
    const scrollTop = scrollEl?.scrollTop;
    if (list) list.innerHTML = conversationRows();
    if (scrollEl && scrollTop != null) scrollEl.scrollTop = scrollTop;
    app.main.querySelector("#conversation-pagination").innerHTML = paginationMarkup();
    bindListEvents(app);
  }

  if (state.selectedId) {
    const refreshed = state.conversations.find((item) => Number(item.id) === Number(state.selectedId));
    if (refreshed) state.selectedConversation = refreshed;
    if (!shouldPreserveSelectedThread(app)) await selectConversation(app, state.selectedId, false);
  } else if (selectFirst && state.conversations[0] && window.innerWidth > 820) {
    await selectConversation(app, state.conversations[0].id, false);
  }
}

function bindListEvents(app) {
  app.main.querySelectorAll("[data-conversation-id]").forEach((button) => {
    button.addEventListener("click", () => selectConversation(app, Number(button.dataset.conversationId), true));
  });
  app.main.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.page += button.dataset.page === "next" ? 1 : -1;
      state.page = Math.max(1, state.page);
      await loadConversationList(app);
    });
  });
}

async function selectConversation(app, id, openMobile) {
  state.selectedId = Number(id);
  state.selectedConversation = state.conversations.find((item) => Number(item.id) === state.selectedId) || null;
  if (!state.selectedConversation) state.selectedConversation = await api.get(`/api/conversations/${state.selectedId}/`);
  const url = new URL(window.location.href);
  url.searchParams.set("conversation", state.selectedId);
  history.replaceState({}, "", `${url.pathname}${url.search}`);
  app.main.querySelectorAll("[data-conversation-id]").forEach((button) => button.classList.toggle("active", Number(button.dataset.conversationId) === state.selectedId));
  if (openMobile) app.main.querySelector("#inbox-layout")?.classList.add("thread-open");
  await loadThread(app);
}

async function loadThread(app) {
  const panel = app.main.querySelector("#thread-panel");
  if (!panel || !state.selectedConversation) return;
  const conversation = state.selectedConversation;
  const conversationId = Number(conversation.id);
  const requestVersion = ++state.threadRequestVersion;
  const requestIsCurrent = () => (
    requestVersion === state.threadRequestVersion
    && Number(state.selectedId) === conversationId
    && panel.isConnected
  );
  const previousForm = panel.querySelector("#message-form");
  const previousTextarea = previousForm?.querySelector("#message-text");
  const previousConversationId = Number(previousForm?.dataset.conversationId);
  const restoreComposerFocus = Boolean(
    previousTextarea
    && previousConversationId === Number(conversation.id)
    && document.activeElement === previousTextarea
  );
  const selectionStart = previousTextarea?.selectionStart;
  const selectionEnd = previousTextarea?.selectionEnd;
  if (previousTextarea && previousConversationId) {
    saveConversationDraft(previousConversationId, previousTextarea.value);
  }

  panel.innerHTML = `<div class="thread-empty"><span class="loading-spinner" style="color:var(--primary)"></span></div>`;
  const data = await api.get(`/api/messages/${queryString({ conversation: conversation.id, ordering: "-created_at", page_size: 100 })}`);
  if (!requestIsCurrent()) return;
  const messages = results(data).reverse();
  if (!requestIsCurrent()) return;

  const contact = conversation.contact_detail || {};
  const name = contactName(conversation);
  const open = conversation.status === "open";
  panel.innerHTML = `<header class="thread-head">
    <button class="btn btn-ghost btn-icon thread-back" type="button" data-thread-back aria-label="Бозгашт">${icon("chevronLeft")}</button>
    ${avatar({ ...contact, name })}
    <div class="thread-head-copy"><strong class="truncate">${escapeHTML(name)}</strong><span>${platformBadge(conversation.platform)} · ${statusBadge(conversation.status)}</span></div>
    <div class="thread-actions">
      ${!open ? `<button class="btn btn-soft btn-sm" type="button" data-conversation-action="open">${icon("refresh")} Боз кардан</button>` : `<button class="btn btn-ghost btn-icon" type="button" data-conversation-action="close" aria-label="Пӯшидани суҳбат">${icon("checkCircle")}</button><button class="btn btn-ghost btn-icon" type="button" data-conversation-action="archive" aria-label="Бойгонӣ">${icon("archive")}</button>`}
      <button class="btn btn-ghost btn-icon" type="button" data-contact-profile aria-label="Муштарӣ">${icon("user")}</button>
    </div>
  </header>
  <div class="messages-scroll" id="messages-scroll">
    ${messages.length ? `<div class="message-day">${escapeHTML(formatDate(messages[0].created_at))}</div>${messages.map(messageMarkup).join("")}` : emptyState({ iconName: "messages", title: "Ҳоло паём нест", text: "Паёми аввалро нависед ва суҳбатро оғоз кунед." })}
  </div>
  <form class="composer" id="message-form" data-conversation-id="${escapeHTML(conversation.id)}">
    <label class="sr-only" for="message-text">Матни паём</label>
    <textarea class="field-textarea" id="message-text" name="text" rows="1" maxlength="4096" placeholder="Паём нависед..." ${open ? "" : "disabled"}></textarea>
    <button class="btn btn-primary btn-icon" type="submit" ${open ? "" : "disabled"} aria-label="Фиристодан">${icon("send")}</button>
  </form>`;
  const textarea = panel.querySelector("#message-text");
  if (textarea) textarea.value = conversationDraft(conversation.id);
  bindThreadEvents(app);
  const scroll = panel.querySelector("#messages-scroll");
  if (scroll) scroll.scrollTop = scroll.scrollHeight;
  if (restoreComposerFocus && textarea && !textarea.disabled && panel.isConnected) {
    try { textarea.focus({ preventScroll: true }); } catch (_) { textarea.focus(); }
    if (typeof textarea.setSelectionRange === "function") {
      const end = textarea.value.length;
      const start = Math.min(Number.isInteger(selectionStart) ? selectionStart : end, end);
      const finish = Math.min(Number.isInteger(selectionEnd) ? selectionEnd : start, end);
      try { textarea.setSelectionRange(start, finish); } catch (_) { /* Some input modes do not expose a caret. */ }
    }
  }
  // This request is ancillary. A slow or failed read marker must never block
  // rendering the composer or sending a reply.
  void markConversationRead(app, conversation, requestIsCurrent);
}

async function handleAiReply(panel, btn) {
  const existing = panel.querySelector(".ai-suggestions");
  if (existing) { existing.remove(); return; }
  const msgText = btn.dataset.msgText || "";
  if (!msgText) return;
  btn.insertAdjacentHTML("afterend", `<div class="ai-suggestions"><div class="ai-loading"><span class="loading-spinner" style="color:var(--primary)"></span>AI javob тайёр мекунад...</div></div>`);
  const suggestionsEl = panel.querySelector(".ai-suggestions");
  try {
    const resp = await api.post("/api/ai/suggestions/", { text: msgText });
    const suggestions = Array.isArray(resp.suggestions) ? resp.suggestions : [];
    if (!suggestions.length) throw new Error("Ҷавоб ёфт нашуд");
    suggestionsEl.innerHTML = suggestions.map((s) => `<button class="ai-suggestion-btn" type="button">${escapeHTML(s)}</button>`).join("") + `<button class="ai-suggestion-btn other" type="button">Дигар... Худам менависам</button>`;
    suggestionsEl.querySelectorAll(".ai-suggestion-btn:not(.other)").forEach((sBtn) => {
      sBtn.addEventListener("click", () => {
        const textarea = panel.querySelector("#message-text");
        if (textarea) { textarea.value = sBtn.textContent; textarea.focus(); }
        suggestionsEl.remove();
      });
    });
    suggestionsEl.querySelector(".ai-suggestion-btn.other")?.addEventListener("click", () => {
      suggestionsEl.remove();
      const textarea = panel.querySelector("#message-text");
      if (textarea) textarea.focus();
    });
  } catch (err) {
    suggestionsEl.innerHTML = `<div class="ai-suggestion-btn other" style="cursor:default;color:var(--danger)">Хато: ${escapeHTML(err.message || err)}</div>`;
  }
}

function bindThreadEvents(app) {
  const panel = app.main.querySelector("#thread-panel");
  panel.querySelector("[data-thread-back]")?.addEventListener("click", () => app.main.querySelector("#inbox-layout")?.classList.remove("thread-open"));
  panel.querySelector("[data-contact-profile]")?.addEventListener("click", () => {
    const contactId = state.selectedConversation?.contact;
    app.navigate(contactId ? `/contacts?contact=${contactId}` : "/contacts");
  });
  panel.querySelectorAll("[data-conversation-action]").forEach((button) => {
    button.addEventListener("click", () => updateConversationStatus(app, button.dataset.conversationAction, button));
  });
  panel.addEventListener("click", (event) => {
    const externalBtn = event.target.closest("[data-external-message]");
    if (externalBtn) {
      event.preventDefault();
      (async () => {
        try {
          const data = await api.get(`/api/messages/${externalBtn.dataset.externalMessage}/external-url/`);
          if (!data.url) return toast("Истинод дастрас нест", "Ин платформа барои паём пайванди мустақим надорад.", "error");
          window.open(safeUrl(data.url), "_blank", "noopener,noreferrer");
        } catch (error) { toast("Пайванд кушода нашуд", error.message, "error"); }
      })();
      return;
    }
    const aiBtn = event.target.closest("[data-ai-reply]");
    if (aiBtn) {
      event.preventDefault();
      handleAiReply(panel, aiBtn);
      return;
    }
    const suggestion = event.target.closest(".ai-suggestion-btn:not(.other)");
    if (suggestion) {
      event.preventDefault();
      const textarea = panel.querySelector("#message-text");
      if (textarea) { textarea.value = suggestion.textContent; textarea.focus(); }
      const suggestions = panel.querySelector(".ai-suggestions");
      if (suggestions) suggestions.remove();
      return;
    }
    const otherBtn = event.target.closest(".ai-suggestion-btn.other");
    if (otherBtn) {
      event.preventDefault();
      const suggestions = panel.querySelector(".ai-suggestions");
      if (suggestions) suggestions.remove();
      const textarea = panel.querySelector("#message-text");
      if (textarea) textarea.focus();
      return;
    }
  });
  const form = panel.querySelector("#message-form");
  form?.addEventListener("submit", (event) => sendMessage(app, event));
  const textarea = panel.querySelector("#message-text");
  const conversationId = Number(form?.dataset.conversationId);
  textarea?.addEventListener("input", () => saveConversationDraft(conversationId, textarea.value));
  textarea?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    if (form?.dataset.sending === "true") return;
    if (typeof form?.requestSubmit === "function") form.requestSubmit();
    else form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
}

async function sendMessage(app, event) {
  event.preventDefault();
  const form = event.currentTarget;
  const textarea = form.querySelector("textarea");
  const conversationId = Number(form.dataset.conversationId || state.selectedId);
  if (!textarea || !Number.isInteger(conversationId) || conversationId <= 0 || form.dataset.sending === "true") return;
  const submittedDraft = textarea.value;
  const text = submittedDraft.trim();
  if (!text) return;
  const button = form.querySelector("button[type=submit]");
  form.dataset.sending = "true";
  form.setAttribute("aria-busy", "true");
  setButtonLoading(button, true, "");
  let message;
  try {
    message = await api.post(`/api/conversations/${conversationId}/messages/`, { text });
  } catch (error) {
    toast("Паём фиристода нашуд", error.message, "error");
    setButtonLoading(button, false);
    delete form.dataset.sending;
    form.removeAttribute("aria-busy");
    return;
  }

  if (textarea.value === submittedDraft) {
    textarea.value = "";
    saveConversationDraft(conversationId, "");
  } else {
    saveConversationDraft(conversationId, textarea.value);
  }
  appendMessageToOpenThread(app, conversationId, message);
  setButtonLoading(button, false);
  delete form.dataset.sending;
  form.removeAttribute("aria-busy");
  if (message?.metadata?.delivery_status === "queued") {
    toast("Паём ба навбат гузошта шуд", "Баъди расонидан ҳолати он нав мешавад.");
  } else {
    toast("Паём фиристода шуд");
  }
}

async function updateConversationStatus(app, action, button) {
  setButtonLoading(button, true, "");
  try {
    let conversation;
    if (action === "open") conversation = await api.patch(`/api/conversations/${state.selectedId}/`, { status: "open" });
    else conversation = await api.post(`/api/conversations/${state.selectedId}/${action}/`);
    state.selectedConversation = conversation;
    const index = state.conversations.findIndex((item) => item.id === conversation.id);
    if (index >= 0) state.conversations[index] = conversation;
    await loadThread(app);
    app.main.querySelector("#conversation-list").innerHTML = conversationRows();
    bindListEvents(app);
    toast(action === "archive" ? "Суҳбат ба бойгонӣ гузашт" : action === "close" ? "Суҳбат пӯшида шуд" : "Суҳбат боз шуд");
  } catch (error) { toast("Ҳолат тағйир наёфт", error.message, "error"); setButtonLoading(button, false); }
}

export async function renderInbox(app) {
  const routeVersion = app.routeVersion;
  let refreshPromise = null;
  let refreshAgain = false;
  let pollTimer = null;
  let stopped = false;
  const routeIsActive = () => {
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    return !stopped && app.routeVersion === routeVersion && path === "/messages";
  };
  const refreshInbox = async (silent = false) => {
    if (!routeIsActive()) return;
    if (refreshPromise) {
      refreshAgain = true;
      return refreshPromise;
    }
    refreshPromise = (async () => {
      do {
        refreshAgain = false;
        if (!routeIsActive()) return;
        await Promise.all([loadConversationList(app, { silent }), app.loadShellData()]);
      } while (refreshAgain && routeIsActive());
    })();
    try {
      await refreshPromise;
    } finally {
      refreshPromise = null;
    }
  };
  const schedulePoll = () => {
    if (!routeIsActive()) return;
    pollTimer = window.setTimeout(async () => {
      try { await refreshInbox(true); } catch (_) { /* The next poll retries transient errors. */ }
      schedulePoll();
    }, 5000);
  };
  const cleanup = () => {
    stopped = true;
    refreshAgain = false;
    if (pollTimer) window.clearTimeout(pollTimer);
    pollTimer = null;
    if (app.activeRefresh === refreshInbox) app.activeRefresh = null;
  };
  const requested = Number(new URLSearchParams(window.location.search).get("conversation"));
  if (requested) state.selectedId = requested;
  app.main.innerHTML = shellMarkup();

  const search = app.main.querySelector("#conversation-search");
  search.addEventListener("input", debounce(async () => {
    state.search = search.value.trim();
    state.page = 1;
    try { await refreshInbox(); } catch (error) { app.renderError(error, () => renderInbox(app)); }
  }));
  app.main.querySelector("#platform-filter").addEventListener("change", async (event) => { state.platform = event.target.value; state.page = 1; await refreshInbox(); });
  app.main.querySelector("#status-filter").addEventListener("change", async (event) => { state.status = event.target.value; state.page = 1; await refreshInbox(); });
  app.main.querySelector("[data-refresh-conversations]").addEventListener("click", () => refreshInbox());

  try {
    await loadConversationList(app, { selectFirst: !requested });
    if (requested && window.innerWidth <= 820) app.main.querySelector("#inbox-layout")?.classList.add("thread-open");
  } catch (error) {
    app.renderError(error, () => renderInbox(app));
    return;
  }
  if (app.setRouteCleanup(cleanup, routeVersion)) {
    app.activeRefresh = refreshInbox;
    schedulePoll();
  }
}
