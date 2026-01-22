import httpx
from typing import Dict, Any


class RateLimitedError(Exception):
    def __init__(
        self,
        message: str,
        *,
        retry_after_ms: int | None = None,
        headers: Dict[str, str] | None = None,
        payload: Dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.retry_after_ms = retry_after_ms
        self.headers = headers or {}
        self.payload = payload or {}


class LimitforgeClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-API-Key": api_key},
        )

    async def close(self):
        await self._client.aclose()

    async def check(
        self, *, resource: str, subject: str, cost: int = 1
    ) -> Dict[str, Any]:
        payload = {"resource": resource, "subject": subject, "cost": cost}
        r = await self._client.post("/v1/check", json=payload)
        # Accept 200 and 429 with body
        if r.status_code not in (200, 429):
            r.raise_for_status()
        data = r.json()
        if not data.get("allowed", False):
            # Prefer JSON retry_after_ms, fallback to header seconds
            retry_ms = data.get("retry_after_ms")
            if retry_ms is None:
                try:
                    retry_s = int(r.headers.get("Retry-After", "0"))
                except ValueError:
                    retry_s = 0
                retry_ms = retry_s * 1000
            raise RateLimitedError(
                "rate_limited",
                retry_after_ms=retry_ms,
                headers={
                    k: v
                    for k, v in r.headers.items()
                    if k.lower().startswith("x-ratelimit") or k.lower() == "retry-after"
                },
                payload=data,
            )
        return data
