import { icon } from "../ui.js?v=20260822-8";

function dashboardPreview(className = "") {
  return `
    <div class="landing-dashboard ${className}" aria-label="Намоиши панели идоракунии Munis">
      <aside class="landing-dashboard-sidebar">
        <div class="landing-dashboard-brand"><span class="landing-dashboard-logo">M</span><strong>MUNIS</strong></div>
        <div class="landing-dashboard-nav" aria-hidden="true">
          <span>${icon("dashboard")}<i>Шарҳ</i></span>
          <span class="active">${icon("messages")}<i>Паёмҳо</i><b>24</b></span>
          <span>${icon("contacts")}<i>Тамосҳо</i></span>
          <span>${icon("orders")}<i>Фармоишҳо</i></span>
          <span>${icon("integrations")}<i>Пайвастҳо</i></span>
        </div>
        <span class="landing-dashboard-user"><i>М</i><span><strong>Муҳаммад</strong><small>Соҳиби бизнес</small></span></span>
      </aside>

      <div class="landing-dashboard-main">
        <header class="landing-dashboard-top">
          <span><strong>Субҳ ба хайр!</strong><small>Ҳамаи каналҳо фаъоланд</small></span>
          <span class="landing-dashboard-actions">${icon("search")} ${icon("bell")}</span>
        </header>

        <div class="landing-preview-stats">
          <article><span class="violet">${icon("messages")}</span><small>Хонданашуда</small><strong>24</strong><em>+8 имрӯз</em></article>
          <article><span class="blue">${icon("contacts")}</span><small>Суҳбатҳо</small><strong>86</strong><em>12 фаъол</em></article>
          <article><span class="orange">${icon("orders")}</span><small>Фармоишҳо</small><strong>17</strong><em>5 нав</em></article>
        </div>

        <div class="landing-dashboard-content">
          <section class="landing-conversation-list">
            <header><span><strong>Суҳбатҳои охирин</strong><small>Имрӯз</small></span><span class="landing-mini-filter">${icon("filter")} Ҳама</span></header>
            <div class="landing-conversation active"><i class="avatar-violet">А</i><span><strong>Алишер</strong><small>Нархаш чанд сомонӣ?</small></span><time>10:42</time><b class="platform telegram">${icon("send")}</b></div>
            <div class="landing-conversation"><i class="avatar-green">М</i><span><strong>Мадина</strong><small>Фармоиш омода шуд?</small></span><time>10:18</time><b class="platform whatsapp">${icon("messages")}</b></div>
            <div class="landing-conversation"><i class="avatar-blue">Ф</i><span><strong>Фарид</strong><small>Раҳмат, қабул кардам</small></span><time>09:54</time><b class="platform instagram">${icon("instagram")}</b></div>
          </section>

          <section class="landing-message-card">
            <header><span class="landing-message-avatar">А</span><span><strong>Алишер</strong><small><i></i> online · Telegram</small></span>${icon("more")}</header>
            <div class="landing-message-body">
              <span class="bubble received">Салом! Нархаш чанд сомонӣ?</span>
              <span class="bubble sent">Салом! 180 сомонӣ. Имрӯз дастрас аст.</span>
              <small>Ҷавоб дар 38 сония</small>
            </div>
            <footer><span>Паём нависед...</span>${icon("send")}</footer>
          </section>
        </div>
      </div>
    </div>`;
}

function flowStep(number, iconName, title, text, tone = "violet") {
  return `
    <li class="landing-flow-step ${tone}">
      <span class="landing-step-icon">${icon(iconName)}</span>
      <span class="landing-step-copy"><b>${String(number).padStart(2, "0")}</b><strong>${title}</strong><small>${text}</small></span>
    </li>`;
}

function securityCard(iconName, title, text) {
  return `
    <article class="landing-security-card">
      <span>${icon(iconName)}</span>
      <div><h3>${title}</h3><p>${text}</p></div>
      <i>${icon("check")}</i>
    </article>`;
}

export function renderLanding(app) {
  const mount = app?.root || app?.main || document.querySelector("#app");
  if (!mount) return;

  document.title = "Munis Business Hub — Telegram, WhatsApp ва Instagram дар як марказ";
  window.scrollTo({ top: 0, behavior: "auto" });

  mount.innerHTML = `
    <div class="landing-page">
      <a class="landing-skip" href="#landing-main">Ба муҳтавои асосӣ гузаред</a>

      <header class="landing-header">
        <div class="landing-container landing-header-inner">
          <a class="landing-brand" href="#top" aria-label="Munis Business Hub — саҳифаи асосӣ">
            <span class="landing-brand-mark" aria-hidden="true"><i></i><i></i></span>
            <span><strong>Munis</strong><small>Business Hub</small></span>
          </a>

          <nav class="landing-nav" aria-label="Навигатсияи асосӣ">
            <a href="#features">Имкониятҳо</a>
            <a href="#workflow">Тарзи кор</a>
            <a href="#architecture">Технология</a>
            <a href="#security">Амният</a>
          </nav>

          <div class="landing-header-actions">
            <button class="landing-btn landing-btn-ghost" type="button" data-nav="/login">Ворид шудан</button>
            <button class="landing-btn landing-btn-primary" type="button" data-nav="/register">Оғози ройгон ${icon("chevronRight")}</button>
          </div>

          <details class="landing-mobile-menu">
            <summary aria-label="Кушодани меню">${icon("menu")}</summary>
            <div>
              <a href="#features">Имкониятҳо</a>
              <a href="#workflow">Тарзи кор</a>
              <a href="#architecture">Технология</a>
              <a href="#security">Амният</a>
              <button type="button" data-nav="/login">Ворид шудан</button>
              <button class="primary" type="button" data-nav="/register">Оғози ройгон</button>
            </div>
          </details>
        </div>
      </header>

      <main id="landing-main">
        <section class="landing-hero" id="top">
          <div class="landing-hero-orb landing-hero-orb-one" aria-hidden="true"></div>
          <div class="landing-hero-orb landing-hero-orb-two" aria-hidden="true"></div>
          <div class="landing-container landing-hero-grid">
            <div class="landing-hero-copy">
              <span class="landing-eyebrow light"><i></i> Маркази ягонаи муоширати бизнес</span>
              <h1>Telegram, WhatsApp ва Instagram — <em>дар як марказ.</em></h1>
              <p>Паёмҳо, муштариён, таърихи суҳбат ва фармоишҳоро аз як фазои кории равшан идора кунед.</p>
              <div class="landing-hero-actions">
                <button class="landing-btn landing-btn-primary landing-btn-large" type="button" data-nav="/register">Ройгон оғоз кунед ${icon("chevronRight")}</button>
                <a class="landing-btn landing-btn-dark-ghost landing-btn-large" href="#workflow">Бубинед, чӣ гуна кор мекунад</a>
              </div>
              <div class="landing-hero-proof" aria-label="Бартариҳои асосӣ">
                <span>${icon("checkCircle")} Насби зуд</span>
                <span>${icon("lock")} Маълумоти ҳифзшуда</span>
                <span>${icon("wifi")} Навсозии real-time</span>
                <span>${icon("search")} Ҷустуҷӯи зуд бо Ctrl K</span>
              </div>
            </div>

            <div class="landing-hero-visual">
              <div class="landing-platform-float telegram">${icon("send")}<span><strong>Telegram</strong><small>12 паёми нав</small></span></div>
              <div class="landing-platform-float whatsapp">${icon("messages")}<span><strong>WhatsApp</strong><small>8 паёми нав</small></span></div>
              <div class="landing-platform-float instagram">${icon("instagram")}<span><strong>Instagram</strong><small>5 паёми нав</small></span></div>
              ${dashboardPreview("hero-preview")}
              <div class="landing-response-float">${icon("clock")}<span><strong>38 сония</strong><small>вақти миёнаи ҷавоб</small></span></div>
            </div>
          </div>
          <div class="landing-container landing-trust-row">
            <span>Бо технологияҳои боэътимод:</span>
            <strong>Telegram MTProto</strong><i></i><strong>WhatsApp Cloud API</strong><i></i><strong>Instagram API</strong><i></i><strong>Django</strong>
          </div>
        </section>

        <section class="landing-section landing-problems" id="features">
          <div class="landing-container">
            <div class="landing-section-heading centered">
              <span class="landing-eyebrow"><i></i> Мушкилоти шинос</span>
              <h2>Вақте ҳар канал ҷудо аст,<br><em>бизнес имкониятро аз даст медиҳад.</em></h2>
              <p>Ҷустуҷӯи паём, гузаштан байни барномаҳо ва сабти дастии фармоишҳо вақти шуморо мегирад.</p>
            </div>

            <div class="landing-problem-grid">
              <article>
                <span class="landing-card-number">01</span>
                <div class="landing-problem-icon red">${icon("messages")}<i>${icon("alert")}</i></div>
                <h3>Паёмҳо парокандаанд</h3>
                <p>Telegram, WhatsApp ва Instagram дар ҷойҳои гуногунанд — тасвири пурраи муштарӣ нест.</p>
              </article>
              <article class="featured">
                <span class="landing-card-number">02</span>
                <div class="landing-problem-icon amber">${icon("clock")}<i>${icon("alert")}</i></div>
                <h3>Ҷавобҳо дер мешаванд</h3>
                <p>Паёми муҳим дар байни огоҳиномаҳо мемонад ва муштарӣ ба рақиб меравад.</p>
              </article>
              <article>
                <span class="landing-card-number">03</span>
                <div class="landing-problem-icon blue">${icon("orders")}<i>${icon("alert")}</i></div>
                <h3>Таърих гум мешавад</h3>
                <p>Суҳбат, тамос ва фармоиш ба ҳам пайваст нестанд; кор аз нав такрор мешавад.</p>
              </article>
            </div>

            <div class="landing-problem-note"><span>${icon("info")}</span><p><strong>Натиҷа:</strong> вақти бештар барои идоракунӣ, ҷавоби сусттар ва назорати камтар.</p></div>
          </div>
        </section>

        <section class="landing-section landing-ecosystem">
          <div class="landing-container landing-split-heading">
            <div>
              <span class="landing-eyebrow light"><i></i> Ҳалли Munis</span>
              <h2>Як экосистема.<br><em>Як ҷараёни корӣ.</em></h2>
            </div>
            <p>Munis Business Hub каналҳои расмии шуморо ба як dashboard мепайвандад — бе иваз кардани тарзи муоширати муштариён.</p>
          </div>

          <div class="landing-container landing-ecosystem-map" aria-label="Telegram, WhatsApp ва Instagram ба Munis пайваст шуда, ба паёмҳо, тамосҳо ва фармоишҳо роҳ медиҳанд">
            <div class="landing-map-column sources">
              <article class="telegram"><span>${icon("send")}</span><div><strong>Telegram</strong><small>Аккаунти бизнес</small></div><i>${icon("chevronRight")}</i></article>
              <article class="whatsapp"><span>${icon("messages")}</span><div><strong>WhatsApp</strong><small>Business Cloud API</small></div><i>${icon("chevronRight")}</i></article>
              <article class="instagram"><span>${icon("instagram")}</span><div><strong>Instagram</strong><small>Business OAuth</small></div><i>${icon("chevronRight")}</i></article>
            </div>
            <div class="landing-map-hub">
              <span class="landing-map-hub-logo">M</span>
              <strong>MUNIS</strong>
              <small>Business Hub</small>
              <i class="pulse one"></i><i class="pulse two"></i>
            </div>
            <div class="landing-map-column outputs">
              <article><span>${icon("messages")}</span><div><strong>Паёмҳо</strong><small>Як inbox</small></div></article>
              <article><span>${icon("contacts")}</span><div><strong>Тамосҳо</strong><small>Таърихи пурра</small></div></article>
              <article><span>${icon("orders")}</span><div><strong>Фармоишҳо</strong><small>Назорат дар як ҷой</small></div></article>
            </div>
          </div>

          <div class="landing-container landing-benefit-strip">
            <span>${icon("checkCircle")} Ҳамаи суҳбатҳо дар як ҷо</span>
            <span>${icon("checkCircle")} Ҷавоби зудтар</span>
            <span>${icon("checkCircle")} Таърихи ягонаи муштарӣ</span>
            <span>${icon("checkCircle")} Назорати real-time</span>
          </div>
        </section>

        <section class="landing-section landing-workflow" id="workflow">
          <div class="landing-container">
            <div class="landing-section-heading">
              <span class="landing-eyebrow"><i></i> Пайвасти расмӣ</span>
              <h2>Аз паёми нав то dashboard — <em>бе қадамҳои зиёдатӣ.</em></h2>
              <p>Ҳар воқеа санҷида, дар навбат коркард ва бехатар нигоҳ дошта мешавад.</p>
            </div>

            <article class="landing-flow-panel telegram-flow">
              <header>
                <span class="landing-flow-logo telegram">${icon("send")}</span>
                <div><span>Ҷараёни Telegram</span><h3>Telegram API / MTProto</h3></div>
                <small>${icon("checkCircle")} Аккаунти шахсии худи бизнес</small>
              </header>
              <ol class="landing-flow-list">
                ${flowStep(1, "phone", "Аккаунт", "Рақами бизнес", "telegram")}
                ${flowStep(2, "send", "MTProto", "Пайвасти расмӣ", "telegram")}
                ${flowStep(3, "integrations", "Munis API", "Қабули воқеа", "violet")}
                ${flowStep(4, "refresh", "Celery + Redis", "Коркарди заминавӣ", "amber")}
                ${flowStep(5, "orders", "PostgreSQL", "Нигоҳдории маълумот", "blue")}
                ${flowStep(6, "dashboard", "Dashboard", "Намоиши real-time", "violet")}
              </ol>
            </article>

            <article class="landing-flow-panel whatsapp-flow">
              <header>
                <span class="landing-flow-logo whatsapp">${icon("messages")}</span>
                <div><span>Ҷараёни WhatsApp</span><h3>WhatsApp Business Cloud API</h3></div>
                <small>${icon("checkCircle")} Webhook-и тасдиқшудаи Meta</small>
              </header>
              <ol class="landing-flow-list">
                ${flowStep(1, "user", "Муштарӣ", "Паём мефиристад", "cyan")}
                ${flowStep(2, "phone", "WhatsApp", "Business Account", "whatsapp")}
                ${flowStep(3, "wifi", "Cloud API", "Канали расмӣ", "violet")}
                ${flowStep(4, "messages", "Webhook", "Тасдиқ ва қабул", "orange")}
                ${flowStep(5, "integrations", "Munis", "Коркард ва сабт", "blue")}
                ${flowStep(6, "dashboard", "Dashboard", "Огоҳии фаврӣ", "violet")}
              </ol>
            </article>
          </div>
        </section>

        <section class="landing-section landing-dashboard-section">
          <div class="landing-container landing-split-heading dashboard-heading">
            <div>
              <span class="landing-eyebrow"><i></i> Dashboard-и зинда</span>
              <h2>Тамоми бизнес — <em>дар як нигоҳ.</em></h2>
            </div>
            <p>Паёми нав, суҳбати фаъол ва фармоиш фавран намоён мешавад. Барои гирифтани тасвири пурра дигар байни барномаҳо нагузаред.</p>
          </div>
          <div class="landing-container landing-full-dashboard-wrap">
            <div class="landing-dashboard-glow" aria-hidden="true"></div>
            ${dashboardPreview("full-preview")}
            <div class="landing-preview-callout callout-one">${icon("wifi")}<span><strong>Real-time</strong><small>Бе refresh</small></span></div>
            <div class="landing-preview-callout callout-two">${icon("checkCircle")}<span><strong>Як профил</strong><small>Тамос + таърих</small></span></div>
          </div>
        </section>

        <section class="landing-section landing-architecture" id="architecture">
          <div class="landing-container landing-architecture-grid">
            <div class="landing-architecture-copy">
              <span class="landing-eyebrow light"><i></i> Архитектураи устувор</span>
              <h2>Барои кори воқеии бизнес <em>омода сохта шудааст.</em></h2>
              <p>Қабатҳои равшан, коркарди заминавӣ ва навсозии фаврӣ имкон медиҳанд, ки система бо афзоиши паёмҳо устувор монад.</p>
              <ul>
                <li>${icon("checkCircle")} API-и сохторёфта ва иҷозатҳои дақиқ</li>
                <li>${icon("checkCircle")} Queue, cache ва вазифаҳои asynchronous</li>
                <li>${icon("checkCircle")} Маълумоти доимӣ ва навсозии WebSocket</li>
              </ul>
              <span class="landing-tech-stack"><b>Django</b><b>PostgreSQL</b><b>Redis</b><b>Celery</b><b>WebSocket</b></span>
            </div>

            <div class="landing-layer-stack" aria-label="Қабатҳои техникии система">
              <article class="frontend"><span>${icon("dashboard")}</span><div><strong>Frontend</strong><small>Dashboard + REST + WebSocket</small></div><b>01</b></article>
              <i>${icon("chevronDown")}</i>
              <article class="api"><span>${icon("integrations")}</span><div><strong>Django REST Framework</strong><small>API + Authentication + Permissions</small></div><b>02</b></article>
              <i>${icon("chevronDown")}</i>
              <article class="queue"><span>${icon("refresh")}</span><div><strong>Celery + Redis</strong><small>Async jobs + Queue + Cache</small></div><b>03</b></article>
              <i>${icon("chevronDown")}</i>
              <article class="database"><span>${icon("orders")}</span><div><strong>PostgreSQL</strong><small>Маълумоти доимии бизнес</small></div><b>04</b></article>
              <i>${icon("chevronDown")}</i>
              <article class="channels"><span>${icon("send")}</span><div><strong>Пайвастҳо</strong><small>Telegram + WhatsApp + Instagram APIs</small></div><b>05</b></article>
              <footer>${icon("lock")} Docker · Nginx · HTTPS · Monitoring</footer>
            </div>
          </div>
        </section>

        <section class="landing-section landing-security" id="security">
          <div class="landing-container">
            <div class="landing-section-heading centered">
              <span class="landing-eyebrow"><i></i> Амният дар ҳар қабат</span>
              <h2>Маълумоти бизнес — <em>танҳо барои шумо.</em></h2>
              <p>Аз воридшавӣ то webhook ва нигоҳдории session, ҳар қадам бо назорати дақиқ ҳифз мешавад.</p>
            </div>

            <div class="landing-security-grid">
              ${securityCard("lock", "JWT Authentication", "Сессия ва дастрасӣ бо token-ҳои кӯтоҳмуддат идора мешаванд.")}
              ${securityCard("user", "Object permissions", "Ҳар корбар танҳо маълумоти аккаунти худашро мебинад.")}
              ${securityCard("eyeOff", "Encryption", "Telegram session ва credential-ҳо рамзгузорӣ нигоҳ дошта мешаванд.")}
              ${securityCard("checkCircle", "Webhook verification", "Имзои рӯйдодҳои WhatsApp пеш аз коркард санҷида мешавад.")}
              ${securityCard("copy", "Idempotency", "Webhook-и такрорӣ паём ё фармоиши duplicate намесозад.")}
              ${securityCard("refresh", "Background processing", "Celery корҳои вазнинро аз дархости асосӣ ҷудо мекунад.")}
            </div>

            <div class="landing-secret-note">
              <span>${icon("lock")}</span>
              <p><strong>Қоидаи асосӣ:</strong> secret, access token ва session ҳеҷ гоҳ ба frontend, Git ё log дода намешаванд.</p>
              <i>${icon("checkCircle")} Ҳифзшуда</i>
            </div>
          </div>
        </section>

        <section class="landing-section landing-vision">
          <div class="landing-container">
            <div class="landing-section-heading centered">
              <span class="landing-eyebrow"><i></i> Натиҷаи ниҳоӣ</span>
              <h2>Аз парокандагӣ — <em>ба як низоми равшан.</em></h2>
            </div>

            <div class="landing-vision-grid">
              <article class="before">
                <header><span>Пеш аз Munis</span><b>Пароканда</b></header>
                <ul>
                  <li><span>${icon("close")}</span><div><strong>Telegram — ҷудо</strong><small>Паёмҳо дар як барнома</small></div></li>
                  <li><span>${icon("close")}</span><div><strong>WhatsApp — ҷудо</strong><small>Огоҳиномаҳо дар телефони дигар</small></div></li>
                  <li><span>${icon("close")}</span><div><strong>Фармоиш бе таърих</strong><small>Маълумот дастӣ ва нопурра</small></div></li>
                </ul>
              </article>

              <span class="landing-vision-arrow">${icon("chevronRight")}<small>Munis</small></span>

              <article class="after">
                <header><span>Бо Munis</span><b>Якҷо</b></header>
                <ul>
                  <li><span>${icon("check")}</span><div><strong>Telegram + WhatsApp + Instagram</strong><small>Ҳамаи каналҳо дар як inbox</small></div></li>
                  <li><span>${icon("check")}</span><div><strong>Паём + тамос + таърих</strong><small>Профили ягонаи муштарӣ</small></div></li>
                  <li><span>${icon("check")}</span><div><strong>Фармоиш + dashboard</strong><small>Назорати фаврӣ ва равшан</small></div></li>
                </ul>
              </article>
            </div>
          </div>
        </section>

        <section class="landing-final-cta">
          <div class="landing-final-orb one" aria-hidden="true"></div><div class="landing-final-orb two" aria-hidden="true"></div>
          <div class="landing-container landing-final-inner">
            <span class="landing-eyebrow light"><i></i> Қадами аввал</span>
            <h2>Муоширати бизнесатонро<br><em>имрӯз якҷо кунед.</em></h2>
            <p>Telegram, WhatsApp ва Instagram-ро пайваст кунед ва ҳар паёмро аз як фазои корӣ идора намоед.</p>
            <div>
              <button class="landing-btn landing-btn-primary landing-btn-large" type="button" data-nav="/register">Сабти номи ройгон ${icon("chevronRight")}</button>
              <button class="landing-btn landing-btn-dark-ghost landing-btn-large" type="button" data-nav="/login">Ман аккаунт дорам</button>
            </div>
            <small>${icon("checkCircle")} Барои оғоз корти бонкӣ лозим нест</small>
          </div>
        </section>
      </main>

      <footer class="landing-footer">
        <div class="landing-container">
          <a class="landing-brand" href="#top">
            <span class="landing-brand-mark" aria-hidden="true"><i></i><i></i></span>
            <span><strong>Munis</strong><small>Business Hub</small></span>
          </a>
          <p>Маркази ягона барои муоширати Telegram, WhatsApp ва Instagram.</p>
          <nav aria-label="Пайвандҳои поёнӣ"><a href="#features">Имкониятҳо</a><a href="#architecture">Технология</a><a href="#security">Амният</a></nav>
          <small>© 2026 Munis Business Hub</small>
        </div>
      </footer>
    </div>`;

  mount.querySelectorAll(".landing-mobile-menu a").forEach((link) => {
    link.addEventListener("click", () => link.closest("details")?.removeAttribute("open"));
  });
}
