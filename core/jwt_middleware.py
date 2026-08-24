from urllib.parse import parse_qs

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.tokens import AccessToken

try:
    from channels.db import database_sync_to_async
except ImportError:  # Keep this module importable when optional Channels is absent.
    from asgiref.sync import sync_to_async

    def database_sync_to_async(func):
        return sync_to_async(func, thread_sensitive=True)


def _access_token_from_scope(scope):
    """Return (was_supplied, token), rejecting ambiguous token parameters."""
    query_string = scope.get("query_string", b"")
    try:
        query = query_string.decode("utf-8")
        values = parse_qs(
            query,
            keep_blank_values=True,
            max_num_fields=100,
        ).get("token")
    except (AttributeError, UnicodeDecodeError, ValueError):
        return False, None

    if values is None:
        return False, None
    if len(values) != 1 or not values[0] or len(values[0]) > 4096:
        return True, None
    return True, values[0]


def _user_for_access_token(raw_token):
    if raw_token is None:
        return AnonymousUser()

    try:
        validated_token = AccessToken(raw_token)
        return JWTAuthentication().get_user(validated_token)
    except (AuthenticationFailed, TokenError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Authenticate WebSockets from a SimpleJWT access token query parameter."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token_supplied, raw_token = _access_token_from_scope(scope)
        if token_supplied:
            scope = dict(scope)
            scope["user"] = await database_sync_to_async(_user_for_access_token)(
                raw_token
            )
        return await self.inner(scope, receive, send)

