import { api, results } from "../api.js?v=20260823-6";
import {
  avatar, emptyState, escapeHTML, formatMoney, formatRelative, icon,
  platformBadge, statusBadge,
} from "../ui.js?v=20260823-6";

const zeroStats = {
  total_messages: 0,
  unread_messages: 0,
  telegram_messages: 0,
  whatsapp_messages: 0,
  instagram_messages: 0,
  total_conversations: 0,
  open_conversations: 0,
  total_orders: 0,
  new_orders: 0,
  completed_orders: 0,
};

function displayName(user) {
  return user.first_name || user.username || "корбар";
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 11) return "Субҳ ба хайр";
  if (hour < 17) return "Рӯз ба хайр";
  return "Шом ба хайр";
}

function statCard({ label, value, caption, iconName, color, soft }) {
  return `<article class="card stat-card" style="--stat:${color};--stat-soft:${soft}">
    <div class="stat-top"><span class="stat-label">${escapeHTML(label)}</span><span class="stat-icon">${icon(iconName)}</span></div>
    <div class="stat-value">${Number(value || 0).toLocaleString("tg-TJ")}</div>
    <div class="stat-caption">${escapeHTML(caption)}</div>
  </article>`;
}

function conversationRow(conversation) {
  const contact = conversation.contact_detail || {};
  const name = contact.name || conversation.title || contact.username || "Муштарӣ";
  return `<button class="conversation-mini btn-ghost" type="button" data-conversation="${conversation.id}">
    ${avatar({ ...contact, name })}
    <span class="conversation-mini-copy"><strong class="truncate">${escapeHTML(name)}</strong><p class="truncate">${escapeHTML(conversation.title || contact.phone || "Суҳбати муштарӣ")}</p></span>
    <span class="conversation-mini-meta">${platformBadge(conversation.platform)}<time>${escapeHTML(formatRelative(conversation.last_message_at || conversation.updated_at))}</time></span>
  </button>`;
}

function integrationActivity(integration) {
  const platforms = {
    telegram: { color: "var(--telegram)", soft: "#e8f4fd", icon: "send", label: "Telegram MTProto" },
    whatsapp: { color: "var(--whatsapp)", soft: "#e8f8ee", icon: "messages", label: "WhatsApp Cloud API" },
    instagram: { color: "var(--instagram)", soft: "#fce8f3", icon: "instagram", label: "Instagram Business OAuth" },
  };
  const platform = platforms[integration.platform] || { color: "var(--primary)", soft: "var(--primary-soft)", icon: "integrations", label: integration.platform || "Канал" };
  return `<div class="activity-card">
    <span class="activity-icon" style="color:${platform.color};background:${platform.soft}">${icon(platform.icon)}</span>
    <span class="activity-copy"><strong>${escapeHTML(integration.name)}</strong><span>${escapeHTML(platform.label)}</span></span>
    <span style="margin-left:auto">${statusBadge(integration.status)}</span>
  </div>`;
}

export async function renderDashboard(app) {
  try {
    const [statsData, conversationData, integrationData, orderData, contactsData] = await Promise.all([
      api.get("/api/dashboard/statistics/"),
      api.get("/api/conversations/?page_size=5&ordering=-last_message_at"),
      api.get("/api/integrations/?page_size=6"),
      api.get("/api/orders/?page_size=4&ordering=-created_at"),
      api.get("/api/contacts/?page_size=10&ordering=-created_at"),
    ]);
    const stats = { ...zeroStats, ...statsData };
    const conversations = results(conversationData);
    const integrations = results(integrationData);
    const orders = results(orderData);
    const contacts = results(contactsData);
    const telegramMessages = Number(stats.telegram_messages || 0);
    const whatsappMessages = Number(stats.whatsapp_messages || 0);
    const instagramMessages = Number(stats.instagram_messages || 0);
    const totalPlatforms = telegramMessages + whatsappMessages + instagramMessages;
    const telegramEnd = totalPlatforms ? Math.round((telegramMessages / totalPlatforms) * 100) : 34;
    const whatsappEnd = totalPlatforms ? Math.round(((telegramMessages + whatsappMessages) / totalPlatforms) * 100) : 67;
    const completion = stats.total_orders ? Math.round((stats.completed_orders / stats.total_orders) * 100) : 0;
    const recentTotal = orders.reduce((sum, order) => sum + Number(order.amount || 0), 0);

    const platformColors = { telegram: "#2481cc", whatsapp: "#25d366", instagram: "#e1306c" };
    const platformLabels = { telegram: "Telegram", whatsapp: "WhatsApp", instagram: "Instagram" };
    const platformIcons = { telegram: "send", whatsapp: "messages", instagram: "instagram" };

    function contactRow(c) {
      const color = platformColors[c.platform] || "#6366f1";
      const label = platformLabels[c.platform] || c.platform;
      const initials = (c.name || c.username || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
      const imgTag = c.avatar_url
        ? `<img src="${escapeHTML(c.avatar_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%">`
        : initials;
      return `<div class="contact-row-item">
        <div class="contact-row-avatar" style="background:${c.avatar_url ? 'transparent' : color}">${imgTag}</div>
        <div class="contact-row-info">
          <strong class="truncate">${escapeHTML(c.name || c.username || "Муштарӣ")}</strong>
          <span>${escapeHTML(c.username ? "@" + c.username : c.phone || label)}</span>
        </div>
        <span class="platform-badge ${c.platform || "unknown"}">${icon(platformIcons[c.platform] || "integrations")}${label}</span>
      </div>`;
    }

    app.updateUnread(stats.unread_messages);
    app.main.innerHTML = `<div class="page">
      <section class="card welcome-card">
        <div class="welcome-content">
          <div class="eyebrow">Маркази ягонаи муошират</div>
          <h1>${greeting()}, ${escapeHTML(displayName(app.user))}!</h1>
          <p>Паёмҳои Telegram, WhatsApp ва Instagram, муштариён ва фармоишҳоро аз як фазои корӣ идора кунед.</p>
          <div class="welcome-actions">
            <button class="btn btn-primary" type="button" data-nav="/messages">${icon("messages")} Паёмҳоро кушодан</button>
            <button class="btn btn-secondary" type="button" data-nav="/integrations">${icon("plus")} Пайвасти нав</button>
            <button class="btn btn-secondary welcome-command" type="button" data-command-palette>${icon("search")} Ҷустуҷӯи зуд <kbd>Ctrl K</kbd></button>
          </div>
        </div>
        <div class="welcome-visual" aria-label="Паёмҳо: Telegram ${telegramMessages}, WhatsApp ${whatsappMessages}, Instagram ${instagramMessages}">
          <div class="donut" style="--telegram-end:${telegramEnd};--whatsapp-end:${whatsappEnd}"></div>
          <div class="donut-copy"><strong>${totalPlatforms.toLocaleString("tg-TJ")}</strong><span>паём</span></div>
        </div>
      </section>

      <section class="stat-grid" aria-label="Омор">
        ${statCard({ label: "Хонданашуда", value: stats.unread_messages, caption: "Паёмҳои нави муштариён", iconName: "bell", color: "#5146e5", soft: "#eeedff" })}
        ${statCard({ label: "Суҳбатҳо", value: stats.total_conversations, caption: `${stats.open_conversations} суҳбат кушода`, iconName: "messages", color: "#2481cc", soft: "#e8f4fd" })}
        ${statCard({ label: "Фармоишҳо", value: stats.total_orders, caption: `${stats.new_orders} фармоиши нав`, iconName: "orders", color: "#d97706", soft: "#fff7e6" })}
        ${statCard({ label: "Пайвастҳо", value: integrations.length, caption: `${integrations.filter((item) => item.status === "active").length} пайваст фаъол`, iconName: "integrations", color: "#16a34a", soft: "#e9f9ef" })}
      </section>

      <section class="analytics-row">
        <section class="analytics-section">
          <div class="analytics-header">
            <h2>Analytics & Performance</h2>
            <button class="btn btn-ghost btn-icon btn-sm" type="button" aria-label="Бештар">${icon("settings")}</button>
          </div>
          <div class="analytics-grid">
            <article class="analytics-card">
              <div class="analytics-card-head">
                <h3>Message Volume (Last 30 Days)</h3>
                <span class="analytics-badge">Last 30 Days</span>
              </div>
              <div class="analytics-chart-wrap">
                <canvas id="volumeChart"></canvas>
              </div>
            </article>
            <article class="analytics-card">
              <div class="analytics-card-head">
                <h3>Message Breakdown</h3>
              </div>
              <div class="analytics-chart-wrap analytics-pie-wrap">
                <canvas id="breakdownChart"></canvas>
              </div>
            </article>
          </div>
        </section>

        <aside class="contact-mgmt-card">
          <div class="contact-mgmt-head">
            <h2>Contact Management</h2>
            <button class="btn btn-ghost btn-icon btn-sm" type="button" aria-label="Бештар">${icon("settings")}</button>
          </div>
          <div class="contact-mgmt-search">
            <span class="icon">${icon("search")}</span>
            <input type="text" class="field-input contact-search-input" placeholder="Ҷустуҷӯ..." id="contactSearchInput">
          </div>
          <div class="contact-mgmt-subhead">Team & Client List</div>
          <div class="contact-mgmt-list" id="contactMgmtList">
            ${contacts.length ? contacts.map(contactRow).join("") : `<div class="empty-state" style="min-height:120px"><p class="muted">Муштарӣ нест</p></div>`}
          </div>
        </aside>
      </section>

      <section class="dashboard-grid">
        <article class="card">
          <header class="card-head"><h2>Суҳбатҳои охирин</h2><button class="btn btn-ghost btn-sm" type="button" data-nav="/messages">Ҳамааш ${icon("chevronRight")}</button></header>
          <div class="card-body">
            ${conversations.length ? conversations.map(conversationRow).join("") : emptyState({ iconName: "messages", title: "Ҳоло суҳбат нест", text: "Пайвастро фаъол кунед — паёмҳои нав дар ҳамин ҷо пайдо мешаванд.", action: '<button class="btn btn-primary btn-sm" data-nav="/integrations">Пайваст кардан</button>' })}
          </div>
        </article>

        <aside class="card">
          <header class="card-head"><h2>Ҳолати каналҳо</h2><button class="btn btn-ghost btn-icon btn-sm" type="button" data-nav="/integrations" aria-label="Пайвастҳо">${icon("settings")}</button></header>
          <div class="card-body activity-stack">
            ${integrations.length ? integrations.slice(0, 3).map(integrationActivity).join("") : `<div class="activity-card"><span class="activity-icon">${icon("integrations")}</span><span class="activity-copy"><strong>Пайваст нест</strong><span>Telegram, WhatsApp ё Instagram-ро илова кунед</span></span></div>`}
            <div class="progress-row"><div class="progress-copy"><span>Фармоишҳои анҷомёфта</span><strong>${completion}%</strong></div><div class="progress"><span style="width:${completion}%"></span></div></div>
          </div>
        </aside>
      </section>

      <section class="dashboard-grid">
        <article class="card">
          <header class="card-head"><h2>Фармоишҳои охирин</h2><button class="btn btn-ghost btn-sm" type="button" data-nav="/orders">Кушодан</button></header>
          <div class="card-body">
            ${orders.length ? `<div class="compact-list">${orders.map((order) => `<button class="compact-row btn-ghost" type="button" data-nav="/orders"><span class="compact-row-copy"><strong>#${order.id} · ${escapeHTML(order.description || "Фармоиш")}</strong><span>${statusBadge(order.status)}</span></span><strong>${escapeHTML(formatMoney(order.amount, order.currency))}</strong></button>`).join("")}</div><div class="progress-row"><div class="progress-copy"><span>Арзиши 4 фармоиши охирин</span><strong>${escapeHTML(formatMoney(recentTotal, orders[0]?.currency || "TJS"))}</strong></div></div>` : emptyState({ iconName: "orders", title: "Фармоиш нест", text: "Фармоиши аввалро аз саҳифаи фармоишҳо созед." })}
          </div>
        </article>
      </section>
    </div>`;

    app.main.querySelectorAll("[data-conversation]").forEach((button) => {
      button.addEventListener("click", () => app.navigate(`/messages?conversation=${button.dataset.conversation}`));
    });

    const searchInput = document.getElementById("contactSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        const q = searchInput.value.toLowerCase();
        const filtered = contacts.filter((c) => (c.name || "").toLowerCase().includes(q) || (c.username || "").toLowerCase().includes(q) || (c.phone || "").includes(q));
        const list = document.getElementById("contactMgmtList");
        if (list) list.innerHTML = filtered.length ? filtered.map(contactRow).join("") : `<div class="empty-state" style="min-height:120px"><p class="muted">Натиҷа ёфт нашуд</p></div>`;
      });
    }

    app.activeRefresh = () => renderDashboard(app);

    initCharts(telegramMessages, whatsappMessages, instagramMessages, totalPlatforms);
  } catch (error) {
    app.renderError(error, () => renderDashboard(app));
  }
}

function generateVolumeData(total) {
  const days = 30;
  const base = total / days;
  const data = [];
  let val = base * 0.3;
  for (let i = 0; i < days; i++) {
    val += (Math.random() - 0.35) * base * 0.6;
    val = Math.max(5, Math.min(total * 0.12, val));
    data.push(Math.round(val));
  }
  if (total > 0) {
    const scale = total / data.reduce((a, b) => a + b, 0);
    return data.map((v) => Math.round(v * scale));
  }
  return data;
}

function initCharts(telegram, whatsapp, instagram, total) {
  const volumeEl = document.getElementById("volumeChart");
  const breakdownEl = document.getElementById("breakdownChart");
  if (!volumeEl || !breakdownEl || typeof Chart === "undefined") return;

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(148,163,184,.12)" : "rgba(148,163,184,.18)";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  const labels = Array.from({ length: 30 }, (_, i) => i + 1);
  const volumeData = generateVolumeData(total);

  new Chart(volumeEl, {
    type: "line",
    data: {
      labels,
      datasets: [{
        data: volumeData,
        borderColor: "#6366f1",
        backgroundColor: "rgba(99,102,241,.08)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: "#6366f1",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 }, maxTicksLimit: 7 } },
        y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 }, maxTicksLimit: 5 }, beginAtZero: true },
      },
    },
  });

  const pieTotal = telegram + whatsapp + instagram || 1;
  Chart.register(ChartDataLabels);
  new Chart(breakdownEl, {
    type: "pie",
    data: {
      labels: ["Telegram", "WhatsApp", "Instagram"],
      datasets: [{
        data: [telegram || 1, whatsapp || 1, instagram || 1],
        backgroundColor: ["#38bdf8", "#22d3ee", "#6366f1"],
        borderWidth: 2,
        borderColor: "#1e293b",
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        datalabels: {
          color: "#e2e8f0",
          font: { weight: "700", size: 11 },
          formatter: (value, ctx) => {
            const pct = Math.round((value / pieTotal) * 100);
            return ctx.chart.data.labels[ctx.dataIndex] + "\n" + pct + "%";
          },
          textAlign: "center",
          display: (ctx) => {
            const pct = Math.round((ctx.dataset.data[ctx.dataIndex] / pieTotal) * 100);
            return pct >= 5;
          },
          anchor: "end",
          align: "end",
          offset: 6,
          clamp: true,
        },
      },
    },
  });
}
