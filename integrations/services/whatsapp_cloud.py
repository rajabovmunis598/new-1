import json
import os
import urllib.error
import urllib.request
from rest_framework.exceptions import APIException
from .base import BaseIntegration

class WhatsAppCloudIntegration(BaseIntegration):
    def send_message(self, conversation, text):
        credentials = self.integration.get_credentials()
        version = os.getenv("WHATSAPP_API_VERSION", "v23.0")
        url = f"https://graph.facebook.com/{version}/{credentials.get('phone_number_id')}/messages"
        payload = {"messaging_product":"whatsapp", "to":conversation.contact.phone or conversation.contact.external_id, "type":"text", "text":{"body":text}}
        request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {credentials.get('access_token','')}", "Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response: result = json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc: raise APIException("WhatsApp API request failed") from exc
        external_id = (result.get("messages") or [{}])[0].get("id")
        return self.save_outgoing(conversation, text, external_id, {"api_response": result})
    def process_event(self, payload):
        from integrations.processing import persist_incoming
        return persist_incoming(self.integration, payload)
    def get_external_url(self, message):
        phone = message.conversation.contact.phone
        return f"https://wa.me/{phone.lstrip('+')}" if phone else None
