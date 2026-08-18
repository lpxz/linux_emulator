"""HS256 JWT: C proves sub is the daemon id B knows."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

ALG = "HS256"
DEFAULT_SECRET = "linux-emulator-dev-secret-key-32b"
DEFAULT_SUB = "local-1"


def jwt_secret() -> str:
    return os.environ.get("DAEMON_JWT_SECRET", DEFAULT_SECRET)


def known_daemon_id() -> str:
    return os.environ.get("DAEMON_ID", DEFAULT_SUB)


def issue_token(
    daemon_id: Optional[str] = None,
    secret: Optional[str] = None,
    ttl_s: int = 3600,
) -> str:
    sub = daemon_id if daemon_id is not None else known_daemon_id()
    key = secret if secret is not None else jwt_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_s),
    }
    return jwt.encode(payload, key, algorithm=ALG)


def proxy_ws_url(base: Optional[str] = None, token: Optional[str] = None) -> str:
    """Attach a JWT query param. Does not log the token."""
    from urllib.parse import quote

    url = base or os.environ.get("REMOTE_PROXY_URL", "ws://127.0.0.1:8090/proxy")
    tok = token if token is not None else issue_token()
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={quote(tok, safe='')}"


def verify_token(
    token: Optional[str],
    secret: Optional[str] = None,
    allowed_sub: Optional[str] = None,
) -> Optional[dict]:
    if not token:
        return None
    key = secret if secret is not None else jwt_secret()
    want = allowed_sub if allowed_sub is not None else known_daemon_id()
    try:
        payload = jwt.decode(token, key, algorithms=[ALG])
    except jwt.PyJWTError:
        return None
    if payload.get("sub") != want:
        return None
    return payload
