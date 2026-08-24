# ТЗ — Munis Business Hub

## 1. Мақсад

Сохтани backend-и production-ready бо Django REST Framework барои пайваст кардани:

- Telegram аккаунти оддии бизнесӣ тавассути Telegram API / MTProto
- WhatsApp Business тавассути WhatsApp Cloud API

Паёмҳо аз платформаҳо қабул шуда, дар PostgreSQL нигоҳ дошта шаванд ва дар dashboard real-time нишон дода шаванд.

> Telegram Bot API қисми асосии ин лоиҳа нест. Барои Telegram аккаунти оддии бизнесӣ Telegram API / MTProto истифода шавад.

---

## 2. Технологияҳо

### Backend
- Python 3.12+
- Django 5.2+
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Celery Beat
- Django Channels
- WebSocket
- JWT / SimpleJWT
- drf-spectacular
- django-filter
- Gunicorn
- Uvicorn / ASGI

### Telegram
- Telegram API
- MTProto
- Telethon ё Pyrogram
- api_id
- api_hash
- Telegram account authorization
- encrypted Telegram session

### WhatsApp
- WhatsApp Business Platform
- WhatsApp Cloud API
- Meta Developer App
- WhatsApp Business Account
- Access Token
- Phone Number ID
- Business Account ID
- Webhook
- Verify Token
- App Secret

### Infrastructure
- Docker
- Docker Compose
- Nginx

---

## 3. Архитектура

```text
Frontend
   |
REST API / WebSocket
   |
Django REST Framework
   |
+-----------------------------+
| PostgreSQL | Redis | Celery |
+-----------------------------+
   |
Integration Layer
   |
+-------------------+-------------------+
|                                       |
Telegram MTProto                    WhatsApp Cloud API
|                                       |
Telegram Account                    WhatsApp Business
```

---

## 4. Django Apps

```text
config/
users/
integrations/
contacts/
conversations/
messages/
orders/
notifications/
audit/
```

---

## 5. User Model

Custom User:

```text
id
username
email
password
first_name
last_name
is_active
is_staff
created_at
updated_at
```

---

## 6. Integration Model

```text
Integration

id
user
platform
name
status
external_account_id
credentials
session_data
webhook_url
created_at
updated_at
last_sync_at
last_error
```

### platform

```text
telegram
whatsapp
```

### status

```text
pending
active
inactive
error
```

`credentials` ва `session_data` encrypted нигоҳ дошта шаванд.

---

# 7. Telegram Integration — MTProto

## 7.1 Талабот

Telegram Bot API истифода нашавад.

Система бояд Telegram аккаунти оддии бизнесиро пайваст карда тавонад.

```text
Business Phone Number
        |
Telegram Account
        |
Telegram API / MTProto
        |
Python Telegram Client
        |
Django Integration Service
```

## 7.2 Credentials

Ҳар user `Telegram API ID` ва `API Hash`-и худро дар формаи пайвастшавӣ ворид мекунад. Онҳо encrypted дар `Integration.credentials` нигоҳ дошта мешаванд.

`api_hash` ба frontend ё API response баргардонида нашавад.

## 7.3 Authentication

Endpoints:

```text
POST /api/integrations/telegram/connect/start/
POST /api/integrations/telegram/connect/verify/
POST /api/integrations/telegram/connect/2fa/
POST /api/integrations/telegram/disconnect/
GET  /api/integrations/telegram/status/
```

Flow:

1. API ID, API Hash ва phone number қабул мешаванд.
2. Telegram client сохта мешавад.
3. Verification code request мешавад.
4. Code verify мешавад.
5. Агар 2FA бошад, password талаб мешавад.
6. Session сохта мешавад.
7. Session encrypted нигоҳ дошта мешавад.
8. Integration active мешавад.

## 7.4 Telegram Session

Session:

- дар frontend нигоҳ дошта нашавад;
- plain-text дар database нигоҳ дошта нашавад;
- encrypted нигоҳ дошта шавад;
- дар logs нишон дода нашавад;
- ба user-и дигар дастрас набошад.

## 7.5 Telegram Messages

Incoming:

```text
Telegram
   |
MTProto Event
   |
Telegram Service
   |
Celery
   |
PostgreSQL
   |
WebSocket
   |
Dashboard
```

Outgoing event-ҳо низ сабт карда шаванд.

---

# 8. WhatsApp Integration

WhatsApp Business Platform / Cloud API истифода шавад.

## 8.1 Талабот

- Meta Developer App
- Meta Business Account
- WhatsApp Business Account
- Business Phone Number
- Phone Number ID
- Business Account ID
- Access Token
- Verify Token
- App Secret
- Webhook

Development/test mode бояд дастгирӣ шавад.

## 8.2 Credentials

Ҳар user маълумоти WhatsApp Cloud API-и худро дар форма ворид мекунад. Access Token, Verify Token ва App Secret encrypted нигоҳ дошта мешаванд. Дар environment танҳо `WHATSAPP_API_VERSION` глобалӣ аст.

## 8.3 Webhook

```text
GET  /api/webhooks/whatsapp/{integration_id}/
POST /api/webhooks/whatsapp/{integration_id}/
```

Flow:

```text
Customer
   |
WhatsApp Business
   |
WhatsApp Cloud API
   |
Webhook
   |
Django DRF
   |
IntegrationEvent
   |
Celery
   |
PostgreSQL
   |
WebSocket
   |
Dashboard
```

Webhook verification/signature санҷида шавад.

---

# 9. Contact Model

```text
Contact

id
integration
external_id
name
username
phone
avatar_url
metadata
created_at
updated_at
```

Constraint:

```text
integration + external_id = unique
```

---

# 10. Conversation Model

```text
Conversation

id
integration
contact
external_chat_id
title
status
last_message_at
created_at
updated_at
```

Status:

```text
open
closed
archived
```

Constraint:

```text
integration + external_chat_id = unique
```

---

# 11. Message Model

```text
Message

id
conversation
external_message_id
sender_type
message_type
text
media_url
reply_to
external_created_at
created_at
updated_at
metadata
```

### sender_type

```text
customer
business
system
```

### message_type

```text
text
image
video
audio
document
location
sticker
other
```

Constraint:

```text
conversation + external_message_id = unique
```

---

# 12. IntegrationEvent Model

```text
IntegrationEvent

id
integration
event_type
external_event_id
status
payload
error_message
created_at
processed_at
```

Status:

```text
received
processing
processed
failed
```

Барои idempotency ва retry истифода шавад.

---

# 13. Order Model

```text
Order

id
user
contact
conversation
external_id
description
amount
currency
status
created_at
updated_at
completed_at
```

Status:

```text
new
processing
completed
cancelled
```

## OrderItem

```text
OrderItem

id
order
name
quantity
price
total
metadata
```

---

# 14. Notification Model

```text
Notification

id
user
type
title
message
is_read
created_at
```

Types:

```text
new_message
message_failed
new_order
integration_error
system
```

---

# 15. Redis

Redis ҳатман истифода шавад барои:

- Celery Broker
- Celery Result Backend
- Cache
- Rate Limiting
- Django Channels
- Temporary Data
- Distributed Locks

---

# 16. Celery

Celery ҳатман истифода шавад.

Tasks:

```text
process_telegram_event
process_whatsapp_event
sync_telegram_messages
send_whatsapp_message
process_outgoing_message
create_notification
retry_failed_event
cleanup_old_events
sync_contacts
generate_statistics
```

Webhook корҳои вазнинро мустақиман иҷро накунад.

---

# 17. Celery Beat

Scheduled tasks:

```text
Every 5 minutes:
    check integrations

Every hour:
    check failed events

Every day:
    cleanup old events

Every day:
    generate statistics
```

---

# 18. WebSocket

Django Channels + Redis Channel Layer истифода шавад.

Вақте message-и нав меояд, dashboard бе refresh нав шавад.

```text
Platform
   |
Integration
   |
Celery
   |
Database
   |
WebSocket
   |
Dashboard
```

---

# 19. Authentication

JWT:

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/token/refresh/
POST /api/auth/logout/
GET  /api/auth/me/
```

---

# 20. Permissions

User танҳо маълумоти худро бинад.

Истифода:

```text
IsAuthenticated
IsOwner
```

Ҳама queryset-ҳо object-level authorization дошта бошанд.

---

# 21. Integration API

```text
GET    /api/integrations/
GET    /api/integrations/{id}/

POST   /api/integrations/telegram/connect/start/
POST   /api/integrations/telegram/connect/verify/
POST   /api/integrations/telegram/connect/2fa/
POST   /api/integrations/telegram/disconnect/

POST   /api/integrations/whatsapp/connect/
POST   /api/integrations/whatsapp/disconnect/
POST   /api/integrations/whatsapp/test/

PATCH  /api/integrations/{id}/
DELETE /api/integrations/{id}/
```

---

# 22. Conversation API

```text
GET   /api/conversations/
GET   /api/conversations/{id}/
PATCH /api/conversations/{id}/

POST /api/conversations/{id}/close/
POST /api/conversations/{id}/archive/
```

Filters:

```text
platform
status
contact
date_from
date_to
```

---

# 23. Message API

```text
GET  /api/messages/
GET  /api/messages/{id}/
POST /api/conversations/{id}/messages/
```

Filters:

```text
platform
sender_type
message_type
date_from
date_to
```

Search:

```text
message text
contact
username
phone
```

---

# 24. External URL

Агар platform deep-link дастгирӣ кунад:

```text
GET /api/messages/{id}/external-url/
```

Response:

```json
{
  "url": "https://..."
}
```

Агар дастгирӣ нашавад:

```json
{
  "url": null
}
```

---

# 25. Dashboard Statistics

```text
GET /api/dashboard/statistics/
```

Натиҷа:

```json
{
  "total_messages": 0,
  "unread_messages": 0,
  "telegram_messages": 0,
  "whatsapp_messages": 0,
  "total_conversations": 0,
  "open_conversations": 0,
  "total_orders": 0,
  "new_orders": 0,
  "completed_orders": 0
}
```

Django ORM:

```text
Count
Sum
Avg
annotate
```

---

# 26. Filtering

`django-filter` истифода шавад.

```python
filter_backends = [
    DjangoFilterBackend,
    SearchFilter,
    OrderingFilter,
]
```

---

# 27. Pagination

Default:

```text
20
```

Maximum:

```text
100
```

Example:

```text
?page=1&page_size=20
```

---

# 28. Database Optimization

Истифода шавад:

```python
select_related()
prefetch_related()
annotate()
Count()
Sum()
Avg()
```

Indexes барои:

```text
external_id
external_message_id
external_chat_id
created_at
status
platform
```

---

# 29. Idempotency

Webhook/event метавонад якчанд маротиба фиристода шавад.

Duplicate набояд сохта шавад.

Unique constraints:

```text
integration + external_message_id
integration + external_event_id
```

---

# 30. Security

Ҳатман:

- HTTPS
- DEBUG=False дар production
- SECRET_KEY дар `.env`
- CORS дуруст
- JWT security
- rate limiting
- object-level permissions
- webhook verification
- encrypted credentials
- encrypted Telegram sessions
- secret-ҳоро дар logs нишон надодан
- `.env` дар `.gitignore`

Telegram `api_hash`, session ва WhatsApp access token ҳеҷ гоҳ ба frontend дода нашаванд.

---

# 31. Environment Variables

```env
DEBUG=False
SECRET_KEY=...

DATABASE_URL=postgresql://...

REDIS_URL=redis://redis:6379/0
CACHE_URL=redis://redis:6379/3

CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

JWT_ACCESS_LIFETIME=...
JWT_REFRESH_LIFETIME=...

WHATSAPP_API_VERSION=...
INTEGRATION_ENCRYPTION_KEY=...
```

---

# 32. Docker

Services:

```text
web
db
redis
celery
celery-beat
nginx
```

---

# 33. Project Structure

```text
project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── users/
├── integrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   ├── tasks.py
│   └── services/
│       ├── base.py
│       ├── telegram_mtproto.py
│       └── whatsapp_cloud.py
│
├── contacts/
├── conversations/
├── messages/
├── orders/
├── notifications/
├── audit/
├── tests/
├── nginx/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── manage.py
└── README.md
```

---

# 34. Integration Adapter

```python
class BaseIntegration:
    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def send_message(self, conversation, text):
        raise NotImplementedError

    def process_event(self, payload):
        raise NotImplementedError

    def get_external_url(self, message):
        raise NotImplementedError
```

Telegram:

```python
class TelegramMTProtoIntegration(BaseIntegration):
    ...
```

WhatsApp:

```python
class WhatsAppCloudIntegration(BaseIntegration):
    ...
```

---

# 35. Telegram Message Flow

```text
Telegram Account
      |
MTProto Event
      |
TelegramMTProtoIntegration
      |
IntegrationEvent
      |
Redis
      |
Celery
      |
+-----+-----+-----+
|           |     |
Contact  Conversation Message
                  |
             Notification
                  |
              WebSocket
                  |
              Dashboard
```

---

# 36. WhatsApp Message Flow

```text
Customer
      |
WhatsApp Business
      |
WhatsApp Cloud API
      |
Webhook
      |
DRF
      |
IntegrationEvent
      |
Redis
      |
Celery
      |
+-----+-----+-----+
|           |     |
Contact  Conversation Message
                  |
             Notification
                  |
              WebSocket
                  |
              Dashboard
```

---

# 37. API Documentation

`drf-spectacular` истифода шавад.

```text
/api/schema/
/api/docs/
/api/redoc/
```

---

# 38. Testing

Test-ҳо ҳатман навишта шаванд.

### Authentication
- Register
- Login
- Refresh
- Permissions

### Telegram
- API configuration
- Authentication flow
- Code verification
- 2FA
- Session encryption
- Incoming message
- Outgoing message event
- Duplicate message
- Disconnect

### WhatsApp
- Webhook verification
- Webhook signature
- Incoming message
- Outgoing message
- Duplicate event
- Failed API request

### General
- Contacts
- Conversations
- Messages
- Orders
- Notifications
- Filters
- Pagination
- WebSocket
- Celery
- Permissions

---

# 39. Production

```text
Internet
   |
Nginx
   |
Django ASGI
   |
+-------------------------+
| PostgreSQL | Redis      |
|            |            |
|            | Celery     |
+-------------------------+
```

---

# 40. Development Order

```text
1. Django project
2. Custom User
3. PostgreSQL
4. JWT
5. Integration architecture
6. Contact
7. Conversation
8. Message
9. Order
10. Telegram MTProto authentication
11. Telegram message listener
12. Telegram session encryption
13. WhatsApp Cloud API configuration
14. WhatsApp webhook
15. Redis
16. Celery
17. Celery Beat
18. Django Channels
19. WebSocket
20. Notifications
21. Search/filter
22. Statistics
23. Swagger
24. Tests
25. Docker
26. Nginx
27. Production configuration
```

---

# 41. MVP

### Authentication
- Register
- Login
- JWT
- Refresh
- Logout
- Profile

### Telegram
- Connect Telegram account
- Phone verification
- 2FA support
- MTProto session
- Receive messages
- Receive outgoing message events
- Save messages
- Conversations
- Contacts
- Disconnect

### WhatsApp
- Connect WhatsApp Business
- Cloud API configuration
- Webhook
- Receive messages
- Send messages where API policy permits
- Message status
- Contacts
- Conversations
- Disconnect

### Dashboard
- Telegram messages
- WhatsApp messages
- Conversations
- Search
- Filters
- Pagination
- Unread messages
- Notifications
- Real-time updates

### Infrastructure
- PostgreSQL
- Redis
- Celery
- Celery Beat
- Django Channels
- Docker
- Nginx

---

# 42. Acceptance Criteria

Project тайёр ҳисобида мешавад, вақте:

1. User метавонад register/login кунад.
2. JWT кор мекунад.
3. User танҳо data-и худро мебинад.
4. Telegram аккаунти оддӣ бо MTProto connect мешавад.
5. Telegram session encrypted нигоҳ дошта мешавад.
6. Telegram incoming message дар database сабт мешавад.
7. Telegram outgoing message event сабт мешавад.
8. WhatsApp Business Cloud API connect мешавад.
9. WhatsApp webhook verify мешавад.
10. WhatsApp incoming message дар database сабт мешавад.
11. WhatsApp outgoing message API flow мувофиқи имконият ва қоидаҳои API кор мекунад.
12. Duplicate events message-и duplicate намесозанд.
13. Celery background processing кор мекунад.
14. Redis кор мекунад.
15. Celery Beat кор мекунад.
16. WebSocket real-time update медиҳад.
17. Dashboard unread messages нишон медиҳад.
18. Search/filter кор мекунад.
19. Orders кор мекунанд.
20. Swagger documentation мавҷуд аст.
21. Tests навишта шудаанд.
22. Docker Compose service-ҳоро оғоз мекунад.
23. Production configuration омода аст.

---

# 43. Қоидаҳои муҳим

Система танҳо аккаунтҳо ва credential-ҳои худи соҳиби онро истифода барад.

### Telegram
- Telegram API / MTProto истифода шавад.
- Session-и шахси дигар истифода нашавад.
- Authentication bypass нашавад.
- Spam automation ва давр задани лимитҳо сохта нашавад.

### WhatsApp
- WhatsApp Business Platform / Cloud API истифода шавад.
- WhatsApp Web scraping истифода нашавад.
- Unofficial client истифода нашавад.
- Session hijacking ва verification bypass нашавад.
- Қоидаҳои Meta риоя шаванд.

---

# 44. Натиҷаи ниҳоӣ

```text
                 MUNIS BUSINESS HUB
                        |
          +-------------+-------------+
          |                           |
          v                           v
 Telegram Account              WhatsApp Business
    MTProto                    WhatsApp Cloud API
          |                           |
          +-------------+-------------+
                        |
                    Django DRF
                        |
               +--------+--------+
               |                 |
             Redis            Celery
               |                 |
               +--------+--------+
                        |
                   PostgreSQL
                        |
                    WebSocket
                        |
                    Dashboard
```

Ҳадаф: communication-и иҷозатдодашудаи бизнес аз Telegram ва WhatsApp дар як dashboard ҷамъ карда шавад, дар ҳоле ки Telegram ва WhatsApp ҳамчун platform-и асосии communication боқӣ мемонанд.
