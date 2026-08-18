"""Open N /ws clients and send echo hello. Watch http://127.0.0.1:8090/dashboard"""
import argparse
import asyncio
import json
import time

import websockets

URL = "ws://127.0.0.1:8090/ws"


async def worker(wid: int, n: int, stats: dict):
    async with websockets.connect(URL) as ws:
        for i in range(n):
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "user", "text": "echo hello"}))
            raw = await ws.recv()
            dt = time.perf_counter() - t0
            msg = json.loads(raw)
            stats["n"] += 1
            if msg.get("type") == "result":
                stats["ok"] += 1
            else:
                stats["fail"] += 1
            stats["ms"].append(dt * 1000)


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clients", type=int, default=20)
    p.add_argument("--requests", type=int, default=25)
    args = p.parse_args()
    stats = {"n": 0, "ok": 0, "fail": 0, "ms": []}
    t0 = time.perf_counter()
    await asyncio.gather(
        *[worker(i, args.requests, stats) for i in range(args.clients)]
    )
    elapsed = time.perf_counter() - t0
    print(
        f"clients={args.clients} each={args.requests} total={stats['n']} "
        f"ok={stats['ok']} fail={stats['fail']} "
        f"wall={elapsed:.2f}s ~{stats['n'] / elapsed:.0f} req/s"
    )
    print("open http://127.0.0.1:8090/dashboard")


if __name__ == "__main__":
    asyncio.run(main())
