# linux_emulator

Mock of a cloud agent on one laptop: HTML (machine A) → remote (machine B, no exec) → local proxy (machine C, runs commands).

## Run

Two terminals. **Proxy first.**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# terminal 1
uvicorn proxy_server:app --port 8091 --reload

# terminal 2
uvicorn remote_server:app --port 8090 --reload
```

Open http://localhost:8090

## Try

- `list all files in ~/`
- `add file ~/test1.txt`
- `remove file ~/test.txt` (create it first if it is not there)

Unknown phrases never reach the proxy.
