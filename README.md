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

# terminal 2 — local daemon (C); connects to :8090/proxy
python proxy_server.py
```

Open http://localhost:8090

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
