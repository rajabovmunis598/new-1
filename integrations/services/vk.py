import json
import secrets as secrets_module
import urllib.error
import urllib.parse
import urllib.request

from rest_framework.exceptions import APIException

from .base import BaseIntegration


class VKIntegration(BaseIntegration):
    endpoint = "https://api.vk.com/method/messages.send"

    @staticmethod
    def api_call(method, access_token, **params):
        params.update({"access_token": access_token, "v": params.get("v", "5.199")})
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(f"https://api.vk.com/method/{method}?{query}")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc:
            raise APIException("VK API request failed") from exc
        if result.get("error"):
            raise APIException(result["error"].get("error_msg") or "VK API rejected the request")
        return result.get("response") or {}

    @classmethod
    def admin_group(cls, user_token):
        groups = cls.api_call("groups.get", user_token, filter="admin", extended=1)
        items = groups.get("items") if isinstance(groups, dict) else groups
        if not items:
            raise APIException("No VK communities with administrator access were found.")
        return items[0]

    @classmethod
    def configure_callback(cls, access_token, group_id, callback_url, secret):
        server = cls.api_call(
            "groups.addCallbackServer",
            access_token,
            group_id=group_id,
            url=callback_url,
            title="Munis Business Hub",
            secret=secret,
        )
        server_id = server.get("server_id") if isinstance(server, dict) else server
        if not server_id:
            raise APIException("VK did not return a callback server id.")
        confirmation = cls.api_call(
            "groups.getCallbackConfirmationCode",
            access_token,
            group_id=group_id,
        ).get("code", "")
        cls.api_call(
            "groups.setCallbackSettings",
            access_token,
            group_id=group_id,
            server_id=server_id,
            api_version="5.199",
            enabled=1,
            message_new=1,
        )
        return str(confirmation)

    def send_message(self, conversation, text):
        credentials = self.integration.get_credentials()
        if credentials.get("demo"):
            return self.save_outgoing(conversation, text, metadata={"demo": True, "delivery_status": "sent"})
        params = urllib.parse.urlencode({
            "access_token": credentials.get("access_token", ""),
            "v": credentials.get("api_version", "5.199"),
            "peer_id": conversation.external_chat_id,
            "random_id": secrets_module.randbelow(2_000_000_000),
            "message": text,
        })
        request = urllib.request.Request(f"{self.endpoint}?{params}")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc:
            raise APIException("VK API request failed") from exc
        if result.get("error"):
            raise APIException(result["error"].get("error_msg") or "VK API rejected the message")
        response_data = result.get("response") or {}
        external_id = response_data.get("conversation_message_id") if isinstance(response_data, dict) else response_data
        return self.save_outgoing(conversation, text, external_id, {"api_response": result})

    def process_event(self, payload):
        from integrations.processing import persist_incoming
        return persist_incoming(self.integration, payload)
