# Metrics dashboard

Date: 2026-08-17

Simple `/dashboard` on remote :8090 (no Grafana). In-memory on B. Poll `GET /metrics`.

## JSON `GET /metrics`

- `ws_clients` — open `/ws` connections
- `proxy_up` — C held socket present
- `ok`, `fail` — replies to A (`result` vs `error`)
- `success_ratio` — `ok / (ok+fail)` or `null` if none
- `latency_ms` — `{p50, p95, last, n}` over last 500 B→C round-trips (parse errors omitted)

## `GET /dashboard`

HTML polls `/metrics` every 1s.

## Load

`python loadtest.py` — N `/ws` clients, each sends `echo hello` in a loop. Watch `/dashboard`.
