from metrics import Metrics, percentile


def test_percentile_empty():
    assert percentile([], 50) is None


def test_percentile_p50_p95():
    vals = [1, 2, 3, 4, 5]
    assert percentile(vals, 50) == 3
    assert percentile(vals, 95) == 5


def test_success_ratio_and_latency():
    m = Metrics()
    snap = m.snapshot(proxy_up=False)
    assert snap["success_ratio"] is None
    assert snap["proxy_up"] is False
    m.record_ok(10)
    m.record_ok(20)
    m.record_fail(100)
    snap = m.snapshot(proxy_up=True)
    assert snap["ok"] == 2
    assert snap["fail"] == 1
    assert snap["success_ratio"] == round(2 / 3, 4)
    assert snap["latency_ms"]["n"] == 3
    assert snap["latency_ms"]["p50"] is not None
    assert snap["latency_ms"]["p95"] is not None
