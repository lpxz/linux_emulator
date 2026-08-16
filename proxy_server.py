"""proxy_server.py — machine C. WebSocket :8091. The only process that execs."""
import json
import subprocess

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from allowed_cmds import ALLOWED, is_recursive_rm

app = FastAPI()

OPS = {
    "list": lambda path: ["ls", "-la", path],
    "create": lambda path: ["touch", path],
    "remove": lambda path: ["rm", "-f", path],
}


def run_argv(argv) -> dict:
    if not argv:
        return {"ok": False, "stdout": "", "stderr": "empty argv"}
    cmd = str(argv[0])
    if cmd not in ALLOWED:
        return {"ok": False, "stdout": "", "stderr": f"unknown command: {cmd}"}
    if is_recursive_rm(argv):
        return {"ok": False, "stdout": "", "stderr": "rm -r is not allowed"}
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


def run_op(op: str, path: str) -> dict:
    if op not in OPS:
        return {"ok": False, "stdout": "", "stderr": f"unknown op: {op}"}
    if not path:
        return {"ok": False, "stdout": "", "stderr": "empty path"}
    return run_argv(OPS[op](path))


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
            if isinstance(msg.get("argv"), list):
                argv = [str(a) for a in msg["argv"]]
                result = run_argv(argv)
            else:
                result = run_op(str(msg.get("op") or ""), str(msg.get("path") or ""))
            await ws.send_text(json.dumps(result))
    except WebSocketDisconnect:
        return
