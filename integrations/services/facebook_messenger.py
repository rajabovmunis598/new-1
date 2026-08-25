import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException, ValidationError

from .base import BaseIntegration


class FacebookAPIError(Exception):
    def __init__(self, message="Facebook API request failed.", status_code=None):
        super().__init__(message)
        self.status_code = status_code


class FacebookGraphClient:
    authorization_endpoint = "https://www.facebook.com/v21.0/dialog/oauth"
    token_endpoint = "https://graph.facebook.com/v21.0/oauth/access_token"
    graph_endpoint = "https://graph.facebook.com/v21.0"
    scopes = (
        "pages_messaging",
        "pages_show_list",
        "pages_manage_metadata",
    )
    webhook_fields = (
        "messages",
        "messaging_postbacks",
        "messaging_seen",
        "message_reactions",
    )

    def __init__(self, *, app_id=None, app_secret=None):
        self.app_id = app_id or getattr(settings, "FACEBOOK_APP_ID", "")
        self.app_secret = app_secret or getattr(settings, "FACEBOOK_APP_SECRET", "")

    def require_app_credentials(self):
        if not self.app_id or not self.app_secret:
            raise ValidationError(
                "Facebook App ID ва App Secret дар танзимоти сервер ворид нашудаанд."
            )

    def authorization_url(self, *, redirect_uri, state):
        self.require_app_credentials()
        query = urllib.parse.urlencode(
            {
                "client_id": self.app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": ",".join(self.scopes),
                "state": state,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    def exchange_code(self, *, code, redirect_uri):
        self.require_app_credentials()
        short_lived = self._request(
            self.token_endpoint,
            form={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        short_token = short_lived.get("access_token")
        if not short_token:
            raise FacebookAPIError("Facebook authorization response is incomplete.")

        query = urllib.parse.urlencode(
            {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short_token,
            }
        )
        long_lived = self._request(f"{self.token_endpoint}?{query}")
        access_token = long_lived.get("access_token")
        if not access_token:
            raise FacebookAPIError("Facebook long-lived token was not returned.")
        return {
            "access_token": access_token,
            "expires_in": int(long_lived.get("expires_in") or 0),
        }

    def get_pages(self, access_token):
        query = urllib.parse.urlencode({"access_token": access_token})
        return self._request(f"{self.graph_endpoint}/me/accounts?{query}")

    def subscribe_webhooks(self, *, page_id, access_token):
        result = self._request(
            f"{self.graph_endpoint}/{page_id}/subscribed_apps",
            method="POST",
            json_body={"subscribed_fields": list(self.webhook_fields)},
            access_token=access_token,
        )
        return result

    def unsubscribe_webhooks(self, *, page_id, access_token):
        return self._request(
            f"{self.graph_endpoint}/{page_id}/subscribed_apps",
            method="DELETE",
            access_token=access_token,
        )

    def get_user_profile(self, *, user_id, access_token):
        query = urllib.parse.urlencode(
            {
                "fields": "name,profile_pic",
                "access_token": access_token,
            }
        )
        return self._request(f"{self.graph_endpoint}/{user_id}?{query}")

    def send_text(self, *, page_id, recipient_id, text, access_token):
        return self._request(
            f"{self.graph_endpoint}/{page_id}/messages",
            method="POST",
            json_body={
                "recipient": {"id": str(recipient_id)},
                "message": {"text": text},
            },
            access_token=access_token,
        )

    @staticmethod
    def _request(url, *, method="GET", form=None, json_body=None, access_token=None):
        headers = {
            "Accept": "application/json",
            "User-Agent": "MunisBusinessHub/1.0",
        }
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise FacebookAPIError(status_code=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FacebookAPIError("Facebook is temporarily unavailable.") from exc

        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise FacebookAPIError("Facebook returned an invalid response.") from exc
        if not isinstance(value, dict):
            raise FacebookAPIError("Facebook returned an invalid response.")
        return value


class FacebookMessengerIntegration(BaseIntegration):
    def _credentials(self):
        credentials = self.integration.get_credentials()
        if not credentials.get("access_token"):
            raise ValidationError(
                "Facebook access token дастрас нест. Ҳисобро аз нав пайваст кунед."
            )
        return credentials

    def _access_token(self):
        return self._credentials()["access_token"]

    def disconnect(self):
        credentials = self.integration.get_credentials()
        token = credentials.get("access_token")
        if token and self.integration.external_account_id:
            try:
                FacebookGraphClient().unsubscribe_webhooks(
                    page_id=self.integration.external_account_id,
                    access_token=token,
                )
            except FacebookAPIError:
                pass
        self.integration.credentials = {}
        self.integration.session_data = ""
        self.integration.webhook_url = ""
        self.integration.status = "inactive"
        self.integration.save(
            update_fields=[
                "credentials",
                "session_data",
                "webhook_url",
                "status",
                "updated_at",
            ]
        )

    def send_message(self, conversation, text):
        if self.integration.get_credentials().get("demo"):
            return self.save_outgoing(conversation, text, metadata={"demo": True, "delivery_status": "sent"})
        if self.integration.status != "active":
            raise ValidationError("Пайвасти Facebook фаъол нест.")
        recipient_id = conversation.contact.external_id or conversation.external_chat_id
        if not recipient_id:
            raise ValidationError("Қабулкунандаи Facebook муайян нашудааст.")
        try:
            result = FacebookGraphClient().send_text(
                page_id=self.integration.external_account_id,
                recipient_id=recipient_id,
                text=text,
                access_token=self._access_token(),
            )
        except FacebookAPIError as exc:
            raise APIException(
                "Паём ба Facebook фиристода нашуд."
            ) from exc
        external_id = result.get("message_id")
        if not external_id:
            raise APIException("Facebook ID-и паёми фиристодашударо барнагардонд.")
        return self.save_outgoing(
            conversation,
            text,
            external_id=str(external_id),
            metadata={"delivery_status": "sent"},
        )

    def get_user_profile(self, user_id):
        try:
            return FacebookGraphClient().get_user_profile(
                user_id=user_id,
                access_token=self._access_token(),
            )
        except (FacebookAPIError, APIException, ValidationError):
            return {}

    def process_event(self, payload):
        from integrations.processing import persist_incoming

        return persist_incoming(self.integration, payload)

    def get_external_url(self, message):
        return None
