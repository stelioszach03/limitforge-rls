# LimitForge RLS

Tenant-aware rate-limit service with four algorithms — token bucket, fixed window, sliding window, concurrency — backed by Redis, with plans and API keys in Postgres.

[![CI](https://github.com/stelioszach03/limitforge-rls/actions/workflows/ci.yml/badge.svg)](https://github.com/stelioszach03/limitforge-rls/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square)](LICENSE)

## Results

| Measure | Value | Evidence |
|---|---|---|
| Line coverage | 92.57% (536 / 579) | [`coverage.xml`](coverage.xml) |
| Branch coverage | 79.55% (70 / 88) | [`coverage.xml`](coverage.xml) |
| CI gate | fails below 90% line | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — `--cov-fail-under=90` |
| Algorithms implemented | 4 | [`app/rl/strategies/`](app/rl/strategies/) |
| Implemented as an atomic Lua script | 2 of 4 — token bucket, fixed window | [`app/rl/scripts/`](app/rl/scripts/) |

CI runs on every push against a live Postgres 16 and Redis 7. **No throughput number is claimed**; the service has not been load-tested in this repo.

All four algorithms return the same contract: `{allowed, remaining, limit, reset_at, retry_after_ms, algorithm, headers}`, with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` and `Retry-After` set on every 200 and 429, so a client never has to query the plan to back off correctly.

## Run

```bash
cp .env.example .env
docker compose up --build          # API :8000, docs /docs, metrics /metrics
```

Local venv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export POSTGRES_DSN="postgresql+psycopg://postgres:postgres@localhost:5432/limitforge"
export REDIS_URL="redis://localhost:6379/0" ADMIN_BEARER_TOKEN="change-me"
alembic upgrade head && uvicorn app.main:app --reload

pytest -q --cov=app --cov-branch --cov-report=term-missing
```

`POST /v1/check` is the hot path. Provisioning goes through `POST /v1/admin/{tenants,plans,keys,policies}`, all requiring `Authorization: Bearer $ADMIN_BEARER_TOKEN`; a minted API key is returned exactly once. Python and Node SDKs live in `sdk/` and install from source — **neither is published to PyPI or npm**.

## Limitations

- **Only token bucket and fixed window are atomic Lua scripts.** `concurrency` is a single `INCRBY`; `sliding_window` does a `ZREMRANGEBYSCORE` followed by a separate pipelined `ZADD`, so its read-modify-write is **not** atomic and concurrent callers can overshoot the limit.
- **Not one round-trip per decision for every algorithm** — sliding window issues several Redis commands per check.
- **Single Redis instance.** No cluster mode, no consistent hashing; a Redis failover drops the decision path.
- **Coverage is line and branch, not correctness.** The Lua scripts run against a real Redis in CI, but there is no adversarial concurrency or fault-injection suite — which is exactly where the sliding-window race above would show up.
- **No published throughput benchmark.** No req/s figure is claimed.
- **Clock trust.** Sliding-window and concurrency rely on Redis server time; heavy cross-region clock skew is out of scope.
- **Admin auth is a single static bearer token** — enough for a demo, not for multi-operator production.

## License

MIT — see [LICENSE](LICENSE).
