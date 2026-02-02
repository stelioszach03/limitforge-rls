import pytest
from app.rl.engine import DecisionEngine
from app.rl.schemas import CheckDecision


def test_engine_headers_static():
    d = CheckDecision(
        allowed=True,
        remaining=1,
        limit=2,
        reset_at=0,
        retry_after_ms=0,
        algorithm="token_bucket",
        headers={"X-RateLimit-Limit": "2"},
    )
    h = DecisionEngine.headers(d)
    assert h["X-RateLimit-Limit"] == "2"

