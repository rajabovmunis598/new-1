import base64
import hashlib
import hmac
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.signing import BadSignature, Signer


def _key(secret=None):
    value = secret or settings.INTEGRATION_ENCRYPTION_KEY
    return hashlib.sha256(value.encode()).digest()


def encrypt_json(value):
    raw = json.dumps(value, separators=(",", ":")).encode()
    key = base64.urlsafe_b64encode(_key())
    return "fernet:" + Fernet(key).encrypt(raw).decode()


def decrypt_json(value):
    if not value:
        return {}
    try:
        if value.startswith("fernet:"):
            encrypted_value = value[7:].encode()
            secrets = dict.fromkeys(
                (settings.INTEGRATION_ENCRYPTION_KEY, settings.SECRET_KEY)
            )
            for secret in secrets:
                try:
                    key = base64.urlsafe_b64encode(_key(secret))
                    return json.loads(Fernet(key).decrypt(encrypted_value))
                except InvalidToken:
                    continue
            return {}

        # Backward compatibility for values written before Fernet became
        # mandatory. All newly written credentials use Fernet above.
        encrypted = base64.urlsafe_b64decode(Signer().unsign(value))
        key = _key(settings.SECRET_KEY)
        raw = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(encrypted))
        return json.loads(raw)
    except (BadSignature, InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return {}


def verify_meta_signature(body, signature, secret):
    if not signature or not signature.startswith("sha256=") or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)
