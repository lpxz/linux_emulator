"""JWT proves C is the daemon id B knows (HS256 + sub)."""
import time

from daemon_auth import issue_token, verify_token

SECRET = "x" * 32


def test_roundtrip_known_daemon():
    tok = issue_token(daemon_id="local-1", secret=SECRET)
    claims = verify_token(tok, secret=SECRET, allowed_sub="local-1")
    assert claims is not None
    assert claims["sub"] == "local-1"


def test_wrong_secret_rejected():
    tok = issue_token(daemon_id="local-1", secret=SECRET)
    assert verify_token(tok, secret="y" * 32, allowed_sub="local-1") is None


def test_unknown_sub_rejected():
    tok = issue_token(daemon_id="evil", secret=SECRET)
    assert verify_token(tok, secret=SECRET, allowed_sub="local-1") is None


def test_missing_token_rejected():
    assert verify_token(None, secret=SECRET, allowed_sub="local-1") is None
    assert verify_token("", secret=SECRET, allowed_sub="local-1") is None


def test_expired_rejected():
    tok = issue_token(daemon_id="local-1", secret=SECRET, ttl_s=-1)
    time.sleep(0.05)
    assert verify_token(tok, secret=SECRET, allowed_sub="local-1") is None


def test_garbage_rejected():
    assert verify_token("not.a.jwt", secret=SECRET, allowed_sub="local-1") is None
