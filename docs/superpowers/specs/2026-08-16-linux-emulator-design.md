# linux_emulator design

Date: 2026-08-16

## Goal

Mock a Cursor-style Cloud Agent on one laptop: a browser (machine A) talks to a remote service (machine B) that **cannot** run local tools; that service talks to a local proxy (machine C) that **can**. The remote accepts common Linux command lines (and three English aliases) and forwards argv to the proxy; results display in the HTML log.

This is a detour on purpose. The HTML could exec locally; we do not, so the three-hop shape matches A → cloud → laptop.

## Non-goals

- LLM translation
- A real shell: no pipes, redirects, `;`, `&`, backticks, `$`
- `rm -r` / `rm -rf`
- Interpreters and network tools (`bash`, `sh`, `python`, `curl`, `ssh`, …)
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
- `allowed_cmds.py` — shared allowlist (remote refuses before any proxy call)
- `requirements.txt` — fastapi, uvicorn, websockets
- `README.md` — how to run and example commands

## Protocols

Browser → remote (`:8090/ws`):

```json
{"type": "user", "text": "ls -la ~/"}
```

Remote → browser:

```json
{"type": "result", "text": "<stdout or combined output>"}
{"type": "error", "text": "<reason>"}
```

Remote → proxy (`:8091/ws`):

```json
{"argv": ["ls", "-la", "/Users/you"]}
```

Legacy `{op, path}` (`list` / `create` / `remove`) is still accepted by the proxy.

Proxy → remote:

```json
{"ok": true, "stdout": "...", "stderr": ""}
{"ok": false, "stdout": "", "stderr": "..."}
```

## Parser (remote only)

1. English aliases (case-insensitive prefixes) still map to argv:
   - `list all files in <path>` → `ls -la <path>`
   - `add file <path>` → `touch <path>`
   - `remove file <path>` → `rm -f <path>`
2. Otherwise `shlex.split` the line. First token must be in `ALLOWED`. Expand leading `~` / `~/` on each arg as a **string** (`Path.home()` only).
3. Shell metacharacters, unknown commands, empty path, or `rm -r` → `error` to HTML, **no** proxy call.

## Allowed commands

`ls`, `cat`, `head`, `tail`, `touch`, `mkdir`, `rmdir`, `rm`, `cp`, `mv`, `ln`, `readlink`, `stat`, `file`, `chmod`, `realpath`, `dirname`, `basename`, `pwd`, `echo`, `printf`, `grep`, `sort`, `uniq`, `cut`, `tr`, `wc`, `diff`, `date`, `uname`, `hostname`, `whoami`, `id`, `df`, `du`, `which`, `env`, `printenv`, `true`, `false`, `sleep`, `cal`, `md5`, `shasum`, `find`.

`mkdir -p` is a flag, not a shell feature — allowed. `echo hello > file` is a redirect — refused.

## Proxy execution

- `subprocess.run(argv, capture_output=True, text=True, timeout=10)`
- **Never** `shell=True`
- First argv token must be in `ALLOWED`; unknown → `ok: false`
- `rm` with `-r` / `-rf` / `--recursive` → `ok: false`

## UI

Plain page: input, Send, Enter to send. Log lines: `you:` / `result:` / `error:`.

## Validation (manual)

1. `ls -la ~/` → listing appears in the HTML log
2. `mkdir ~/linux_emulator_dir` → directory exists
3. `touch ~/test1.txt` → file exists
4. `list all files in ~/` still works
5. `rm -rf /` and `echo hi > ~/x` → error, no proxy call

## Phase 2 (not this change)

Replace remote↔proxy WebSocket with gRPC. Browser protocol unchanged.

## Success

Three processes, two WebSocket hops, remote has no exec, allowlisted commands work, English aliases still work, README explains how to run.
