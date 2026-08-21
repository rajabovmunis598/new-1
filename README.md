# Munis Business Hub backend

Production-oriented Django REST backend for Telegram MTProto and WhatsApp Cloud API messaging.

## Local development

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

API documentation is available at `/api/docs/`; WebSocket clients connect to `/ws/dashboard/`.

## Docker

Set production secrets in `.env`, then run `docker compose up --build`. Services include PostgreSQL, Redis, ASGI web, Celery worker, Celery Beat and Nginx.

Telegram connection requires `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`. WhatsApp webhook must point to `/api/webhooks/whatsapp/`; Meta signature validation uses `WHATSAPP_APP_SECRET`.

## Tests

```powershell
.\.venv\Scripts\python manage.py test tests
```
