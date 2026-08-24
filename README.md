# Munis Business Hub

Production-oriented business communications hub with a complete responsive frontend, Django REST API, Telegram MTProto, WhatsApp Cloud API and Instagram Messaging integrations.

The frontend is a dependency-free native JavaScript SPA served by Django. It includes a public product page, authentication, dashboard, unified inbox, contacts, orders, integrations, notifications and account settings. No Node build step is required.

## Local development

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

`runserver` starts the Telegram listener automatically, so one command runs both
the website and incoming Telegram delivery. To run Uvicorn directly instead,
start the listener in a second terminal:

```powershell
.\.venv\Scripts\python manage.py run_telegram_listener
```

Use `manage.py runserver --no-telegram-listener` only when a standalone listener
is already running. The listener starts one isolated MTProto client for every
active Telegram integration. The Inbox refreshes automatically and replies are
delivered to Telegram before the API reports them as sent.

Open `http://127.0.0.1:8000/`. Create an account from the public landing page, then use the protected workspace at `/dashboard`.

Main routes:

- `/` - product landing page
- `/login` and `/register` - authentication
- `/dashboard` - business overview
- `/messages` - unified Telegram, WhatsApp and Instagram inbox
- `/contacts` - customer profiles and history
- `/orders` - order management
- `/integrations` - Telegram, WhatsApp and Instagram connection flows
- `/settings` - profile, appearance, notification and security preferences

API documentation is available at `/api/docs/`; authenticated WebSocket clients connect to `/ws/dashboard/?token=<access-token>`. Development uses the in-memory channel layer by default. Production (`DEBUG=False`) uses Redis.

## Docker

Set production secrets in `.env`, then run `docker compose up --build`. Services include PostgreSQL, Redis, ASGI web, Celery worker, Celery Beat, the Telegram listener and Nginx.

Each user enters their own Telegram API ID/API Hash or WhatsApp Cloud API credentials on the Integrations page. Instagram accounts connect through the server's Meta OAuth application. Per-user secrets and Instagram access tokens are encrypted per integration and are never returned by the API. Each WhatsApp integration receives its own callback URL, while Instagram uses the global signed webhook at `/api/webhooks/instagram/`.

To enable Instagram, configure `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`,
`INSTAGRAM_VERIFY_TOKEN`, and the exact HTTPS callback URL in
`INSTAGRAM_REDIRECT_URI`. Register that same callback and
`/api/webhooks/instagram/` in the Meta application. OAuth state is signed,
short-lived, and single use. In local `DEBUG` mode only, an unset redirect URI
falls back to Django's absolute callback URL.

Instagram Messaging supports professional Business or Creator accounts, not
personal accounts. Before opening the site to arbitrary customers, obtain the
required Meta Advanced Access and complete App Review for the requested scopes.
Instagram's messaging rules also require the customer to message the connected
professional account first; this integration does not start unsolicited chats.

For production, set a stable `INTEGRATION_ENCRYPTION_KEY`, use Redis for `CACHE_URL`, and terminate HTTPS before Django. Changing the encryption key makes existing integration credentials unreadable.

## SMTP email

Set the `EMAIL_*` values in `core/settings.py` or provide the corresponding environment variables from `.env.example`. Gmail uses port `587` with TLS and an app password (enter the app password without spaces). Never commit a real SMTP password.

After configuring SMTP, send a real test message with:

```powershell
.\.venv\Scripts\python manage.py send_test_email recipient@example.com
```

The command reports the SMTP error without changing application data. The project does not send registration, password-reset, or notification email automatically until one of those workflows is explicitly enabled.

## Tests

```powershell
.\.venv\Scripts\python manage.py test
node --check frontend\static\frontend\js\app.js
```
