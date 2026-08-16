# linux_emulator design

Date: 2026-08-16

## Goal

Mock a Cursor-style Cloud Agent on one laptop: a browser (machine A) talks to a remote service (machine B) that **cannot** run local tools; that service talks to a local proxy (machine C) that **can**. The remote translates three natural-language intents into structured ops; the proxy runs the matching Linux commands; results display in the HTML log.

This is a detour on purpose. The HTML could exec locally; we do not, so the three-hop shape matches A → cloud → laptop.

## Non-goals (v1)

- LLM translation
- Arbitrary shell / natural language beyond the three intents
- `rm -r`, directories as remove targets
- gRPC (phase 2: swap remote↔proxy only; HTML unchanged)
- Auth, multi-user, persistence

## Processes (one machine)

| Process | Mock of | Port | May exec? |
| --- | --- | --- | --- |
| Browser + `ui.html` | Machine A | — | No |
| `remote_server.py` | Cloud agent (B) | HTTP+WS **8090** | **No** (`subprocess` / `os.system` / file write forbidden) |
| `proxy_server.py` | Local proxy (C) | WS **8091** | **Yes**, argv only |

Remote connects **outbound** to `ws://127.0.0.1:8091` so the proxy does not need to know about the remote. Start **proxy first**, then remote, then open http://localhost:8090.

## Files

- `ui.html` — text box, Send, log
- `remote_server.py` — `GET /` serves UI; `WS /ws` from browser; client WS to proxy
- `proxy_server.py` — `WS /ws`; runs commands
- `requirements.txt` — fastapi, uvicorn, websockets
- `README.md` — how to run and the three validation phrases

## Protocols

Browser → remote (`:8090/ws`):

```json
{"type": "user", "text": "list all files in ~/"}
```

Remote → browser:

```json
{"type": "result", "text": "<stdout or combined output>"}
{"type": "error", "text": "<reason>"}
```

Remote → proxy (`:8091/ws`):

```json
{"op": "list", "path": "/Users/you"}
{"op": "create", "path": "/Users/you/test1.txt"}
{"op": "remove", "path": "/Users/you/test.txt"}
```

Proxy → remote:

```json
{"ok": true, "stdout": "...", "stderr": ""}
{"ok": false, "stdout": "", "stderr": "..."}
```

## Parser (remote only)

Deterministic, case-insensitive. Path is the remainder after the prefix; strip quotes; expand leading `~` to the home directory **as a string** (remote may read `Path.home()` for expansion only — that is not executing a tool).

| Intent | Phrase | `op` | Proxy argv |
| --- | --- | --- | --- |
| list | `list all files in <path>` | `list` | `ls -la <path>` |
| add | `add file <path>` | `create` | `touch <path>` |
| remove | `remove file <path>` | `remove` | `rm -f <path>` |

Unknown phrase → `error` to HTML, **no** proxy call.

Empty path → `error`, no proxy call.

Paths may be `~`, `~/`, `~/foo`, or any absolute path the user typed (v1 does not sandbox).

## Proxy execution

- `subprocess.run(argv, capture_output=True, text=True, timeout=10)`
- **Never** `shell=True`
- `list` / `create` / `remove` only; unknown `op` → `ok: false`
- `touch` creates an empty file (and parent dirs are **not** auto-created; missing parent → stderr)
- `rm -f` is file-only (no `-r`)

## UI

Plain page: input, Send, Enter to send. Log lines: `you:` / `result:` / `error:`.

## Validation (manual)

1. `list all files in ~/` → listing appears in the HTML log  
2. `add file ~/test1.txt` → file exists  
3. `remove file ~/test.txt` → file gone (create it first if needed)

## Phase 2 (not v1)

Replace remote↔proxy WebSocket with gRPC. Browser protocol unchanged.

## Success

Three processes, two WebSocket hops, remote has no exec, the three phrases work, README explains how to run.
