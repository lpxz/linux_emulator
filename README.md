# linux_emulator

Mock of a cloud agent on one laptop: HTML (machine A) → remote (machine B, no exec) → local proxy (machine C, runs commands).

## Run

Two terminals. **Remote first** (so the local proxy has somewhere to dial).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# terminal 1 — cloud mock (B)
uvicorn remote_server:app --port 8090 --reload

# terminal 2 — local daemon (C); JWT on /proxy
python proxy_server.py
```

C proves it is the daemon B knows with an HS256 JWT (`sub` + `exp`). Set the same `DAEMON_JWT_SECRET` and `DAEMON_ID` on both processes (defaults `linux-emulator-dev-secret-key-32b` / `local-1` so the two-terminal demo works without extra env). Wrong secret or `sub` → B never holds the `/proxy` socket. Browser `/ws` stays unauthenticated.

Open http://localhost:8090 · metrics: http://localhost:8090/dashboard

Load (after both processes are up):

```bash
python loadtest.py --clients 20 --requests 25
```

## Try

Common Linux commands (argv only, no shell):

- `ls -la ~/`
- `mkdir ~/linux_emulator_dir`
- `touch ~/hi.txt`
- `cat ~/hi.txt`
- `echo hello`
- `pwd`

English phrases still work:

- `list all files in ~/`
- `add file ~/test1.txt`
- `remove file ~/test.txt`

Unknown commands, pipes, redirects, and `rm -r` never reach the proxy.

## Failure handling

C dials B and reconnects with backoff (1s → 30s). Watch terminal 2 for `connected` / `reconnect in Ns`.

If C is down, the page shows `error: proxy is down`.

If B is killed, the page’s `/ws` dies too. The UI reconnects (1s → 8s) and prints `disconnected; retrying…` then `connected`. Wait for `connected` before sending; a dead tab socket will not ride C’s reconnect.

Demo: kill terminal 1, watch C backoff, restart B, wait for both `connected` lines, send. Then kill terminal 2 and send → `proxy is down`.
