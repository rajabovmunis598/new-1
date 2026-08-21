import base64
import hashlib
import hmac
import json
from django.conf import settings
from django.core.signing import BadSignature, Signer


def _key():
    return hashlib.sha256(settings.SECRET_KEY.encode()).digest()


def encrypt_json(value):
    raw = json.dumps(value, separators=(",", ":")).encode()
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_key())
        return "fernet:" + Fernet(key).encrypt(raw).decode()
    except ImportError:
        pass
    key = _key()
    encrypted = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(raw))
    return Signer().sign(base64.urlsafe_b64encode(encrypted).decode())


def decrypt_json(value):
    if not value:
        return {}
    try:
        if value.startswith("fernet:"):
            from cryptography.fernet import Fernet, InvalidToken
            return json.loads(Fernet(base64.urlsafe_b64encode(_key())).decrypt(value[7:].encode()))
        encrypted = base64.urlsafe_b64decode(Signer().unsign(value))
        key = _key()
        raw = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(encrypted))
        return json.loads(raw)
    except Exception:
        return {}


def verify_meta_signature(body, signature, secret):
    if not signature or not signature.startswith("sha256=") or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)
