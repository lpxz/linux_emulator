"""C dials B /proxy; B asks C on that socket. Browser still uses /ws."""
import json
import threading
import time

import pytest
import uvicorn
import websockets
from websockets.sync.client import connect

from remote_server import app

HOST = "127.0.0.1"
PORT = 18090
WS = f"ws://{HOST}:{PORT}"
HTTP = f"http://{HOST}:{PORT}"


@pytest.fixture(scope="module")
def server():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    srv = uvicorn.Server(config)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(80):
        if getattr(srv, "started", False):
            break
        time.sleep(0.05)
    else:
        pytest.fail("uvicorn did not start")
    yield
    srv.should_exit = True


def test_get_ui(server):
    import urllib.request

    with urllib.request.urlopen(HTTP + "/") as r:
        assert r.status == 200
        body = r.read().decode()
        assert "linux_emulator" in body


def test_proxy_unavailable_when_c_not_connected(server):
    with connect(WS + "/ws") as browser:
        browser.send(json.dumps({"type": "user", "text": "echo hello"}))
        msg = json.loads(browser.recv(timeout=5))
    assert msg["type"] == "error"
    assert "proxy unavailable" in msg["text"]


def test_b_asks_c_on_socket_c_opened(server):
    with connect(WS + "/proxy") as proxy:
        with connect(WS + "/ws") as browser:
            browser.send(json.dumps({"type": "user", "text": "echo hello"}))
            req = json.loads(proxy.recv(timeout=5))
            assert req.get("argv") == ["echo", "hello"]
            proxy.send(json.dumps({"ok": True, "stdout": "hello\n", "stderr": ""}))
            msg = json.loads(browser.recv(timeout=5))
    assert msg["type"] == "result"
    assert "hello" in msg["text"]


def test_unknown_command_does_not_ask_c(server):
    with connect(WS + "/proxy") as proxy:
        with connect(WS + "/ws") as browser:
            browser.send(json.dumps({"type": "user", "text": "curl http://x"}))
            msg = json.loads(browser.recv(timeout=5))
            assert msg["type"] == "error"
            with pytest.raises(TimeoutError):
                proxy.recv(timeout=0.4)


def test_proxy_client_roundtrip(server):
    import asyncio

    import proxy_server
    import websockets as ws_aio

    connected = threading.Event()
    stop = threading.Event()

    async def run_c():
        while not stop.is_set():
            try:
                async with ws_aio.connect(WS + "/proxy") as sock:
                    connected.set()
                    await proxy_server.serve_proxy_socket(sock)
                    return
            except Exception:
                await asyncio.sleep(0.05)

    t = threading.Thread(target=lambda: asyncio.run(run_c()), daemon=True)
    t.start()
    assert connected.wait(timeout=5)
    try:
        with connect(WS + "/ws") as browser:
            browser.send(json.dumps({"type": "user", "text": "echo hello"}))
            msg = json.loads(browser.recv(timeout=8))
        assert msg["type"] == "result"
        assert "hello" in msg["text"]
    finally:
        stop.set()
