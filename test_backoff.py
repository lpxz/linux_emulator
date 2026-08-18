from proxy_server import BACKOFF_CAP, BACKOFF_INITIAL, next_backoff


def test_backoff_doubles_then_caps():
    d = BACKOFF_INITIAL
    seq = []
    for _ in range(8):
        d = next_backoff(d)
        seq.append(d)
    assert seq[0] == BACKOFF_INITIAL * 2
    assert seq[-1] == BACKOFF_CAP
    assert seq == sorted(seq)
    assert all(x <= BACKOFF_CAP for x in seq)
