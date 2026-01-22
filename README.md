# Limitforge RLS — Rate Limiter as a Service (MVP)

Backend service that makes fast rate‑limit decisions with multiple algorithms, Redis‑backed state, and a minimal multi‑tenant admin API. Includes Prometheus metrics, optional OpenTelemetry tracing, and SDKs for Python/Node.

## Why
- Prevent abuse, bots, and DDoS on public APIs
- Enforce fair usage and protect shared resources
- Centralize throttling policies with low‑latency decisions

## Algorithms
- token_bucket: low latency, burstable; ideal for most endpoints
- fixed_window: simple window counters (atomic via Lua)
- sliding_window: smoother limits (MVP O(n) ZSET implementation)
- concurrency: in‑flight request cap (semaphore)

## Headers Contract
- X-RateLimit-Limit: integer, total limit for the window
- X-RateLimit-Remaining: integer, remaining budget
- X-RateLimit-Reset: unix seconds when budget resets
- Retry-After: seconds to wait before retry (429 only)

## Quickstart (Local venv)
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and set:
   - `POSTGRES_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/limitforge`
   - `REDIS_URL=redis://localhost:6379/0`
   - `ADMIN_BEARER_TOKEN=change-me`
4. `uvicorn app.main:app --reload`

## Quickstart (Docker Compose)
1. `cp .env.example .env` and set `POSTGRES_DSN=postgresql+psycopg://postgres:postgres@postgres:5432/limitforge`
2. `docker compose up --build`
3. App: http://localhost:8000

## Admin API (Bearer)
Create tenant:
```bash
curl -s -X POST http://localhost:8000/v1/admin/tenants \
  -H "Authorization: Bearer $ADMIN_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme"}'
```

Create plan:
```bash
curl -s -X POST http://localhost:8000/v1/admin/plans \
  -H "Authorization: Bearer $ADMIN_BEARER_TOKEN" -H "Content-Type: application/json" \
  -d '{"tenant_id":"<TENANT_UUID>","name":"basic","algorithm":"token_bucket","bucket_capacity":100,"refill_rate_per_sec":50}'
```

Create API key (returns raw key once):
```bash
curl -s -X POST http://localhost:8000/v1/admin/keys \
  -H "Authorization: Bearer $ADMIN_BEARER_TOKEN" -H "Content-Type: application/json" \
  -d '{"tenant_id":"<TENANT_UUID>","name":"k1"}'
```

Create policy:
```bash
curl -s -X POST http://localhost:8000/v1/admin/policies \
  -H "Authorization: Bearer $ADMIN_BEARER_TOKEN" -H "Content-Type: application/json" \
  -d '{"tenant_id":"<TENANT_UUID>","resource":"GET:/orders","subject_type":"api_key","plan_id":"<PLAN_UUID>"}'
```

## Decision API
```bash
curl -i -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: <RAW_API_KEY>" -H "Content-Type: application/json" \
  -d '{"resource":"GET:/orders","subject":"user:1","cost":1}'
```
Response includes headers X‑RateLimit‑* and Retry‑After when blocked (429).

## SDKs
- Python: `pip install limitforge-sdk`
  - See `sdk/python/README.md` for examples (client + FastAPI middleware)
- Node: `npm install limitforge-sdk`
  - See `sdk/node/README.md` (client + Express middleware)

## Metrics & Tracing
- Prometheus at `/metrics` (counters, histograms)
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to enable OTLP tracing; FastAPI is auto‑instrumented

## Roadmap
- Shard keys and consistent hashing for multi‑node Redis
- Multi‑region replication and drift controls
- Redis Streams for audit/eventing
- gRPC data‑plane API and sidecar
- Envoy/NGINX filters for edge enforcement
