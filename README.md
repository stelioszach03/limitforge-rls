![CI](https://github.com/stelioszach03/limitforge-rls/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-informational)

# LimitForge RLS

A tenant-aware **rate-limit service** for APIs. Four algorithms —
**token bucket**, **fixed window**, **sliding window**, **concurrency** —
each compiled into a Redis Lua script so the decision, the header set, and
the ledger update are indivisible. Plans and keys live in Postgres;
decisions burn through Redis.

> A rate limiter is a contract, not a barrier — it tells the client exactly
> how to behave.

---

## Live demo

| What | URL |
| --- | --- |
| Editorial landing with live burst-test widget | <https://stelioszach.com/limitforge-rls/> |
| OpenAPI / Swagger docs | <https://stelioszach.com/limitforge-rls/docs> |
| Health | <https://stelioszach.com/limitforge-rls/v1/health> |
| Prometheus metrics | <https://stelioszach.com/limitforge-rls/metrics/> |

Fire a 15-call burst at the token-bucket plan on the live service:

```bash
KEY=6fIqNQtZcyRHc49GAHEaX5tk5lw3Ewb9OEm1pqwMyIo            # public demo key
PLAN=197a7f69-3cea-4329-a8c7-512e9617c2aa                   # demo-bucket (cap 10, refill 2/s)

for i in $(seq 1 15); do
  curl -sS -X POST https://stelioszach.com/limitforge-rls/v1/check \
    -H "x-api-key: $KEY" -H "content-type: application/json" \
    -d "{\"resource\":\"GET:/demo\",\"subject\":\"me-$$\",\"cost\":1,\"plan_id\":\"$PLAN\"}" &
done | wait
```

Expect ~10 `allowed=true` followed by 429s with non-zero `retry_after_ms`.

---

## Why

- Centralise throttling policy across many API fleets.
- Give consumers a **precise contract** (`X-RateLimit-*`, `Retry-After`) so
  they can back off correctly.
- Stop abuse and brownouts before they reach the origin.
- Pick the right algorithm per endpoint — not one-size-fits-all.

---

## Algorithms

| Family | When to reach for it | Backing store | Notes |
| --- | --- | --- | --- |
| `token_bucket` | Smooth rate limiting that tolerates small bursts | Redis + Lua | Default; refill continuous, cap `C`, rate `r`. |
| `fixed_window` | Cheapest per-call check; strong upper bound | Redis `INCR` + `EXPIRE` | Edge-burst prone at window boundaries. |
| `sliding_window` | Smoother than fixed, no boundary effect | Redis sorted set | O(k) memory per active subject. |
| `concurrency` | Cap *in-flight* calls, not rate | Redis sorted set | Useful for expensive endpoints. |

All four return the same decision contract:

```json
{
  "allowed": true,
  "remaining": 9,
  "limit": 10,
  "reset_at": 1776376469,
  "retry_after_ms": 0,
  "algorithm": "token_bucket",
  "headers": {
    "X-RateLimit-Limit": "10",
    "X-RateLimit-Remaining": "9",
    "X-RateLimit-Reset": "1776376469",
    "Retry-After": "0"
  }
}
```

---

## Architecture

```
  client  ── POST /v1/check ──▶  nginx  ──▶  FastAPI (app.api.v1)
                                             │
                                             ▼
                     x-api-key verify (Redis first, Postgres fallback)
                                             │
                                             ▼
                     resolve Plan (cache hit → Redis, miss → Postgres + fill)
                                             │
                                             ▼
                            DecisionEngine.check(plan)  → Lua
                                             │
                            decision + headers + Prometheus + structlog
```

- **Hot path** — `POST /v1/check` hits Postgres only on a cold tenant/plan;
  every subsequent decision is one Redis round-trip.
- **Atomicity** — each algorithm is a Lua script, so the read-modify-write
  executes inside Redis's single-threaded core.
- **Subject granularity** — any string; typically `user:<id>`,
  `api-key:<hash>`, or the request IP.

---

## Quickstart

### Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
# API        → http://localhost:8000
# Docs       → http://localhost:8000/docs
# Metrics    → http://localhost:8000/metrics
```

### Local (venv)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export POSTGRES_DSN="postgresql+psycopg://postgres:postgres@localhost:5432/limitforge"
export REDIS_URL="redis://localhost:6379/0"
export ADMIN_BEARER_TOKEN="change-me"
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Provisioning a tenant (admin APIs)

All `/v1/admin/*` endpoints require `Authorization: Bearer $ADMIN_BEARER_TOKEN`.

```bash
export ADMIN=change-me

# 1. Create a tenant
TENANT=$(curl -sS -X POST http://localhost:8000/v1/admin/tenants \
  -H "Authorization: Bearer $ADMIN" -H "content-type: application/json" \
  -d '{"name":"Acme"}' | jq -r .id)

# 2. Create a plan
PLAN=$(curl -sS -X POST http://localhost:8000/v1/admin/plans \
  -H "Authorization: Bearer $ADMIN" -H "content-type: application/json" \
  -d "{\"tenant_id\":\"$TENANT\",\"name\":\"pro\",\"algorithm\":\"token_bucket\",
       \"bucket_capacity\":100,\"refill_rate_per_sec\":20}" | jq -r .id)

# 3. Mint an API key (raw key returned ONCE)
KEY=$(curl -sS -X POST http://localhost:8000/v1/admin/keys \
  -H "Authorization: Bearer $ADMIN" -H "content-type: application/json" \
  -d "{\"tenant_id\":\"$TENANT\",\"name\":\"prod\"}" | jq -r .key)

# 4. (Optional) pin a plan to a resource
curl -sS -X POST http://localhost:8000/v1/admin/policies \
  -H "Authorization: Bearer $ADMIN" -H "content-type: application/json" \
  -d "{\"tenant_id\":\"$TENANT\",\"resource\":\"GET:/orders\",
       \"subject_type\":\"api_key\",\"plan_id\":\"$PLAN\"}"

# 5. Make a decision
curl -i -X POST http://localhost:8000/v1/check \
  -H "x-api-key: $KEY" -H "content-type: application/json" \
  -d '{"resource":"GET:/orders","subject":"user:1","cost":1}'
```

---

## API surface

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/v1/check` | `x-api-key` | The hot path — makes one decision. |
| `GET`  | `/v1/health` | — | Liveness + version. |
| `GET`  | `/metrics` | — | Prometheus scrape target. |
| `POST` | `/v1/admin/tenants` | Bearer | Create a tenant. |
| `POST` | `/v1/admin/plans`   | Bearer | Create a plan (algorithm + parameters). |
| `POST` | `/v1/admin/keys`    | Bearer | Mint an API key for a tenant. |
| `POST` | `/v1/admin/policies` | Bearer | Pin a plan to a resource / subject_type. |
| `GET`  | `/v1/admin/tenants/{id}/summary` | Bearer | Tenant object counts. |

Machine-readable spec: <https://stelioszach.com/limitforge-rls/openapi.json>.

---

## Response headers

Every `200` and `429` carry the following, so clients don't have to query the
plan to behave correctly:

- `X-RateLimit-Limit` — total budget for the window / bucket / concurrency.
- `X-RateLimit-Remaining` — units left right now.
- `X-RateLimit-Reset` — unix-seconds when the budget fully resets.
- `Retry-After` — seconds to wait before retrying (only on `429`).

---

## SDKs

- **Python** — `pip install limitforge-sdk` — see `sdk/python/` for a thin
  client and a ready-to-drop FastAPI middleware.
- **Node** — `npm install limitforge-sdk` — see `sdk/node/` for a client and
  Express middleware.

---

## Testing

```bash
pytest -q --cov=app --cov-branch --cov-report=term-missing
```

CI runs on every push with a live Postgres 16 + Redis 7 service and a
90% coverage gate. Ruff + Black gate lint and formatting.

---

## Observability

- **Metrics** — `rl_allowed_total`, `rl_blocked_total`, plus a
  `requests_total{route,outcome}` counter for every route.
- **Logs** — JSON lines via `structlog`; each decision logs
  `algorithm`, `tenant`, `subject_hash`, `outcome`.
- **Traces** — OTEL auto-instrumentation on FastAPI, SQLAlchemy, Redis.
  Export to any OTLP collector via `OTEL_EXPORTER_OTLP_ENDPOINT`.

---

## Roadmap

- Consistent hashing / shard keys across a Redis cluster.
- Multi-region replication with drift controls.
- Redis Streams for an audit / eventing topic.
- gRPC data-plane and a sidecar pattern for per-pod deployment.
- Envoy / NGINX filter so enforcement can happen at the edge.

---

## License

MIT — see [LICENSE](LICENSE).

---

Built in Athens by **Stelios Zacharioudakis** · <sdi2200243@di.uoa.gr> ·
[stelioszach.com](https://stelioszach.com)
