import secrets
import hashlib
import base64


def create_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def create_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


def create_state() -> str:
    return secrets.token_urlsafe(32)
