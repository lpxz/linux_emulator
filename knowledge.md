# Knowledge

## Ask vs connect (linux_emulator)

A asks B, B asks C. Who **opens** the socket is different from who **asks**.

| | Process | Role |
|---|---|---|
| **A** | browser + `ui.html` | Asks B |
| **B** | `remote_server.py` :8090 | Cloud hub. Never execs. Never dials C. |
| **C** | `proxy_server.py` | Local daemon. Dials B, then waits. Only process that execs. |

**Connect:** A dials `ws://127.0.0.1:8090/ws`. C dials `ws://127.0.0.1:8090/proxy`. Same host/port, different paths.

**Ask:** browser `{type:user}` → B parses → B sends `{argv}` on the socket **C already opened** → C `subprocess.run` → `{ok, stdout, stderr}` → B → browser `{type:result|error}`.

C is not in `ui.html`. `location.host` in the page is whatever served the HTML (8090).

Start **remote first**, then `python proxy_server.py`. If C is down, B returns `proxy unavailable`.

`serve_proxy_socket` does not connect; `websockets.connect(REMOTE_URL)` in `run_daemon` does. `async with` holds that client socket. `async for raw in ws` only ends when the socket dies; C never hangs up on purpose. Reconnect: 1s, 2s, 4s, … cap 30s; reset to 1s after a successful connect.

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
