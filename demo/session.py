"""Cookie de sessão assinado (HMAC-SHA256) para o login do web-demo."""
import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

SESSION_COOKIE = "demo_session"
SESSION_TTL_SECONDS = 43200  # 12h


def make_session(username: str, secret: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    payload = {"u": username, "exp": int(time.time()) + ttl_seconds}
    body = urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def read_session(token: str, secret: str) -> str | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    padding = "=" * (-len(body) % 4)
    try:
        payload = json.loads(urlsafe_b64decode(body + padding))
    except ValueError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("exp"), (int, float)):
        return None
    if payload["exp"] < time.time():
        return None
    user = payload.get("u")
    return user if isinstance(user, str) else None
