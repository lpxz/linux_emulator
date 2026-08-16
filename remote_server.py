"""remote_server.py — machine B (cloud mock). HTTP+WS :8090. Must not exec."""
import json
import re
from pathlib import Path

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI()

PROXY_URL = "ws://127.0.0.1:8091/ws"

LIST_RE = re.compile(r"^list all files in\s+(.+)$", re.I)
ADD_RE = re.compile(r"^add file\s+(.+)$", re.I)
REMOVE_RE = re.compile(r"^remove file\s+(.+)$", re.I)

OP_FOR = {
    "list": "list",
    "add": "create",
    "remove": "remove",
}


def expand_path(raw: str) -> str:
    raw = raw.strip().strip("'\"")
    if raw in ("~", "~/"):
        return str(Path.home())
    if raw.startswith("~/"):
        return str(Path.home() / raw[2:])
    return raw


def parse_intent(text: str):
    text = (text or "").strip()
    m = LIST_RE.match(text)
    if m:
        return "list", expand_path(m.group(1))
    m = ADD_RE.match(text)
    if m:
        return "add", expand_path(m.group(1))
    m = REMOVE_RE.match(text)
    if m:
        return "remove", expand_path(m.group(1))
    return None, None


async def call_proxy(op: str, path: str) -> dict:
    async with websockets.connect(PROXY_URL) as ws:
        await ws.send(json.dumps({"op": op, "path": path}))
        raw = await ws.recv()
        return json.loads(raw)


@app.get("/")
async def serve_ui():
    return FileResponse("ui.html")


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
            kind, path = parse_intent(msg.get("text") or "")
            if not kind or not path:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "text": "unknown phrase; try: list all files in <path> | add file <path> | remove file <path>",
                        }
                    )
                )
                continue
            try:
                result = await call_proxy(OP_FOR[kind], path)
            except Exception as e:
                await ws.send_text(
                    json.dumps({"type": "error", "text": f"proxy unavailable: {e}"})
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
