import os
from django.core.cache import cache
from rest_framework.exceptions import ValidationError
from .base import BaseIntegration

class TelegramMTProtoIntegration(BaseIntegration):
    def _client(self, session=""):
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise ValidationError("Telethon is not installed") from exc
        api_id, api_hash = os.getenv("TELEGRAM_API_ID"), os.getenv("TELEGRAM_API_HASH")
        if not api_id or not api_hash: raise ValidationError("Telegram API is not configured")
        return TelegramClient(StringSession(session), int(api_id), api_hash)
    async def start(self, phone):
        client = self._client(); await client.connect(); result = await client.send_code_request(phone)
        cache.set(f"tg_auth:{self.integration.pk}", {"phone": phone, "hash": result.phone_code_hash, "session": client.session.save()}, 600)
        await client.disconnect()
    async def verify(self, code):
        data = cache.get(f"tg_auth:{self.integration.pk}")
        if not data: raise ValidationError("Authentication session expired")
        client = self._client(data["session"]); await client.connect()
        try: await client.sign_in(data["phone"], code, phone_code_hash=data["hash"])
        except Exception as exc:
            if exc.__class__.__name__ == "SessionPasswordNeededError": return {"requires_2fa": True}
            raise ValidationError("Invalid verification code") from exc
        await self._activate(client); return {"requires_2fa": False}
    async def verify_2fa(self, password):
        data = cache.get(f"tg_auth:{self.integration.pk}")
        if not data: raise ValidationError("Authentication session expired")
        client = self._client(data["session"]); await client.connect(); await client.sign_in(password=password); await self._activate(client)
    async def _activate(self, client):
        me = await client.get_me(); self.integration.set_session(client.session.save()); self.integration.external_account_id = str(me.id); self.integration.status = "active"; self.integration.save(); cache.delete(f"tg_auth:{self.integration.pk}"); await client.disconnect()
    def send_message(self, conversation, text):
        # Network delivery is delegated to Celery in production; local row preserves outgoing intent.
        return self.save_outgoing(conversation, text, metadata={"delivery_status": "queued"})
    def process_event(self, payload):
        from integrations.processing import persist_incoming
        return persist_incoming(self.integration, payload)
    def get_external_url(self, message):
        username = message.conversation.contact.username
        return f"https://t.me/{username}/{message.external_message_id}" if username else None
