from collections import defaultdict
import hashlib
import logging
import time

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SensitiveRouteRateLimit(BaseHTTPMiddleware):
    """Use Redis for limits shared across workers, with an in-process development fallback."""
    def __init__(self, app, limit: int = 10, window_seconds: int = 60, redis_url: str | None = None):
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.hits = defaultdict(list)
        self.redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None

    async def dispatch(self, request, call_next):
        if request.url.path not in {"/api/auth/login", "/api/auth/register", "/api/auth/forgot-password", "/api/auth/reset-password"}:
            return await call_next(request)
        now = time.monotonic()
        client = request.client.host if request.client else "unknown"
        if self.redis:
            identity = hashlib.sha256(f"{client}:{request.url.path}".encode()).hexdigest()
            key = f"skilltrack:rate:{identity}"
            try:
                count, ttl = await self.redis.eval(
                    "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return {n,redis.call('TTL',KEYS[1])}",
                    1, key, self.window_seconds,
                )
                if count > self.limit:
                    return JSONResponse(status_code=429, content={"detail": "Too many attempts. Try again later."}, headers={"Retry-After": str(ttl)})
            except RedisError:
                logger.exception("Shared rate-limit store is unavailable")
                return JSONResponse(status_code=503, content={"detail": "Authentication service is temporarily unavailable"}, headers={"Retry-After": "10"})
            return await call_next(request)
        key = (client, request.url.path)
        recent = [hit for hit in self.hits[key] if now - hit < self.window_seconds]
        if len(recent) >= self.limit:
            self.hits[key] = recent
            return JSONResponse(status_code=429, content={"detail": "Too many attempts. Try again in a minute."}, headers={"Retry-After": str(self.window_seconds)})
        recent.append(now)
        self.hits[key] = recent
        if len(self.hits) > 10000:
            self.hits = defaultdict(list, {key: values for key, values in self.hits.items() if values and now - values[-1] < self.window_seconds})
        return await call_next(request)
