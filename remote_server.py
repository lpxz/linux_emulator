"""remote_server.py — machine B (cloud mock). HTTP+WS :8090. Must not exec."""
import asyncio
import json
import re
import shlex
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from allowed_cmds import ALLOWED, has_shell_meta, is_recursive_rm

app = FastAPI()

proxy_lock = asyncio.Lock()
proxy_ws: Optional[WebSocket] = None
proxy_replies: Optional[asyncio.Queue] = None

LIST_RE = re.compile(r"^list all files in\s+(.+)$", re.I)
ADD_RE = re.compile(r"^add file\s+(.+)$", re.I)
REMOVE_RE = re.compile(r"^remove file\s+(.+)$", re.I)

UNKNOWN = (
    "unknown command; try a common Linux command (ls, mkdir, touch, cat, …) "
    "or: list all files in <path> | add file <path> | remove file <path>"
)


def expand_path(raw: str) -> str:
    raw = raw.strip().strip("'\"")
    if raw in ("~", "~/"):
        return str(Path.home())
    if raw.startswith("~/"):
        return str(Path.home() / raw[2:])
    return raw


def expand_argv(argv):
    out = []
    for a in argv:
        if a == "~" or a.startswith("~/"):
            out.append(expand_path(a))
        else:
            out.append(a)
    return out


def english_to_argv(text: str):
    text = (text or "").strip()
    m = LIST_RE.match(text)
    if m:
        path = expand_path(m.group(1))
        return ["ls", "-la", path] if path else None
    m = ADD_RE.match(text)
    if m:
        path = expand_path(m.group(1))
        return ["touch", path] if path else None
    m = REMOVE_RE.match(text)
    if m:
        path = expand_path(m.group(1))
        return ["rm", "-f", path] if path else None
    return False


def parse_to_argv(text: str):
    """Return argv list, or an error string, or None for unknown."""
    text = (text or "").strip()
    if not text:
        return None
    mapped = english_to_argv(text)
    if mapped is None:
        return "empty path"
    if mapped:
        return mapped
    if has_shell_meta(text):
        return "no shell: pipes, redirects, and ; & ` $ are not allowed"
    try:
        argv = shlex.split(text)
    except ValueError as e:
        return str(e)
    if not argv:
        return None
    if argv[0] not in ALLOWED:
        return None
    argv = expand_argv(argv)
    if is_recursive_rm(argv):
        return "rm -r is not allowed"
    return argv


async def call_proxy(argv) -> dict:
    global proxy_ws, proxy_replies
    async with proxy_lock:
        ws = proxy_ws
        q = proxy_replies
        if ws is None or q is None:
            raise RuntimeError("proxy is down")
        while not q.empty():
            q.get_nowait()
        try:
            await ws.send_text(json.dumps({"argv": argv}))
            raw = await asyncio.wait_for(q.get(), timeout=15)
        except Exception:
            if proxy_ws is ws:
                proxy_ws = None
                proxy_replies = None
            raise
        return json.loads(raw)


@app.get("/")
async def serve_ui():
    return FileResponse("ui.html")


@app.websocket("/proxy")
async def proxy_from_c(ws: WebSocket):
    """C dials this socket; B then asks C on it."""
    global proxy_ws, proxy_replies
    await ws.accept()
    old = proxy_ws
    proxy_ws = ws
    proxy_replies = asyncio.Queue()
    if old is not None and old is not ws:
        try:
            await old.close()
        except Exception:
            pass
    try:
        while True:
            raw = await ws.receive_text()
            if proxy_replies is not None:
                await proxy_replies.put(raw)
    except WebSocketDisconnect:
        pass
    finally:
        if proxy_ws is ws:
            proxy_ws = None
            proxy_replies = None


@app.websocket("/ws")
async def browser_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "text": "bad json"}))
                continue
            if msg.get("type") != "user":
                continue
            parsed = parse_to_argv(msg.get("text") or "")
            if isinstance(parsed, str):
                await ws.send_text(json.dumps({"type": "error", "text": parsed}))
                continue
            if not parsed:
                await ws.send_text(json.dumps({"type": "error", "text": UNKNOWN}))
                continue
            try:
                result = await call_proxy(parsed)
            except Exception:
                await ws.send_text(
                    json.dumps({"type": "error", "text": "proxy is down"})
                )
                continue
            if result.get("ok"):
                text = result.get("stdout") or "(ok)"
                await ws.send_text(json.dumps({"type": "result", "text": text}))
            else:
                err = (result.get("stderr") or result.get("stdout") or "command failed").strip()
                await ws.send_text(json.dumps({"type": "error", "text": err}))
    except WebSocketDisconnect:
        return
