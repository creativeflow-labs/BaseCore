from collections import deque
from threading import Lock
from time import time

from fastapi import Depends, Header, HTTPException, Request, status

from .settings import Settings, get_settings

_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}
_RATE_LIMIT_LOCK = Lock()


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.enable_auth:
        return
    if not settings.service_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="service_api_key is not configured",
        )
    if x_api_key != settings.service_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )


def enforce_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.rate_limit_enabled:
        return

    client_host = request.client.host if request.client else "unknown"
    now = time()
    window_start = now - settings.rate_limit_window_seconds

    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS.setdefault(client_host, deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
            )
        bucket.append(now)
