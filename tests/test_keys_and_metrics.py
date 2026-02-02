from types import SimpleNamespace

from app.rl.keys import (
    bucket_key,
    window_key,
    concurrency_key,
    rl_key_token_bucket,
    rl_key_fixed_window,
    rl_key_sliding,
    rl_key_conc,
)
from app.observability.metrics import update_redis_pool_gauge


def test_key_helpers():
    assert bucket_key("ns", "sub", "tb:n") == "rl:ns:sub:tb:n"
    assert window_key("ns", "sub", 123) == "rl:ns:sub:win:123"
    assert concurrency_key("ns", "sub") == "rl:ns:sub:concurrent"
    assert rl_key_token_bucket("t", "s", "r") == "lf:tb:t:s:r"
    assert rl_key_fixed_window("t", "s", "r", 10) == "lf:fw:t:s:r:10"
    assert rl_key_sliding("t", "s", "r") == "lf:sw:t:s:r"
    assert rl_key_conc("t", "s", "r") == "lf:cc:t:s:r"


def test_update_redis_pool_gauge_graceful_no_pool():
    class R:
        pass

    update_redis_pool_gauge(R())  # should not raise


def test_update_redis_pool_gauge_counts_created_minus_available():
    pool = SimpleNamespace(_created_connections=[1, 2, 3], _available_connections=[1])
    r = SimpleNamespace(connection_pool=pool)
    update_redis_pool_gauge(r)  # should not raise

