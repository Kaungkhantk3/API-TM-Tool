"""Small signed-token authentication for the single-admin deployment."""

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


def auth_config() -> tuple[str, str, str]:
    return (
        os.getenv("ADMIN_USERNAME", ""),
        os.getenv("ADMIN_PASSWORD", ""),
        os.getenv("AUTH_SECRET", ""),
    )


def validate_auth_config() -> None:
    username, password, secret = auth_config()
    if not username or not password or len(secret) < 32:
        raise RuntimeError("Set ADMIN_USERNAME, ADMIN_PASSWORD, and an AUTH_SECRET of at least 32 characters.")


def authenticate(username: str, password: str) -> bool:
    admin_username, admin_password, _ = auth_config()
    return hmac.compare_digest(username, admin_username) and hmac.compare_digest(password, admin_password)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(username: str) -> str:
    _, _, secret = auth_config()
    payload = {"sub": username, "exp": int(time.time()) + 60 * 60 * 8}
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), encoded_payload.encode(), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        admin_username, _, secret = auth_config()
        payload_part, signature_part = credentials.credentials.split(".", 1)
        expected = hmac.new(secret.encode(), payload_part.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_decode(signature_part), expected):
            raise ValueError("Invalid signature")
        payload = json.loads(_decode(payload_part))
        if payload["sub"] != admin_username or payload["exp"] <= time.time():
            raise ValueError("Expired token")
        return payload["sub"]
    except (KeyError, ValueError, json.JSONDecodeError):
        raise unauthorized
