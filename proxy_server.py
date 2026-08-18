"""proxy_server.py — machine C. Local daemon. The only process that execs."""
import asyncio
import json
import os
import subprocess

import websockets

from allowed_cmds import ALLOWED, is_recursive_rm

REMOTE_URL = os.environ.get("REMOTE_PROXY_URL", "ws://127.0.0.1:8090/proxy")
BACKOFF_INITIAL = 1.0
BACKOFF_CAP = 30.0


def next_backoff(delay: float) -> float:
    return min(max(delay, BACKOFF_INITIAL) * 2, BACKOFF_CAP)

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


def handle_message(raw: str) -> dict:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "stdout": "", "stderr": "bad json"}
    if isinstance(msg.get("argv"), list):
        return run_argv([str(a) for a in msg["argv"]])
    return run_op(str(msg.get("op") or ""), str(msg.get("path") or ""))


async def serve_proxy_socket(ws):
    async for raw in ws:
        await ws.send(json.dumps(handle_message(raw)))


async def run_daemon():
    delay = BACKOFF_INITIAL
    while True:
        try:
            async with websockets.connect(REMOTE_URL) as ws:
                delay = BACKOFF_INITIAL
                await serve_proxy_socket(ws)
        except Exception:
            pass
        await asyncio.sleep(delay)
        delay = next_backoff(delay)


if __name__ == "__main__":
    asyncio.run(run_daemon())
