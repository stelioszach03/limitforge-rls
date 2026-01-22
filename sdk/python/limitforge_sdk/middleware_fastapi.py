from typing import Callable, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .client import LimitforgeClient, RateLimitedError


def default_mapper(request: Request) -> Tuple[str, str]:
    resource = f"{request.method}:{request.url.path}"
    subj = (
        request.headers.get("X-Client-Id")
        or request.headers.get("X-API-Key")
        or "anonymous"
    )
    return resource, subj


class LimitforgeMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        base_url: str,
        api_key: str,
        *,
        mapper: Callable[[Request], Tuple[str, str]] = default_mapper,
        cost: int = 1,
        timeout: float = 1.0,
    ):
        super().__init__(app)
        self.client = LimitforgeClient(base_url, api_key, timeout=timeout)
        self.mapper = mapper
        self.cost = cost

    async def dispatch(self, request: Request, call_next):
        try:
            resource, subject = self.mapper(request)
            await self.client.check(resource=resource, subject=subject, cost=self.cost)
        except RateLimitedError as e:
            headers = e.headers.copy()
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limited", "retry_after_ms": e.retry_after_ms},
                headers=headers,
            )
        except Exception:
            return JSONResponse(
                status_code=503, content={"detail": "rate limit service unavailable"}
            )
        return await call_next(request)
