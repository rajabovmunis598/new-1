import hashlib
import hmac
import json
import urllib.error
import urllib.request

from rest_framework.exceptions import APIException

from .base import BaseIntegration


class ViberIntegration(BaseIntegration):
    endpoint = "https://chatapi.viber.com/pa/send_message"
    webhook_endpoint = "https://chatapi.viber.com/pa/set_webhook"

    def set_webhook(self, url):
        result = self._request_to(self.webhook_endpoint, {"url": url})
        return result

    def _request_to(self, endpoint, payload):
        token = self.integration.get_credentials().get("auth_token", "")
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "X-Viber-Auth-Token": token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc:
            raise APIException("Viber API request failed") from exc
        if result.get("status") not in (0, "0", None):
            raise APIException(result.get("status_message") or "Viber API rejected the request")
        return result

    def _request(self, payload):
        result = self._request_to(self.endpoint, payload)
        return result

    def send_message(self, conversation, text):
        receiver = conversation.external_chat_id
        result = self._request({
            "receiver": receiver,
            "type": "text",
            "text": text,
            "min_api_version": 7,
        })
        return self.save_outgoing(conversation, text, metadata={"api_response": result})

    def process_event(self, payload):
        from integrations.processing import persist_incoming
        return persist_incoming(self.integration, payload)

    @staticmethod
    def valid_signature(body, signature, token):
        if not signature or not token:
            return False
        expected = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
