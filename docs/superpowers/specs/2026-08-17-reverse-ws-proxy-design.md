# Reverse WebSocket: C dials B, B asks C

Date: 2026-08-17

## Goal

Invert **who opens** the remote↔proxy socket so it matches a cloud agent: the local proxy (C) is a daemon that **connects out** to the remote (B). After that socket exists, **B uses it** to ask C for tool calls / local data. Ask direction stays **A → B → C**.

`ui.html` is unchanged. The proxy is **not** in the browser.

## Ask vs connect

| | Who | Meaning |
|---|---|---|
| **Ask** | A asks B, B asks C | Request for data / argv |
| **Connect** | A dials B (`/ws`); C dials B (`/proxy`) | Who opens the WebSocket |

B never dials C. A never talks to C.

## Processes

| | Process | Role | Listens? | Exec? |
|---|---|---|---|---|
| **A** | browser + `ui.html` | Asks B | No | No |
| **B** | `remote_server.py` | Cloud hub | HTTP+WS **:8090** | **No** |
| **C** | `proxy_server.py` | Local daemon | **No** (client) | **Yes**, argv only |

Start **remote first**, then the proxy daemon, then open http://localhost:8090.

## Files

- `remote_server.py` — keep `GET /` and browser `WS /ws`. Add `WS /proxy` for C. Hold **one** proxy connection (a new C replaces the previous). `call_proxy` **sends** `{argv}` on that socket and waits for `{ok, stdout, stderr}` instead of `websockets.connect` to :8091. Serialize with a lock so two browser messages cannot interleave on that socket.
- `proxy_server.py` — stop serving FastAPI/WS. Connect to `ws://127.0.0.1:8090/proxy`, loop: recv → `run_argv` / `run_op` → send result. Reconnect if B restarts.
- `ui.html` — `GET /` page; browser WS to `/ws`; reconnects on close
- `allowed_cmds.py` — no change.
- `README.md` / `.cursor/agents/coding.md` / `2026-08-16-linux-emulator-design.md` — start order and who listens.

## Protocols (JSON unchanged)

Browser → B (`:8090/ws`): `{"type":"user","text":"..."}`  
B → browser: `{"type":"result","text":"..."}` or `{"type":"error","text":"..."}`  
B → C (on the socket **C opened**): `{"argv":["ls","-la","..."]}`  
C → B: `{"ok":true,"stdout":"...","stderr":""}`

Legacy `{op, path}` still accepted by C. One in-flight argv at a time (serialize). Parser, allowlist, `rm -r`, and no-`subprocess` on B are unchanged.

## Errors

- No proxy connected, or `/proxy` drops mid-call → browser `{"type":"error","text":"proxy is down"}`. B clears the held socket.
- C reconnects to B with exponential backoff (1s, 2s, 4s, … 30s), logs `connected` / `connect failed` / `reconnect in Ns`. Delay resets after a successful connect.
- B process death closes A’s `/ws`. `ui.html` reconnects (1s … 8s) and shows `disconnected; retrying…` then `connected`. Send while not open → `not connected`.
- Bad parse / unknown / shell meta / `rm -r` → error to A, **no** message to C.

## Validation

Same command checks as the 2026-08-16 spec, plus: with remote up and proxy down, a valid `ls` yields `proxy is down` (not a hang). After proxy connects, `ls -la ~/` works.

## Non-goals

Request ids / concurrent tool calls, gRPC, auth, putting the proxy in `ui.html`.

## Success

Three processes; C is a local daemon that dials B; B asks C on that WS; A still only talks to B; remote still has no exec.
