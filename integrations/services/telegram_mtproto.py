import asyncio

from django.core.cache import cache
from rest_framework.exceptions import APIException, ValidationError

from integrations.security import decrypt_json, encrypt_json

from .base import BaseIntegration


class TelegramMTProtoIntegration(BaseIntegration):
    def _client(self, session=""):
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise ValidationError("Telethon дар сервер насб нашудааст") from exc

        credentials = self.integration.get_credentials()
        api_id = credentials.get("api_id")
        api_hash = credentials.get("api_hash")
        if not api_id or not api_hash:
            raise ValidationError("API ID ва API Hash-и ҳамин пайваст дастрас нестанд.")
        try:
            api_id = int(api_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Telegram API ID бояд рақам бошад") from exc

        return TelegramClient(StringSession(session), api_id, api_hash)

    @property
    def _auth_cache_key(self):
        return f"tg_auth:{self.integration.pk}"

    async def _save_auth(self, value):
        await cache.aset(self._auth_cache_key, encrypt_json(value), 600)

    async def _load_auth(self):
        value = await cache.aget(self._auth_cache_key)
        if isinstance(value, str):
            value = decrypt_json(value)
        if not isinstance(value, dict):
            return {}
        required = ("phone", "hash", "session")
        return value if all(value.get(key) for key in required) else {}

    @staticmethod
    async def _disconnect_client(client):
        try:
            await client.disconnect()
        except Exception:
            pass

    async def start(self, phone):
        client = self._client()
        try:
            await client.connect()
            result = await client.send_code_request(phone)
            await self._save_auth({
                "phone": phone,
                "hash": result.phone_code_hash,
                "session": client.session.save(),
            })
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(
                "Telegram рамзро нафиристод. API ID, API Hash ва рақамро санҷед."
            ) from exc
        finally:
            await self._disconnect_client(client)

    async def verify(self, code):
        from telethon.errors import SessionPasswordNeededError

        data = await self._load_auth()
        if not data:
            raise ValidationError("Муҳлати тасдиқи Telegram гузашт. Аз нав оғоз кунед.")
        client = self._client(data["session"])
        try:
            await client.connect()
            try:
                await client.sign_in(
                    data["phone"],
                    code,
                    phone_code_hash=data["hash"],
                )
            except SessionPasswordNeededError:
                data["session"] = client.session.save()
                await self._save_auth(data)
                return {"requires_2fa": True}
            except Exception as exc:
                raise ValidationError("Рамзи тасдиқи Telegram нодуруст аст.") from exc
            await self._activate(client)
            return {"requires_2fa": False}
        finally:
            await self._disconnect_client(client)

    async def verify_2fa(self, password):
        data = await self._load_auth()
        if not data:
            raise ValidationError("Муҳлати тасдиқи Telegram гузашт. Аз нав оғоз кунед.")
        client = self._client(data["session"])
        try:
            await client.connect()
            try:
                await client.sign_in(password=password)
            except Exception as exc:
                raise ValidationError("Гузарвожаи 2FA қабул нашуд.") from exc
            await self._activate(client)
        finally:
            await self._disconnect_client(client)

    async def _activate(self, client):
        me = await client.get_me()
        self.integration.set_session(client.session.save())
        self.integration.external_account_id = str(me.id)
        self.integration.status = "active"
        await self.integration.asave(
            update_fields=[
                "session_data",
                "external_account_id",
                "status",
                "updated_at",
            ]
        )
        await cache.adelete(self._auth_cache_key)

    def disconnect(self):
        cache.delete(self._auth_cache_key)
        super().disconnect()

    def send_message(self, conversation, text):
        if self.integration.status != "active":
            raise ValidationError("Пайвасти Telegram фаъол нест.")
        session = self.integration.get_session()
        if not session:
            raise ValidationError("Сессияи Telegram дастрас нест. Аз нав пайваст кунед.")

        peer = conversation.get_external_peer()
        username = conversation.contact.username
        try:
            result = asyncio.run(
                self._send_to_telegram(
                    session=session,
                    peer=peer,
                    fallback_chat_id=conversation.external_chat_id,
                    fallback_username=username,
                    text=text,
                )
            )
        except (ValidationError, APIException):
            raise
        except Exception as exc:
            raise APIException(
                "Паём ба Telegram фиристода нашуд. Пайвастро санҷед."
            ) from exc

        return self.save_outgoing(
            conversation,
            text,
            external_id=str(result.id),
            external_created_at=getattr(result, "date", None),
            metadata={"delivery_status": "sent"},
        )

    @staticmethod
    def _input_peer(peer):
        if not isinstance(peer, dict):
            return None
        peer_type = peer.get("type")
        peer_id = peer.get("id")
        if peer_id in (None, ""):
            return None

        from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

        if peer_type == "chat":
            return InputPeerChat(int(peer_id))
        access_hash = peer.get("access_hash")
        if access_hash in (None, ""):
            return None
        if peer_type == "user":
            return InputPeerUser(int(peer_id), int(access_hash))
        if peer_type == "channel":
            return InputPeerChannel(int(peer_id), int(access_hash))
        return None

    async def _send_to_telegram(
        self,
        *,
        session,
        peer,
        fallback_chat_id,
        fallback_username,
        text,
    ):
        client = self._client(session)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise ValidationError(
                    "Сессияи Telegram дигар фаъол нест. Аз нав пайваст кунед."
                )

            entity = self._input_peer(peer)
            if entity is None:
                fallback = fallback_username or fallback_chat_id
                if isinstance(fallback, str) and fallback.lstrip("-").isdigit():
                    fallback = int(fallback)
                entity = await client.get_input_entity(fallback)
            return await client.send_message(entity, text)
        except (ValidationError, APIException):
            raise
        except Exception as exc:
            raise APIException(
                "Паём ба Telegram фиристода нашуд. Пайвастро санҷед."
            ) from exc
        finally:
            await self._disconnect_client(client)
    def process_event(self, payload):
        from integrations.processing import persist_incoming
        return persist_incoming(self.integration, payload)
    def get_external_url(self, message):
        username = message.conversation.contact.username
        return f"https://t.me/{username}/{message.external_message_id}" if username else None
