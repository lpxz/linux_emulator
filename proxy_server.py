"""proxy_server.py — machine C. WebSocket :8091. The only process that execs."""
import json
import subprocess

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

OPS = {
    "list": lambda path: ["ls", "-la", path],
    "create": lambda path: ["touch", path],
    "remove": lambda path: ["rm", "-f", path],
}


def run_op(op: str, path: str) -> dict:
    if op not in OPS:
        return {"ok": False, "stdout": "", "stderr": f"unknown op: {op}"}
    if not path:
        return {"ok": False, "stdout": "", "stderr": "empty path"}
    try:
        r = subprocess.run(
            OPS[op](path), capture_output=True, text=True, timeout=10
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


@app.websocket("/ws")
async def proxy_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps({"ok": False, "stdout": "", "stderr": "bad json"})
                )
                continue
            result = run_op(str(msg.get("op") or ""), str(msg.get("path") or ""))
            await ws.send_text(json.dumps(result))
    except WebSocketDisconnect:
        return
