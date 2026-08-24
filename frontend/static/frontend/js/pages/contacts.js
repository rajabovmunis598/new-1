import { api, results } from "../api.js?v=20260822-8";
import {
  avatar, debounce, emptyState, escapeHTML, formatDate, formatMoney, icon,
  platformBadge, queryString, statusBadge,
} from "../ui.js?v=20260822-8";

const state = { page: 1, search: "", selectedId: null, contacts: [], response: null };

function contactName(contact) {
  return contact.name || contact.username || contact.phone || `Муштарӣ #${contact.id}`;
}

function listMarkup() {
  if (!state.contacts.length) {
    return emptyState({
      iconName: "contacts",
      title: "Муштарӣ ёфт нашуд",
      text: state.search ? "Матни ҷустуҷӯро тағйир диҳед." : "Контактҳо баъди гирифтани паём аз Telegram, WhatsApp ё Instagram пайдо мешаванд.",
    });
  }
  return state.contacts.map((contact) => `<button class="contact-row ${Number(state.selectedId) === Number(contact.id) ? "active" : ""}" type="button" data-contact-id="${contact.id}">
    ${avatar(contact)}
    <span class="contact-copy"><strong class="truncate">${escapeHTML(contactName(contact))}</strong><span class="truncate">${escapeHTML(contact.phone || (contact.username ? `@${contact.username}` : "Маълумоти тамос нест"))}</span></span>
    ${platformBadge(contact.platform)}
  </button>`).join("");
}

function paginationMarkup() {
  const count = Number(state.response?.count || 0);
  const pages = Math.max(1, Math.ceil(count / 20));
  return `<span>${count.toLocaleString("tg-TJ")} муштарӣ</span><span class="cluster"><button class="btn btn-ghost btn-icon btn-sm" type="button" data-contact-page="prev" ${state.response?.previous ? "" : "disabled"}>${icon("chevronLeft")}</button><span>${state.page} / ${pages}</span><button class="btn btn-ghost btn-icon btn-sm" type="button" data-contact-page="next" ${state.response?.next ? "" : "disabled"}>${icon("chevronRight")}</button></span>`;
}

function detailPlaceholder() {
  return `<article class="card">${emptyState({ iconName: "user", title: "Муштариро интихоб кунед", text: "Барои дидани маълумоти тамос, суҳбатҳо ва фармоишҳо аз рӯйхат муштариро интихоб кунед." })}</article>`;
}

function conversationItem(conversation) {
  return `<button class="compact-row btn-ghost" type="button" data-open-conversation="${conversation.id}"><span class="compact-row-copy"><strong>${escapeHTML(conversation.title || "Суҳбат")}</strong><span>${platformBadge(conversation.platform)} · ${escapeHTML(formatDate(conversation.last_message_at || conversation.created_at))}</span></span>${statusBadge(conversation.status)}</button>`;
}

function orderItem(order) {
  return `<button class="compact-row btn-ghost" type="button" data-nav="/orders"><span class="compact-row-copy"><strong>#${order.id} · ${escapeHTML(order.description || "Фармоиш")}</strong><span>${escapeHTML(formatDate(order.created_at))}</span></span><span style="text-align:right"><strong>${escapeHTML(formatMoney(order.amount, order.currency))}</strong><span style="display:block;margin-top:4px">${statusBadge(order.status)}</span></span></button>`;
}

async function loadDetail(app, contact) {
  state.selectedId = Number(contact.id);
  const detail = app.main.querySelector("#contact-detail");
  detail.innerHTML = `<article class="card"><div class="empty-state"><span class="loading-spinner" style="color:var(--primary)"></span></div></article>`;
  app.main.querySelectorAll("[data-contact-id]").forEach((button) => button.classList.toggle("active", Number(button.dataset.contactId) === state.selectedId));
  const url = new URL(window.location.href);
  url.searchParams.set("contact", state.selectedId);
  history.replaceState({}, "", `${url.pathname}${url.search}`);

  try {
    const [conversationData, orderData] = await Promise.all([
      api.get(`/api/conversations/${queryString({ contact: contact.id, page_size: 6, ordering: "-last_message_at" })}`),
      api.get(`/api/orders/${queryString({ contact: contact.id, page_size: 6, ordering: "-created_at" })}`),
    ]);
    const conversations = results(conversationData);
    const orders = results(orderData);
    const name = contactName(contact);
    detail.innerHTML = `<article class="card">
      <div class="profile-cover"></div>
      <div class="contact-profile">
        ${avatar({ ...contact, name }, "lg")}
        <h2>${escapeHTML(name)}</h2>
        <p>${platformBadge(contact.platform)} · Аз ${escapeHTML(formatDate(contact.created_at))}</p>
        <div class="detail-grid">
          <div class="detail-item"><span>Рақами телефон</span><strong>${contact.phone ? `<a href="tel:${escapeHTML(contact.phone)}">${escapeHTML(contact.phone)}</a>` : "—"}</strong></div>
          <div class="detail-item"><span>Номи корбар</span><strong>${contact.username ? `@${escapeHTML(contact.username)}` : "—"}</strong></div>
          <div class="detail-item"><span>ID-и беруна</span><strong>${escapeHTML(contact.external_id || "—")}</strong></div>
          <div class="detail-item"><span>Охирин навсозӣ</span><strong>${escapeHTML(formatDate(contact.updated_at))}</strong></div>
        </div>
        <div class="page-actions" style="margin-top:18px">
          ${conversations[0] ? `<button class="btn btn-primary" type="button" data-open-conversation="${conversations[0].id}">${icon("messages")} Навиштани паём</button>` : ""}
          ${contact.phone ? `<a class="btn btn-secondary" href="tel:${escapeHTML(contact.phone)}">${icon("phone")} Занг</a>` : ""}
        </div>
      </div>
    </article>
    <section class="related-grid">
      <article class="card"><header class="card-head"><h3>Суҳбатҳо</h3><span class="muted">${conversationData.count || conversations.length}</span></header><div class="card-body">${conversations.length ? `<div class="compact-list">${conversations.map(conversationItem).join("")}</div>` : emptyState({ iconName: "messages", title: "Суҳбат нест", text: "Бо ин муштарӣ ҳоло суҳбат сабт нашудааст." })}</div></article>
      <article class="card"><header class="card-head"><h3>Фармоишҳо</h3><span class="muted">${orderData.count || orders.length}</span></header><div class="card-body">${orders.length ? `<div class="compact-list">${orders.map(orderItem).join("")}</div>` : emptyState({ iconName: "orders", title: "Фармоиш нест", text: "Барои ин муштарӣ ҳоло фармоиш сабт нашудааст." })}</div></article>
    </section>`;
    detail.querySelectorAll("[data-open-conversation]").forEach((button) => button.addEventListener("click", () => app.navigate(`/messages?conversation=${button.dataset.openConversation}`)));
  } catch (error) {
    detail.innerHTML = `<article class="card">${emptyState({ iconName: "alert", title: "Маълумот бор нашуд", text: error.message, action: `<button class="btn btn-primary btn-sm" type="button" data-retry-contact>Дубора кӯшиш</button>` })}</article>`;
    detail.querySelector("[data-retry-contact]")?.addEventListener("click", () => loadDetail(app, contact));
  }
}

function bindList(app) {
  app.main.querySelectorAll("[data-contact-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const contact = state.contacts.find((item) => Number(item.id) === Number(button.dataset.contactId));
      if (contact) loadDetail(app, contact);
    });
  });
  app.main.querySelectorAll("[data-contact-page]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.page = Math.max(1, state.page + (button.dataset.contactPage === "next" ? 1 : -1));
      await loadContacts(app);
    });
  });
}

async function loadContacts(app, preferredId = null) {
  const list = app.main.querySelector("#contact-list");
  list.innerHTML = `<div class="empty-state"><span class="loading-spinner" style="color:var(--primary)"></span></div>`;
  const data = await api.get(`/api/contacts/${queryString({ page: state.page, page_size: 20, search: state.search, ordering: "name" })}`);
  state.response = data;
  state.contacts = results(data);
  list.innerHTML = listMarkup();
  app.main.querySelector("#contact-pagination").innerHTML = paginationMarkup();
  bindList(app);

  const targetId = preferredId || state.selectedId;
  let target = state.contacts.find((item) => Number(item.id) === Number(targetId));
  if (!target && targetId) {
    try { target = await api.get(`/api/contacts/${targetId}/`); } catch (_) { target = null; }
  }
  if (!target && window.innerWidth > 1020) target = state.contacts[0];
  if (target) await loadDetail(app, target);
  else app.main.querySelector("#contact-detail").innerHTML = detailPlaceholder();
}

export async function renderContacts(app) {
  const requested = Number(new URLSearchParams(window.location.search).get("contact"));
  if (requested) state.selectedId = requested;
  app.main.innerHTML = `<div class="page">
    <header class="page-header"><div><div class="eyebrow">Муносибат бо муштариён</div><h1>Муштариён</h1><p>Контактҳои Telegram, WhatsApp ва Instagram, таърихи суҳбат ва фармоишҳо дар як ҷо.</p></div></header>
    <section class="split-layout">
      <article class="card contact-list">
        <header class="card-head"><label class="search-field" style="width:100%"><span class="sr-only">Ҷустуҷӯ</span>${icon("search")}<input class="field-input" id="contact-search" type="search" value="${escapeHTML(state.search)}" placeholder="Ном, username ё телефон..."></label></header>
        <div id="contact-list"></div>
        <footer class="table-footer" id="contact-pagination"></footer>
      </article>
      <div id="contact-detail">${detailPlaceholder()}</div>
    </section>
  </div>`;
  const search = app.main.querySelector("#contact-search");
  search.addEventListener("input", debounce(async () => { state.search = search.value.trim(); state.page = 1; await loadContacts(app); }));
  try { await loadContacts(app, requested); }
  catch (error) { app.renderError(error, () => renderContacts(app)); return; }
  app.activeRefresh = () => loadContacts(app, state.selectedId);
}
