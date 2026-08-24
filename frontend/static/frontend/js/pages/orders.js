import { api, results } from "../api.js?v=20260822-8";
import {
  avatar,
  closeModal,
  confirmAction,
  debounce,
  emptyState,
  escapeHTML,
  formatDate,
  formatMoney,
  icon,
  openModal,
  platformBadge,
  platformLabel,
  queryString,
  setButtonLoading,
  statusBadge,
  toast,
} from "../ui.js?v=20260822-8";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = [
  ["new", "Нав"],
  ["processing", "Дар кор"],
  ["completed", "Анҷом ёфт"],
  ["cancelled", "Бекор шуд"],
];

function entityId(value) {
  return value && typeof value === "object" ? value.id : value;
}

function statusOptions(selected = "new", includeAll = false) {
  const options = includeAll ? [["", "Ҳамаи вазъҳо"], ...STATUS_OPTIONS] : STATUS_OPTIONS;
  return options.map(([value, label]) => (
    `<option value="${escapeHTML(value)}" ${value === selected ? "selected" : ""}>${escapeHTML(label)}</option>`
  )).join("");
}

function displayError(error, fallback = "Амалиёт иҷро нашуд. Дубора кӯшиш кунед.") {
  const message = typeof error?.message === "string" ? error.message.trim() : "";
  return message || fallback;
}

function shortText(value, length = 64) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= length) return text;
  return `${text.slice(0, Math.max(0, length - 1)).trimEnd()}…`;
}

function localApiPath(value) {
  if (!value) return null;
  try {
    const url = new URL(value, window.location.origin);
    return `${url.pathname}${url.search}`;
  } catch (_) {
    return null;
  }
}

async function fetchAllPages(path) {
  const items = [];
  let next = path;
  let pagesRead = 0;

  while (next && pagesRead < 100) {
    const data = await api.get(next);
    items.push(...results(data));
    if (Array.isArray(data)) break;
    next = localApiPath(data?.next);
    pagesRead += 1;
  }
  return items;
}

function refreshShell(app) {
  if (typeof app.loadShellData !== "function") return;
  Promise.resolve(app.loadShellData()).catch(() => {});
}

export async function renderOrders(app) {
  const main = app.main;
  const pageToken = `orders-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const state = {
    page: 1,
    search: "",
    status: "",
    data: null,
    loading: true,
    error: "",
    requestNumber: 0,
    contacts: [],
    conversations: [],
    referencesLoading: true,
    referenceErrors: [],
    referencePromise: null,
  };

  main.innerHTML = `<section class="page" data-orders-page="${pageToken}">
    <header class="page-header">
      <div>
        <div class="eyebrow">Фурӯш ва хизматрасонӣ</div>
        <h1>Фармоишҳо</h1>
        <p>Фармоишҳои муштариёнро аз Telegram, WhatsApp ва Instagram пайгирӣ ва идора кунед.</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" type="button" data-action="create" disabled>
          ${icon("plus")} Фармоиши нав
        </button>
      </div>
    </header>

    <div class="filter-bar" aria-label="Филтрҳои фармоишҳо">
      <label class="search-field">
        <span class="sr-only">Ҷустуҷӯи фармоиш</span>
        ${icon("search")}
        <input class="field-input" type="search" data-orders-search
          placeholder="ID, тавсиф, ном ё телефон..." autocomplete="off">
      </label>
      <label>
        <span class="sr-only">Вазъи фармоиш</span>
        <select class="field-select" data-orders-status>${statusOptions("", true)}</select>
      </label>
      <button class="btn btn-ghost btn-sm" type="button" data-action="clear-filters">
        ${icon("refresh")} Пок кардан
      </button>
    </div>

    <div data-orders-results aria-live="polite" aria-busy="true"></div>
  </section>`;

  const root = main.querySelector(`[data-orders-page="${pageToken}"]`);
  const searchInput = root.querySelector("[data-orders-search]");
  const statusSelect = root.querySelector("[data-orders-status]");

  const isMounted = () => root.isConnected && main.contains(root);
  const currentRows = () => results(state.data);
  const findOrder = (id) => currentRows().find((order) => String(order.id) === String(id));
  const contactFor = (id) => {
    const target = entityId(id);
    return state.contacts.find((contact) => String(contact.id) === String(target)) || null;
  };
  const conversationFor = (id) => {
    const target = entityId(id);
    return state.conversations.find((conversation) => String(conversation.id) === String(target)) || null;
  };

  function contactName(contact, fallbackId = "") {
    if (!contact) return fallbackId ? `Муштарӣ #${fallbackId}` : "Муштарии номаълум";
    return contact.name || (contact.username ? `@${contact.username}` : "") || contact.phone || `Муштарӣ #${contact.id}`;
  }

  function contactSubtitle(contact) {
    if (!contact) return "Маълумоти тамос дастрас нест";
    return contact.phone || (contact.username ? `@${contact.username}` : "") || contact.external_id || "Маълумоти иловагӣ нест";
  }

  function orderTitle(order) {
    return order.external_id ? order.external_id : `#${order.id}`;
  }

  function moneyMarkup(value, currency) {
    return escapeHTML(formatMoney(value, currency || "TJS"));
  }

  function tableRow(order) {
    const contactId = entityId(order.contact);
    const contact = contactFor(contactId);
    const description = shortText(order.description || "Бе тавсиф");
    return `<tr>
      <td>
        <div class="table-primary">${escapeHTML(orderTitle(order))}</div>
        <div class="table-secondary">${escapeHTML(description)}</div>
      </td>
      <td>
        <div class="table-primary">${escapeHTML(contactName(contact, contactId))}</div>
        <div class="table-secondary">${escapeHTML(contactSubtitle(contact))}</div>
      </td>
      <td>${statusBadge(order.status)}</td>
      <td>
        <div class="table-primary">${escapeHTML(formatDate(order.created_at))}</div>
        <div class="table-secondary">Навсозӣ: ${escapeHTML(formatDate(order.updated_at))}</div>
      </td>
      <td><span class="order-total">${moneyMarkup(order.amount, order.currency)}</span></td>
      <td>
        <div class="table-actions">
          <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="view" data-id="${escapeHTML(order.id)}" aria-label="Дидани фармоиш ${escapeHTML(orderTitle(order))}">${icon("eye")}</button>
          <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="edit" data-id="${escapeHTML(order.id)}" aria-label="Таҳрири фармоиш ${escapeHTML(orderTitle(order))}">${icon("edit")}</button>
          <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="delete" data-id="${escapeHTML(order.id)}" aria-label="Нест кардани фармоиш ${escapeHTML(orderTitle(order))}">${icon("trash")}</button>
        </div>
      </td>
    </tr>`;
  }

  function mobileCard(order) {
    const contactId = entityId(order.contact);
    const contact = contactFor(contactId);
    return `<article class="mobile-data-card">
      <div class="mobile-data-head">
        <div>
          <div class="table-primary">${escapeHTML(orderTitle(order))}</div>
          <div class="table-secondary">${escapeHTML(shortText(order.description || "Бе тавсиф", 78))}</div>
        </div>
        ${statusBadge(order.status)}
      </div>
      <div class="mobile-data-meta">
        <span><strong class="table-primary">Муштарӣ</strong><br>${escapeHTML(contactName(contact, contactId))}</span>
        <span><strong class="table-primary">Маблағ</strong><br>${moneyMarkup(order.amount, order.currency)}</span>
        <span><strong class="table-primary">Сана</strong><br>${escapeHTML(formatDate(order.created_at))}</span>
        <span><strong class="table-primary">Асъор</strong><br>${escapeHTML(order.currency || "TJS")}</span>
      </div>
      <div class="mobile-data-actions">
        <button class="btn btn-secondary btn-sm" type="button" data-action="view" data-id="${escapeHTML(order.id)}">${icon("eye")} Дидан</button>
        <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="edit" data-id="${escapeHTML(order.id)}" aria-label="Таҳрир">${icon("edit")}</button>
        <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="delete" data-id="${escapeHTML(order.id)}" aria-label="Нест кардан">${icon("trash")}</button>
      </div>
    </article>`;
  }

  function paginationMarkup() {
    const count = Number(state.data?.count ?? currentRows().length);
    const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
    const start = count ? ((state.page - 1) * PAGE_SIZE) + 1 : 0;
    const end = Math.min(state.page * PAGE_SIZE, count);

    return `<footer class="table-footer">
      <span>${start.toLocaleString("tg-TJ")}–${end.toLocaleString("tg-TJ")} аз ${count.toLocaleString("tg-TJ")}</span>
      <nav class="cluster" aria-label="Саҳифабандии фармоишҳо">
        <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="page" data-page="${state.page - 1}" ${state.data?.previous ? "" : "disabled"} aria-label="Саҳифаи пешина">${icon("chevronLeft")}</button>
        <span>Саҳифаи ${state.page.toLocaleString("tg-TJ")} / ${totalPages.toLocaleString("tg-TJ")}</span>
        <button class="btn btn-ghost btn-icon btn-sm" type="button" data-action="page" data-page="${state.page + 1}" ${state.data?.next ? "" : "disabled"} aria-label="Саҳифаи навбатӣ">${icon("chevronRight")}</button>
      </nav>
    </footer>`;
  }

  function renderResults() {
    if (!isMounted()) return;
    const container = root.querySelector("[data-orders-results]");
    if (!container) return;
    container.setAttribute("aria-busy", state.loading ? "true" : "false");

    if (state.loading) {
      container.innerHTML = `<section class="card" style="margin-top:18px">
        <div class="empty-state">
          <div><span class="loading-spinner" style="color:var(--primary)" aria-hidden="true"></span><h3>Фармоишҳо бор мешаванд</h3><p>Лутфан, каме интизор шавед.</p></div>
        </div>
      </section>`;
      return;
    }

    if (state.error) {
      container.innerHTML = `<section class="card" style="margin-top:18px">${emptyState({
        iconName: "alert",
        title: "Фармоишҳо бор нашуданд",
        text: state.error,
        action: `<button class="btn btn-primary btn-sm" type="button" data-action="retry">${icon("refresh")} Дубора кӯшиш</button>`,
      })}</section>`;
      return;
    }

    const orders = currentRows();
    if (!orders.length) {
      const filtered = Boolean(state.search || state.status);
      container.innerHTML = `<section class="card" style="margin-top:18px">${emptyState({
        iconName: filtered ? "search" : "orders",
        title: filtered ? "Ягон фармоиш ёфт нашуд" : "Ҳоло фармоиш нест",
        text: filtered ? "Ҷустуҷӯ ё филтрро тағйир диҳед." : "Фармоиши аввалро барои яке аз муштариён сабт кунед.",
        action: filtered
          ? `<button class="btn btn-secondary btn-sm" type="button" data-action="clear-filters">${icon("refresh")} Пок кардани филтрҳо</button>`
          : `<button class="btn btn-primary btn-sm" type="button" data-action="create">${icon("plus")} Фармоиши нав</button>`,
      })}</section>`;
      return;
    }

    container.innerHTML = `<section class="card table-card" style="margin-top:18px">
      <header class="card-head">
        <h2>Рӯйхати фармоишҳо</h2>
        <span class="muted">${Number(state.data?.count ?? orders.length).toLocaleString("tg-TJ")} адад</span>
      </header>
      <table class="data-table">
        <thead><tr><th>Фармоиш</th><th>Муштарӣ</th><th>Вазъ</th><th>Сана</th><th>Маблағ</th><th><span class="sr-only">Амалҳо</span></th></tr></thead>
        <tbody>${orders.map(tableRow).join("")}</tbody>
      </table>
      <div class="mobile-cards">${orders.map(mobileCard).join("")}</div>
      ${paginationMarkup()}
    </section>`;
  }

  async function loadOrders() {
    const requestNumber = ++state.requestNumber;
    state.loading = true;
    state.error = "";
    renderResults();
    try {
      const data = await api.get(`/api/orders/${queryString({
        page: state.page,
        page_size: PAGE_SIZE,
        search: state.search,
        status: state.status,
        ordering: "-created_at",
      })}`);
      if (requestNumber !== state.requestNumber || !isMounted()) return;
      state.data = data;
    } catch (error) {
      if (requestNumber !== state.requestNumber || !isMounted()) return;
      state.error = displayError(error, "Фармоишҳоро бор карда натавонистем.");
    } finally {
      if (requestNumber === state.requestNumber && isMounted()) {
        state.loading = false;
        renderResults();
      }
    }
  }

  function mergeConversationContacts(contacts, conversations) {
    const map = new Map(contacts.map((contact) => [String(contact.id), contact]));
    conversations.forEach((conversation) => {
      const contact = conversation.contact_detail;
      if (contact?.id && !map.has(String(contact.id))) map.set(String(contact.id), contact);
    });
    return [...map.values()].sort((a, b) => contactName(a).localeCompare(contactName(b), "tg"));
  }

  async function loadReferences() {
    if (state.referencePromise) return state.referencePromise;
    state.referencesLoading = true;
    state.referencePromise = (async () => {
      const [contactResult, conversationResult] = await Promise.allSettled([
        fetchAllPages(`/api/contacts/${queryString({ page_size: 100, ordering: "name" })}`),
        fetchAllPages(`/api/conversations/${queryString({ page_size: 100, ordering: "-last_message_at" })}`),
      ]);

      state.referenceErrors = [];
      if (contactResult.status === "fulfilled") state.contacts = contactResult.value;
      else state.referenceErrors.push(displayError(contactResult.reason, "Муштариён бор нашуданд."));

      if (conversationResult.status === "fulfilled") state.conversations = conversationResult.value;
      else state.referenceErrors.push(displayError(conversationResult.reason, "Сӯҳбатҳо бор нашуданд."));

      state.contacts = mergeConversationContacts(state.contacts, state.conversations);
    })().finally(() => {
      state.referencesLoading = false;
      state.referencePromise = null;
      if (isMounted()) {
        root.querySelectorAll('[data-action="create"]').forEach((button) => { button.disabled = false; });
        if (state.data && !state.loading) renderResults();
      }
    });
    return state.referencePromise;
  }

  function contactOptions(selected = "") {
    let options = state.contacts.map((contact) => {
      const secondary = contact.phone || (contact.username ? `@${contact.username}` : "") || contact.platform || "";
      const label = secondary ? `${contactName(contact)} — ${secondary}` : contactName(contact);
      return `<option value="${escapeHTML(contact.id)}" ${String(contact.id) === String(selected) ? "selected" : ""}>${escapeHTML(label)}</option>`;
    }).join("");
    if (selected && !state.contacts.some((contact) => String(contact.id) === String(selected))) {
      options += `<option value="${escapeHTML(selected)}" selected>Муштарӣ #${escapeHTML(selected)}</option>`;
    }
    return options;
  }

  function conversationOptions(contactId, selected = "") {
    const available = state.conversations.filter((conversation) => (
      String(entityId(conversation.contact)) === String(contactId)
    ));
    let options = `<option value="">Бе сӯҳбати вобаста</option>`;
    options += available.map((conversation) => {
      const label = conversation.title || `Сӯҳбат #${conversation.id}`;
      const platform = conversation.platform ? ` · ${platformLabel(conversation.platform)}` : "";
      return `<option value="${escapeHTML(conversation.id)}" ${String(conversation.id) === String(selected) ? "selected" : ""}>${escapeHTML(`${label}${platform}`)}</option>`;
    }).join("");
    if (selected && !available.some((conversation) => String(conversation.id) === String(selected))) {
      options += `<option value="${escapeHTML(selected)}" selected>Сӯҳбат #${escapeHTML(selected)}</option>`;
    }
    return options;
  }

  function formErrorMarkup() {
    return `<div class="inline-alert error" data-form-error hidden role="alert">${icon("alert")}<span></span></div>`;
  }

  function showFormError(form, error, fallback) {
    const box = form.querySelector("[data-form-error]");
    if (!box) return;
    box.hidden = false;
    box.querySelector("span").textContent = displayError(error, fallback);
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function itemRowMarkup(index) {
    return `<div class="order-item-row" data-item-row="${index}">
      <label class="field">
        <span class="field-label">Ном</span>
        <input class="field-input" type="text" data-item-name maxlength="255" placeholder="Маҳсулот ё хизматрасонӣ" required>
      </label>
      <label class="field">
        <span class="field-label">Миқдор</span>
        <input class="field-input" type="number" data-item-quantity min="1" step="1" value="1" inputmode="numeric" required>
      </label>
      <label class="field item-price">
        <span class="field-label">Нарх</span>
        <input class="field-input" type="number" data-item-price min="0" step="0.01" value="0.00" inputmode="decimal" required>
      </label>
      <button class="btn btn-ghost btn-icon" type="button" data-remove-item aria-label="Нест кардани мавод">${icon("trash")}</button>
    </div>`;
  }

  function openNoContactsModal() {
    const modal = openModal({
      title: "Фармоиши нав",
      body: emptyState({
        iconName: state.referenceErrors.length ? "alert" : "contacts",
        title: state.referenceErrors.length ? "Муштариён бор нашуданд" : "Ҳоло муштарӣ нест",
        text: state.referenceErrors.length
          ? state.referenceErrors.join(" ")
          : "Фармоиш бояд ба муштарӣ вобаста бошад. Муштариён баъди гирифтани паём аз Telegram, WhatsApp ё Instagram пайдо мешаванд.",
        action: `<button class="btn btn-secondary btn-sm" type="button" data-retry-references>${icon("refresh")} Аз нав санҷидан</button>`,
      }),
      footer: `<button class="btn btn-secondary" type="button" data-modal-close>Пӯшидан</button>`,
    });
    modal.querySelector("[data-retry-references]")?.addEventListener("click", async (event) => {
      setButtonLoading(event.currentTarget, true, "Санҷиш...");
      await loadReferences();
      if (!modal.isConnected) return;
      closeModal();
      if (state.contacts.length) openCreateModal();
      else openNoContactsModal();
    });
  }

  function openCreateModal() {
    if (state.referencesLoading) {
      toast("Каме интизор шавед", "Рӯйхати муштариён ҳоло бор мешавад.", "error");
      return;
    }
    if (!state.contacts.length) {
      openNoContactsModal();
      return;
    }

    const initialContact = state.contacts[0]?.id || "";
    const formId = `create-order-${Date.now()}`;
    const modal = openModal({
      title: "Фармоиши нав",
      wide: true,
      body: `<form class="stack" id="${formId}" data-create-order-form>
        ${formErrorMarkup()}
        ${state.referenceErrors.length ? `<div class="form-note">${icon("info")} ${escapeHTML(state.referenceErrors.join(" "))} Фармоишро бе сӯҳбат ҳам сабт кардан мумкин аст.</div>` : ""}
        <div class="form-grid two">
          <label class="field">
            <span class="field-label">Муштарӣ</span>
            <select class="field-select" name="contact" required>${contactOptions(initialContact)}</select>
          </label>
          <label class="field">
            <span class="field-label">Сӯҳбат <span class="optional">(ихтиёрӣ)</span></span>
            <select class="field-select" name="conversation">${conversationOptions(initialContact)}</select>
          </label>
          <label class="field">
            <span class="field-label">ID-и беруна <span class="optional">(ихтиёрӣ)</span></span>
            <input class="field-input" type="text" name="external_id" maxlength="255" placeholder="Масалан, WEB-1042">
          </label>
          <label class="field">
            <span class="field-label">Вазъ</span>
            <select class="field-select" name="status">${statusOptions("new")}</select>
          </label>
        </div>
        <label class="field">
          <span class="field-label">Тавсиф <span class="optional">(ихтиёрӣ)</span></span>
          <textarea class="field-textarea" name="description" placeholder="Шарҳи кӯтоҳи фармоиш..."></textarea>
        </label>
        <div class="form-grid two">
          <label class="field">
            <span class="field-label">Асъор</span>
            <input class="field-input" type="text" name="currency" value="TJS" maxlength="10" list="order-currencies" required>
            <datalist id="order-currencies"><option value="TJS"><option value="USD"><option value="RUB"><option value="EUR"></datalist>
          </label>
          <label class="field">
            <span class="field-label">Маблағи умумӣ</span>
            <input class="field-input" type="number" name="amount" value="0.00" min="0" step="0.01" readonly>
            <span class="field-hint">Аз рӯйи маводҳо худкор ҳисоб мешавад.</span>
          </label>
        </div>
        <div class="compact-row">
          <div class="compact-row-copy"><strong>Маводҳои фармоиш</strong><span>Ном, миқдор ва нархи ҳар маводро ворид кунед.</span></div>
          <button class="btn btn-secondary btn-sm" type="button" data-add-item>${icon("plus")} Илова</button>
        </div>
        <div class="order-items" data-order-items>${itemRowMarkup(0)}</div>
        <div class="compact-row">
          <span class="muted">Ҷамъи маводҳо</span>
          <strong class="order-total" data-items-total>${moneyMarkup(0, "TJS")}</strong>
        </div>
      </form>`,
      footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button><button class="btn btn-primary" type="submit" form="${formId}" data-create-submit>${icon("check")} Сабт кардан</button>`,
    });

    const form = modal.querySelector("[data-create-order-form]");
    const itemsContainer = form.querySelector("[data-order-items]");
    const amountInput = form.elements.amount;
    const currencyInput = form.elements.currency;
    const conversationSelect = form.elements.conversation;
    let itemIndex = 1;

    const calculateTotal = () => {
      const total = [...itemsContainer.querySelectorAll("[data-item-row]")].reduce((sum, row) => {
        const quantity = Number(row.querySelector("[data-item-quantity]").value);
        const price = Number(row.querySelector("[data-item-price]").value);
        return sum + ((Number.isFinite(quantity) ? quantity : 0) * (Number.isFinite(price) ? price : 0));
      }, 0);
      const rounded = Math.round((total + Number.EPSILON) * 100) / 100;
      amountInput.value = rounded.toFixed(2);
      form.querySelector("[data-items-total]").textContent = formatMoney(rounded, currencyInput.value.trim().toUpperCase() || "TJS");
      const rows = itemsContainer.querySelectorAll("[data-item-row]");
      rows.forEach((row) => { row.querySelector("[data-remove-item]").disabled = rows.length === 1; });
      return rounded;
    };

    form.elements.contact.addEventListener("change", () => {
      conversationSelect.innerHTML = conversationOptions(form.elements.contact.value);
    });
    form.querySelector("[data-add-item]").addEventListener("click", () => {
      itemsContainer.insertAdjacentHTML("beforeend", itemRowMarkup(itemIndex++));
      calculateTotal();
      itemsContainer.lastElementChild.querySelector("[data-item-name]").focus();
    });
    itemsContainer.addEventListener("click", (event) => {
      const remove = event.target.closest("[data-remove-item]");
      if (!remove || itemsContainer.querySelectorAll("[data-item-row]").length === 1) return;
      remove.closest("[data-item-row]").remove();
      calculateTotal();
    });
    itemsContainer.addEventListener("input", calculateTotal);
    currencyInput.addEventListener("input", calculateTotal);
    calculateTotal();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = modal.querySelector("[data-create-submit]");
      const itemRows = [...itemsContainer.querySelectorAll("[data-item-row]")];
      const items = itemRows.map((row) => ({
        name: row.querySelector("[data-item-name]").value.trim(),
        quantity: Number(row.querySelector("[data-item-quantity]").value),
        price: Number(row.querySelector("[data-item-price]").value).toFixed(2),
        metadata: {},
      }));
      const payload = {
        contact: Number(form.elements.contact.value),
        conversation: conversationSelect.value ? Number(conversationSelect.value) : null,
        external_id: form.elements.external_id.value.trim(),
        description: form.elements.description.value.trim(),
        amount: calculateTotal().toFixed(2),
        currency: currencyInput.value.trim().toUpperCase() || "TJS",
        status: form.elements.status.value,
        items,
      };

      form.querySelector("[data-form-error]").hidden = true;
      setButtonLoading(submit, true, "Сабт мешавад...");
      try {
        await api.post("/api/orders/", payload);
        closeModal();
        toast("Фармоиш сабт шуд", "Фармоиши нав ба рӯйхат илова гардид.");
        state.page = 1;
        await loadOrders();
        refreshShell(app);
      } catch (error) {
        showFormError(form, error, "Фармоиш сабт нашуд.");
        setButtonLoading(submit, false);
      }
    });
  }

  function detailMarkup(order) {
    const contactId = entityId(order.contact);
    const contact = contactFor(contactId);
    const conversationId = entityId(order.conversation);
    const conversation = conversationFor(conversationId);
    const orderItems = Array.isArray(order.items) ? order.items : [];
    const itemList = orderItems.length ? `<div class="compact-list">${orderItems.map((item) => {
      const quantity = Number(item.quantity || 0);
      const price = Number(item.price || 0);
      const total = item.total ?? (quantity * price);
      return `<div class="compact-row"><div class="compact-row-copy"><strong>${escapeHTML(item.name || "Мавод")}</strong><span>${quantity.toLocaleString("tg-TJ")} × ${moneyMarkup(price, order.currency)}</span></div><strong>${moneyMarkup(total, order.currency)}</strong></div>`;
    }).join("")}</div>` : `<div class="form-note">Барои ин фармоиш маводи алоҳида сабт нашудааст.</div>`;

    return `<div class="stack">
      <div class="conversation-mini">
        ${avatar(contact || { name: contactName(null, contactId) })}
        <div class="conversation-mini-copy"><strong>${escapeHTML(orderTitle(order))}</strong><p>${escapeHTML(contactName(contact, contactId))}${contact?.platform ? ` · ${platformBadge(contact.platform)}` : ""}</p></div>
        <div class="conversation-mini-meta">${statusBadge(order.status)}</div>
      </div>
      <div class="detail-grid">
        <div class="detail-item"><span>Маблағ</span><strong>${moneyMarkup(order.amount, order.currency)}</strong></div>
        <div class="detail-item"><span>ID-и беруна</span><strong>${escapeHTML(order.external_id || "—")}</strong></div>
        <div class="detail-item"><span>Сӯҳбат</span><strong>${escapeHTML(conversation ? (conversation.title || `#${conversation.id}`) : (conversationId ? `#${conversationId}` : "Пайваст нашудааст"))}</strong></div>
        <div class="detail-item"><span>Санаи сабт</span><strong>${escapeHTML(formatDate(order.created_at))}</strong></div>
        <div class="detail-item"><span>Охирин навсозӣ</span><strong>${escapeHTML(formatDate(order.updated_at))}</strong></div>
        <div class="detail-item"><span>Санаи анҷом</span><strong>${escapeHTML(formatDate(order.completed_at))}</strong></div>
      </div>
      <div><div class="field-label">Тавсиф</div><div class="form-note">${order.description ? escapeHTML(order.description).replace(/\n/g, "<br>") : "Тавсиф ворид нашудааст."}</div></div>
      <div><div class="compact-row"><div class="compact-row-copy"><strong>Маводҳо</strong><span>${orderItems.length.toLocaleString("tg-TJ")} номгӯй</span></div><strong>${moneyMarkup(orderItems.reduce((sum, item) => sum + Number(item.total ?? (Number(item.quantity || 0) * Number(item.price || 0))), 0), order.currency)}</strong></div>${itemList}</div>
    </div>`;
  }

  function openOrderDetails(orderOrId) {
    const id = entityId(orderOrId?.id ?? orderOrId);
    let currentOrder = typeof orderOrId === "object" ? orderOrId : findOrder(id);
    const modal = openModal({
      title: `Фармоиш ${currentOrder ? orderTitle(currentOrder) : `#${id}`}`,
      wide: true,
      body: `<div data-order-detail><div class="empty-state"><div><span class="loading-spinner" style="color:var(--primary)" aria-hidden="true"></span><h3>Маълумот бор мешавад</h3></div></div></div>`,
      footer: `<button class="btn btn-secondary" type="button" data-modal-close>Пӯшидан</button><button class="btn btn-secondary" type="button" data-open-linked-conversation hidden>${icon("messages")} Ба сӯҳбат</button><button class="btn btn-secondary" type="button" data-detail-edit disabled>${icon("edit")} Таҳрир</button><button class="btn btn-danger" type="button" data-detail-delete disabled>${icon("trash")} Нест кардан</button>`,
    });
    const detail = modal.querySelector("[data-order-detail]");
    const editButton = modal.querySelector("[data-detail-edit]");
    const deleteButton = modal.querySelector("[data-detail-delete]");
    const conversationButton = modal.querySelector("[data-open-linked-conversation]");

    const loadDetail = async () => {
      detail.innerHTML = `<div class="empty-state"><div><span class="loading-spinner" style="color:var(--primary)" aria-hidden="true"></span><h3>Маълумот бор мешавад</h3></div></div>`;
      editButton.disabled = true;
      deleteButton.disabled = true;
      try {
        currentOrder = await api.get(`/api/orders/${encodeURIComponent(id)}/`);
        if (!modal.isConnected) return;
        detail.innerHTML = detailMarkup(currentOrder);
        editButton.disabled = false;
        deleteButton.disabled = false;
        const conversationId = entityId(currentOrder.conversation);
        conversationButton.hidden = !conversationId;
        if (conversationId) conversationButton.dataset.conversation = conversationId;
      } catch (error) {
        if (!modal.isConnected) return;
        detail.innerHTML = emptyState({
          iconName: "alert",
          title: "Маълумот бор нашуд",
          text: displayError(error),
          action: `<button class="btn btn-primary btn-sm" type="button" data-detail-retry>${icon("refresh")} Дубора кӯшиш</button>`,
        });
      }
    };

    detail.addEventListener("click", (event) => {
      if (event.target.closest("[data-detail-retry]")) loadDetail();
    });
    editButton.addEventListener("click", () => {
      if (!currentOrder) return;
      closeModal();
      openEditModal(currentOrder);
    });
    deleteButton.addEventListener("click", () => {
      if (!currentOrder) return;
      closeModal();
      deleteOrder(currentOrder);
    });
    conversationButton.addEventListener("click", () => {
      const conversationId = conversationButton.dataset.conversation;
      if (!conversationId) return;
      closeModal();
      app.navigate(`/messages?conversation=${encodeURIComponent(conversationId)}`);
    });
    loadDetail();
  }

  function openEditModal(order) {
    const contactId = entityId(order.contact);
    const conversationId = entityId(order.conversation) || "";
    const formId = `edit-order-${order.id}-${Date.now()}`;
    const modal = openModal({
      title: `Таҳрири ${orderTitle(order)}`,
      wide: true,
      body: `<form class="stack" id="${formId}" data-edit-order-form>
        ${formErrorMarkup()}
        <div class="form-grid two">
          <label class="field"><span class="field-label">Муштарӣ</span><select class="field-select" name="contact" required>${contactOptions(contactId)}</select></label>
          <label class="field"><span class="field-label">Сӯҳбат <span class="optional">(ихтиёрӣ)</span></span><select class="field-select" name="conversation">${conversationOptions(contactId, conversationId)}</select></label>
          <label class="field"><span class="field-label">ID-и беруна</span><input class="field-input" type="text" name="external_id" maxlength="255" value="${escapeHTML(order.external_id || "")}"></label>
          <label class="field"><span class="field-label">Вазъ</span><select class="field-select" name="status">${statusOptions(order.status)}</select></label>
          <label class="field"><span class="field-label">Маблағ</span><input class="field-input" type="number" name="amount" min="0" step="0.01" value="${escapeHTML(order.amount ?? "0.00")}" required></label>
          <label class="field"><span class="field-label">Асъор</span><input class="field-input" type="text" name="currency" maxlength="10" value="${escapeHTML(order.currency || "TJS")}" required></label>
        </div>
        <label class="field"><span class="field-label">Тавсиф <span class="optional">(ихтиёрӣ)</span></span><textarea class="field-textarea" name="description">${escapeHTML(order.description || "")}</textarea></label>
        <div class="form-note">${icon("info")} Маводҳои дохили фармоиш дар ин равзана тағйир намеёбанд.</div>
      </form>`,
      footer: `<button class="btn btn-secondary" type="button" data-modal-close>Бекор</button><button class="btn btn-primary" type="submit" form="${formId}" data-edit-submit>${icon("check")} Нигоҳ доштан</button>`,
    });
    const form = modal.querySelector("[data-edit-order-form]");
    const conversationSelect = form.elements.conversation;
    form.elements.contact.addEventListener("change", () => {
      conversationSelect.innerHTML = conversationOptions(form.elements.contact.value);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = modal.querySelector("[data-edit-submit]");
      // Items are intentionally omitted: this edit flow updates only the order's basic fields.
      const payload = {
        contact: Number(form.elements.contact.value),
        conversation: conversationSelect.value ? Number(conversationSelect.value) : null,
        external_id: form.elements.external_id.value.trim(),
        description: form.elements.description.value.trim(),
        amount: Number(form.elements.amount.value).toFixed(2),
        currency: form.elements.currency.value.trim().toUpperCase() || "TJS",
        status: form.elements.status.value,
      };
      form.querySelector("[data-form-error]").hidden = true;
      setButtonLoading(submit, true, "Нигоҳдорӣ...");
      try {
        await api.patch(`/api/orders/${encodeURIComponent(order.id)}/`, payload);
        closeModal();
        toast("Фармоиш нав шуд", "Тағйирот бомуваффақият нигоҳ дошта шуд.");
        await loadOrders();
        refreshShell(app);
      } catch (error) {
        showFormError(form, error, "Тағйирот нигоҳ дошта нашуд.");
        setButtonLoading(submit, false);
      }
    });
  }

  async function deleteOrder(order) {
    const confirmed = await confirmAction({
      title: "Нест кардани фармоиш",
      message: `Фармоиши ${orderTitle(order)} пурра нест карда шавад? Ин амал баргардонида намешавад.`,
      confirmText: "Нест кардан",
      danger: true,
    });
    if (!confirmed || !isMounted()) return;

    state.requestNumber += 1;
    state.loading = true;
    renderResults();
    try {
      await api.delete(`/api/orders/${encodeURIComponent(order.id)}/`);
      if (state.page > 1 && currentRows().length === 1) state.page -= 1;
      toast("Фармоиш нест шуд", `Фармоиши ${orderTitle(order)} аз рӯйхат бардошта шуд.`);
      await loadOrders();
      refreshShell(app);
    } catch (error) {
      state.loading = false;
      renderResults();
      toast("Фармоиш нест нашуд", displayError(error), "error");
    }
  }

  const runSearch = debounce(() => {
    if (!isMounted()) return;
    const nextSearch = searchInput.value.trim();
    if (nextSearch === state.search) return;
    state.search = nextSearch;
    state.page = 1;
    loadOrders();
  }, 350);

  searchInput.addEventListener("input", runSearch);
  searchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const nextSearch = searchInput.value.trim();
    if (nextSearch === state.search) return;
    state.search = nextSearch;
    state.page = 1;
    loadOrders();
  });
  statusSelect.addEventListener("change", () => {
    state.status = statusSelect.value;
    state.page = 1;
    loadOrders();
  });

  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || !root.contains(button) || button.disabled) return;
    const action = button.dataset.action;
    const order = button.dataset.id ? findOrder(button.dataset.id) : null;

    if (action === "create") openCreateModal();
    else if (action === "view" && order) openOrderDetails(order);
    else if (action === "edit" && order) openEditModal(order);
    else if (action === "delete" && order) deleteOrder(order);
    else if (action === "retry") loadOrders();
    else if (action === "clear-filters") {
      state.search = "";
      state.status = "";
      state.page = 1;
      searchInput.value = "";
      statusSelect.value = "";
      loadOrders();
    } else if (action === "page") {
      const page = Number(button.dataset.page);
      if (!Number.isInteger(page) || page < 1 || page === state.page) return;
      state.page = page;
      loadOrders();
      root.querySelector(".filter-bar")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  app.activeRefresh = () => {
    if (isMounted()) loadOrders();
  };

  renderResults();
  await Promise.allSettled([loadReferences(), loadOrders()]);
}
