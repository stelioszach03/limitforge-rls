# Limitforge Python SDK

Async client and FastAPI middleware for Limitforge RLS.

Install:
```bash
pip install limitforge-sdk
```

Client usage:
```python
import asyncio
from limitforge_sdk import LimitforgeClient, RateLimitedError

async def main():
    client = LimitforgeClient("http://localhost:8000", api_key="<raw-api-key>")
    try:
        decision = await client.check(resource="GET:/demo", subject="user:1", cost=1)
        print("allowed", decision)
    except RateLimitedError as e:
        print("blocked; retry after ms:", e.retry_after_ms)
    finally:
        await client.close()

asyncio.run(main())
```

FastAPI middleware:
```python
from fastapi import FastAPI, Request
from limitforge_sdk.middleware_fastapi import LimitforgeMiddleware, default_mapper

app = FastAPI()

def mapper(req: Request):
    # resource as METHOD:PATH, subject from custom header or api key
    resource = f"{req.method}:{req.url.path}"
    subject = req.headers.get("X-Client-Id") or req.headers.get("X-API-Key") or "anonymous"
    return resource, subject

app.add_middleware(
    LimitforgeMiddleware,
    base_url="http://localhost:8000",
    api_key="<raw-api-key>",
    mapper=mapper,
)
```
