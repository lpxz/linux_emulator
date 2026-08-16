# linux_emulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three local processes that mock HTML → cloud agent → laptop proxy, with three NL file commands.

**Architecture:** Browser WebSocket to `remote_server.py` on :8090 (parse only, no exec). Remote WebSocket client to `proxy_server.py` on :8091 (argv `ls`/`touch`/`rm` only). Start proxy first.

**Tech Stack:** Python 3.9+, FastAPI, Uvicorn, websockets.

**Spec:** `docs/superpowers/specs/2026-08-16-linux-emulator-design.md`

## Global Constraints

- Manual testing only
- `remote_server.py` must not import `subprocess` or call `os.system`; no file create/delete
- Proxy: `subprocess.run(argv, …)` never `shell=True`; timeout 10s
- Ports: remote HTTP+WS **8090**, proxy WS **8091**
- Intents only: `list all files in <path>`, `add file <path>`, `remove file <path>` (case-insensitive)
- list → `ls -la`; add → `touch`; remove → `rm -f` (no `-r`)
- Expand leading `~` via `Path.home()` string join on the remote
- Browser JSON: `user` in; `result` / `error` out
- Proxy JSON: `{op, path}` in; `{ok, stdout, stderr}` out
- Unknown phrase: error to HTML, no proxy call

---

### Task 1: Scaffold

**Files:** Create `requirements.txt`, `.gitignore`

- [ ] Write `requirements.txt`:

```
fastapi
uvicorn
websockets
```

- [ ] Write `.gitignore`: `venv/`, `.venv/`, `__pycache__/`, `*.pyc`, `.DS_Store`
- [ ] Commit: `Add linux_emulator scaffold.`

---

### Task 2: Local proxy (the only process that execs)

**Files:** Create `proxy_server.py`

- [ ] Write `proxy_server.py` as specified below (FastAPI WS `/ws` on port 8091).
- [ ] Commit: `Add local proxy that runs ls/touch/rm.`

```python
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
                await ws.send_text(json.dumps(
                    {"ok": False, "stdout": "", "stderr": "bad json"}
                ))
                continue
            result = run_op(str(msg.get("op") or ""), str(msg.get("path") or ""))
            await ws.send_text(json.dumps(result))
    except WebSocketDisconnect:
        return
```

---

### Task 3: Remote (parse + forward, no exec) and UI

**Files:** Create `remote_server.py`, `ui.html`

- [ ] Write both files as specified below.
- [ ] Commit: `Add remote parser and HTML client.`

`remote_server.py` must not import `subprocess`.

Parser prefixes (anchored, case-insensitive): `list all files in `, `add file `, `remove file `.

---

### Task 4: README and manual check

**Files:** Create `README.md`

- [ ] Write run instructions (proxy :8091 first, then remote :8090, open http://localhost:8090).
- [ ] Verify: `GET /` 200; phrase `list all files in ~/` returns stdout; `add file` / `remove file` on a temp path under home.
- [ ] Commit: `Add run instructions.`
