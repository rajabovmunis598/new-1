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


class InstagramAPIError(Exception):
    """A sanitized Instagram transport/API error safe to show to callers."""

    def __init__(self, message="Instagram API request failed.", status_code=None):
        super().__init__(message)
        self.status_code = status_code


class InstagramAPIClient:
    authorization_endpoint = "https://www.instagram.com/oauth/authorize"
    token_endpoint = "https://api.instagram.com/oauth/access_token"
    graph_endpoint = "https://graph.instagram.com"
    scopes = (
        "instagram_business_basic",
        "instagram_business_manage_messages",
    )
    webhook_fields = (
        "messages",
        "messaging_postbacks",
        "messaging_seen",
        "message_reactions",
    )

    def __init__(self, *, app_id=None, app_secret=None, version=None):
        self.app_id = app_id if app_id is not None else settings.INSTAGRAM_APP_ID
        self.app_secret = (
            app_secret if app_secret is not None else settings.INSTAGRAM_APP_SECRET
        )
        self.version = version or settings.INSTAGRAM_API_VERSION

    def require_app_credentials(self):
        if not self.app_id or not self.app_secret:
            raise ValidationError(
                "Instagram App ID ва App Secret дар танзимоти сервер ворид нашудаанд."
            )

    def authorization_url(self, *, redirect_uri, state):
        self.require_app_credentials()
        query = urllib.parse.urlencode(
            {
                "enable_fb_login": "0",
                "force_authentication": "1",
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
            method="POST",
            form={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        short_token = short_lived.get("access_token")
        account_id = short_lived.get("user_id")
        if not short_token or not account_id:
            raise InstagramAPIError("Instagram authorization response is incomplete.")

        query = urllib.parse.urlencode(
            {
                "grant_type": "ig_exchange_token",
                "client_secret": self.app_secret,
                "access_token": short_token,
            }
        )
        long_lived = self._request(f"{self.graph_endpoint}/access_token?{query}")
        access_token = long_lived.get("access_token")
        if not access_token:
            raise InstagramAPIError("Instagram long-lived token was not returned.")
        return {
            "access_token": access_token,
            "user_id": str(account_id),
            "expires_in": int(long_lived.get("expires_in") or 0),
        }

    def get_own_profile(self, access_token):
        query = urllib.parse.urlencode(
            {
                "fields": "user_id,username",
            }
        )
        return self._request(
            f"{self.graph_endpoint}/{self.version}/me?{query}",
            access_token=access_token,
        )

    def subscribe_webhooks(self, *, account_id, access_token):
        result = self._request(
            f"{self.graph_endpoint}/{self.version}/{account_id}/subscribed_apps",
            method="POST",
            json_body={"subscribed_fields": list(self.webhook_fields)},
            access_token=access_token,
        )
        if result.get("success") is not True:
            raise InstagramAPIError("Instagram webhook subscription failed.")
        return result

    def unsubscribe_webhooks(self, *, account_id, access_token):
        return self._request(
            f"{self.graph_endpoint}/{self.version}/{account_id}/subscribed_apps",
            method="DELETE",
            access_token=access_token,
        )

    def refresh_access_token(self, access_token):
        query = urllib.parse.urlencode(
            {
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            }
        )
        return self._request(f"{self.graph_endpoint}/refresh_access_token?{query}")

    def get_user_profile(self, *, instagram_scoped_id, access_token):
        query = urllib.parse.urlencode(
            {
                "fields": "name,username,profile_pic",
            }
        )
        return self._request(
            f"{self.graph_endpoint}/{self.version}/{instagram_scoped_id}?{query}",
            access_token=access_token,
        )

    def send_text(self, *, account_id, recipient_id, text, access_token):
        return self._request(
            f"{self.graph_endpoint}/{self.version}/{account_id}/messages",
            method="POST",
            json_body={
                "recipient": {"id": str(recipient_id)},
                "message": {"text": text},
            },
            access_token=access_token,
        )

    @staticmethod
    def _request(
        url,
        *,
        method="GET",
        form=None,
        json_body=None,
        access_token=None,
    ):
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

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise InstagramAPIError(status_code=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise InstagramAPIError("Instagram is temporarily unavailable.") from exc

        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InstagramAPIError("Instagram returned an invalid response.") from exc
        if not isinstance(value, dict):
            raise InstagramAPIError("Instagram returned an invalid response.")
        return value


class InstagramMessagingIntegration(BaseIntegration):
    def _credentials(self):
        credentials = self.integration.get_credentials()
        if not credentials.get("access_token"):
            raise ValidationError(
                "Instagram access token дастрас нест. Ҳисобро аз нав пайваст кунед."
            )
        return credentials

    def _access_token(self):
        credentials = self._credentials()
        expires_at = parse_datetime(str(credentials.get("expires_at") or ""))
        if expires_at and timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)
        if expires_at and expires_at <= timezone.now() + timedelta(days=7):
            try:
                refreshed = InstagramAPIClient().refresh_access_token(
                    credentials["access_token"]
                )
            except InstagramAPIError as exc:
                raise APIException(
                    "Instagram token нав карда нашуд. Ҳисобро аз нав пайваст кунед."
                ) from exc
            token = refreshed.get("access_token")
            if not token:
                raise APIException(
                    "Instagram token нав карда нашуд. Ҳисобро аз нав пайваст кунед."
                )
            credentials["access_token"] = token
            expires_in = int(refreshed.get("expires_in") or 0)
            if expires_in:
                credentials["expires_at"] = (
                    timezone.now() + timedelta(seconds=expires_in)
                ).isoformat()
            self.integration.set_credentials(credentials)
            self.integration.save(update_fields=["credentials", "updated_at"])
        return credentials["access_token"]

    def disconnect(self):
        credentials = self.integration.get_credentials()
        token = credentials.get("access_token")
        if token and self.integration.external_account_id:
            try:
                InstagramAPIClient().unsubscribe_webhooks(
                    account_id=self.integration.external_account_id,
                    access_token=token,
                )
            except InstagramAPIError:
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
        if self.integration.status != "active":
            raise ValidationError("Пайвасти Instagram фаъол нест.")
        recipient_id = conversation.contact.external_id or conversation.external_chat_id
        if not recipient_id:
            raise ValidationError("Қабулкунандаи Instagram муайян нашудааст.")
        try:
            result = InstagramAPIClient().send_text(
                account_id=self.integration.external_account_id,
                recipient_id=recipient_id,
                text=text,
                access_token=self._access_token(),
            )
        except InstagramAPIError as exc:
            raise APIException(
                "Паём ба Instagram фиристода нашуд. Permission ва муҳлати ҷавобро санҷед."
            ) from exc
        external_id = result.get("message_id")
        if not external_id:
            raise APIException("Instagram ID-и паёми фиристодашударо барнагардонд.")
        return self.save_outgoing(
            conversation,
            text,
            external_id=str(external_id),
            metadata={"delivery_status": "sent"},
        )

    def get_user_profile(self, instagram_scoped_id):
        try:
            return InstagramAPIClient().get_user_profile(
                instagram_scoped_id=instagram_scoped_id,
                access_token=self._access_token(),
            )
        except (InstagramAPIError, APIException, ValidationError):
            return {}

    def process_event(self, payload):
        from integrations.processing import persist_incoming

        return persist_incoming(self.integration, payload)

    def get_external_url(self, message):
        username = message.conversation.contact.username
        return f"https://www.instagram.com/{username}/" if username else None
