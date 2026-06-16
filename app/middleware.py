import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.redis_client import get_redis, _redis_or_fallback
from app.config import get_settings

settings = get_settings()

BAN_WINDOW = 60       # секунд
BAN_THRESHOLD = 100   # запросов на /sub/ за 10 секунд → бан на 5 минут
BAN_DURATION = 300    # 5 минут бана

# In-memory fallback bans
_fallback_bans = {}  # ip -> timestamp when ban expires

def _is_banned(ip: str) -> bool:
    r, fallback = _redis_or_fallback()
    if fallback:
        return _fallback_bans.get(ip, 0) > time.time()
    try:
        return r.exists(f"ban:{ip}")
    except Exception:
        return _fallback_bans.get(ip, 0) > time.time()

def _ban_ip(ip: str, duration: int = BAN_DURATION):
    r, fallback = _redis_or_fallback()
    if fallback:
        _fallback_bans[ip] = time.time() + duration
    else:
        try:
            r.setex(f"ban:{ip}", duration, "1")
        except Exception:
            _fallback_bans[ip] = time.time() + duration

def _track_and_check(ip: str, path: str) -> bool:
    """Returns True if IP should be banned (over threshold)."""
    if not path.startswith("/sub/"):
        return False
    r, fallback = _redis_or_fallback()
    key = f"ddos:{ip}"
    if fallback:
        # Simple in-memory counter per 10-second window
        now = int(time.time())
        window = now // 10
        mem_key = f"{key}:{window}"
        count = _fallback_bans.get(mem_key, 0) + 1  # reuse dict for counters
        _fallback_bans[mem_key] = count
        # Cleanup old windows
        for k in list(_fallback_bans.keys()):
            if k.startswith(key) and int(k.split(":")[-1]) < window - 1:
                _fallback_bans.pop(k, None)
        return count > BAN_THRESHOLD
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 10)
        results = pipe.execute()
        count = results[0]
        return count > BAN_THRESHOLD
    except Exception:
        return False

class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Check if already banned
        if _is_banned(ip):
            return Response(
                content="🔒 IP temporarily blocked due to excessive requests.",
                status_code=429,
                headers={"Retry-After": str(BAN_DURATION)}
            )

        # Track subscription abuse
        if _track_and_check(ip, path):
            _ban_ip(ip, BAN_DURATION)
            return Response(
                content="🔒 Your IP has been blocked for 5 minutes. Too many requests.",
                status_code=429,
                headers={"Retry-After": str(BAN_DURATION)}
            )

        response = await call_next(request)
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
