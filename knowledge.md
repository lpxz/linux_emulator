# Knowledge

## Ask vs connect (linux_emulator)

A asks B, B asks C. Who **opens** the socket is different from who **asks**.

| | Process | Role |
|---|---|---|
| **A** | browser + `ui.html` | Asks B |
| **B** | `remote_server.py` :8090 | Cloud hub. Never execs. Never dials C. |
| **C** | `proxy_server.py` | Local daemon. Dials B, then waits. Only process that execs. |

**Connect:** A dials `ws://127.0.0.1:8090/ws` (no JWT). C dials `ws://127.0.0.1:8090/proxy?token=…`. Same host/port, different paths. B verifies C’s HS256 JWT (`sub` must be `DAEMON_ID`, signature uses `DAEMON_JWT_SECRET`). Defaults `local-1` / `linux-emulator-dev-secret-key-32b`. Do not log the token URL.

**Ask:** browser `{type:user}` → B parses → B sends `{argv}` on the socket **C already opened** → C `subprocess.run` → `{ok, stdout, stderr}` → B → browser `{type:result|error}`.

C is not in `ui.html`. `location.host` in the page is whatever served the HTML (8090).

Start **remote first**, then `python proxy_server.py`. If C is down, B returns `proxy is down`.

`serve_proxy_socket` does not connect; `websockets.connect(proxy_ws_url(REMOTE_URL))` in `run_daemon` does (JWT query param). `async with` holds that client socket. `async for raw in ws` only ends when the socket dies; C never hangs up on purpose.

## Failure handling

Two independent sockets. Killing B does not kill C’s process; killing C does not close the browser’s `/ws` until B notices C is gone on the next ask.

**C (proxy daemon)** — reconnect with exponential backoff (1s, 2s, 4s, … cap 30s). Successful connect resets to 1s. Logs:

- `connected to ws://127.0.0.1:8090/proxy`
- `socket closed by remote` or `connect failed: …`
- `reconnect in Ns`

**B → A** — if no proxy is held, or the `/proxy` socket drops mid-call: `{"type":"error","text":"proxy is down"}`.

**A (browser)** — `/ws` is created on page load. If B dies, that socket dies too; sending on it does nothing useful. `ui.html` reconnects on `close` (1s, 2s, 4s, … cap 8s), shows `disconnected; retrying…`, then `connected`. Send while not `OPEN` → `not connected`. After B restarts, wait for `connected` before sending (hard-refresh once if the tab still has the old script).

### Demo

`source venv/bin/activate` in each terminal (or use `./venv/bin/...`).

1. Terminal 1: `uvicorn remote_server:app --port 8090 --reload`
2. Terminal 2: `python proxy_server.py` — expect `connected to …`
3. Open http://localhost:8090, wait for `connected`, `echo hello`
4. Kill terminal 1. Terminal 2 logs backoff. Page: `disconnected; retrying…`. Bring terminal 1 back. Terminal 2: `connected to …`. Page: `connected`. Send again.
5. Kill terminal 2. Send `echo hello` → `error: proxy is down`. Start terminal 2 again, then send works.

## Metrics dashboard

No Grafana. B keeps in-memory counters (`metrics.py`), reset when remote restarts.

- http://127.0.0.1:8090/dashboard — polls `GET /metrics` every 1s
- Fields: `success_ratio` (`ok/(ok+fail)`), `latency_ms.p50` / `p95` / `last` (last 500 B→C round-trips), `ok` / `fail`, `ws_clients`, `proxy_up`
- Parse errors count as `fail` with no latency. Proxy round-trips (ok or fail) record ms.

Load (remote + proxy already up):

```bash
python loadtest.py --clients 20 --requests 25
```

Example: 500 ok, 0 fail, p50 ~40ms (B serializes asks on one C socket). Watch the dashboard while it runs.

## Daemon JWT

C, not the browser. HS256. Same `DAEMON_JWT_SECRET` and `DAEMON_ID` on B and C (defaults `linux-emulator-dev-secret-key-32b` / `local-1`). C mints `sub`+`exp` on each connect. B checks signature, expiry, and `sub == DAEMON_ID`. Missing/wrong token → close 1008; never becomes the held `/proxy` socket. Do not log `?token=`.

## Git worktrees

If Cursor has no `/worktree` support, this is enough.

### Minimal commands

```bash
git worktree add -b newbranch ~/new_root
git worktree list
git worktree remove ~/new_root
```

From the **main folder**, after you have committed on `newbranch`:

```bash
git merge newbranch
```

There is no `git worktree merge`. Merge is normal `git merge` of a **branch**, run in the folder you want the files to land in.

### What `add -b` does

```bash
git worktree add -b feat/foo ~/.cursor/worktrees/linux_emulator/feat-foo
```

One command, two effects:

1. Create branch `feat/foo` (from current `HEAD` unless you pass a third argument).
2. Create a second working folder at that path and check `feat/foo` out **there**.

This folder stays on its current branch. Same repo (shared `.git` data), different directory, different branch. The path is just a folder; `~/.cursor/worktrees/...` is Cursor’s usual place, not a git rule.

`git switch` only changes which branch **this** folder is on. It does not `cd` to the other checkout.

### Constraints

- The same branch cannot be checked out in two worktrees at once. Merge from the main folder while the extra checkout still exists; do not `git switch newbranch` here until the extra folder is gone.
- `remove` deletes the extra folder, not the branch.
- `merge` only sees **commits**. Uncommitted edits in `~/new_root` will not come along.

### Cursor Agents Window

`/worktree` autocomplete is classic IDE Agent chat, not Agents Window. In Agents Window: **New Chat** + **New Worktree**. One window can hold many agents; each worktree chat is its own checkout. Chat history does not copy into a new chat.
