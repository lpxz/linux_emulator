"""In-memory metrics for remote_server (process lifetime)."""
from collections import deque

WINDOW = 500


def percentile(sorted_vals, p: float):
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return round(sorted_vals[0], 3)
    idx = int(round((p / 100.0) * (n - 1)))
    idx = min(n - 1, max(0, idx))
    return round(sorted_vals[idx], 3)


class Metrics:
    def __init__(self):
        self.ws_clients = 0
        self.ok = 0
        self.fail = 0
        self.last_ms = None
        self._lat = deque(maxlen=WINDOW)

    def reset(self):
        self.__init__()

    def record_ok(self, ms: float):
        self.ok += 1
        self._observe(ms)

    def record_fail(self, ms=None):
        self.fail += 1
        if ms is not None:
            self._observe(ms)

    def _observe(self, ms: float):
        self.last_ms = round(ms, 3)
        self._lat.append(ms)

    def snapshot(self, proxy_up: bool) -> dict:
        total = self.ok + self.fail
        lats = sorted(self._lat)
        return {
            "ws_clients": self.ws_clients,
            "proxy_up": proxy_up,
            "ok": self.ok,
            "fail": self.fail,
            "success_ratio": round(self.ok / total, 4) if total else None,
            "latency_ms": {
                "last": self.last_ms,
                "p50": percentile(lats, 50),
                "p95": percentile(lats, 95),
                "n": len(lats),
            },
        }


METRICS = Metrics()
