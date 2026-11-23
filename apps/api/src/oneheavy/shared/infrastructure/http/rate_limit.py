"""Rate limiting en memoria (ventana deslizante) — protege login contra fuerza bruta.

Para múltiples réplicas reemplazar por un backend Redis manteniendo la interfaz.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container

_UNITS = {"second": 1, "minute": 60, "hour": 3600}


def parse_rate(rate: str) -> tuple[int, int]:
    """'5/minute' → (5, 60)."""
    count, unit = rate.split("/")
    return int(count), _UNITS[unit.strip().rstrip("s")]


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def rate_limited(scope: str) -> Callable[..., Coroutine[Any, Any, None]]:
    async def _dep(request: Request, container: Container = Depends(get_container)) -> None:
        limiter: SlidingWindowLimiter = container.extras.setdefault("http.limiter", SlidingWindowLimiter())
        limit, window = parse_rate(container.settings.login_rate_limit)
        client = request.client.host if request.client else "unknown"
        if not limiter.hit(f"{scope}:{client}", limit, window):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Demasiados intentos, espera un momento")

    return _dep
