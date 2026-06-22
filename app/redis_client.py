import redis
import json
from datetime import datetime
from app.config import get_settings

settings = get_settings()

_pool = None

# In-memory fallback when Redis is unavailable
_fallback_cache = {}
_fallback_devices = {}

def get_redis() -> redis.Redis | None:
    global _pool
    try:
        if _pool is None:
            _pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
        r = redis.Redis(connection_pool=_pool)
        r.ping()
        return r
    except Exception:
        return None

def _redis_or_fallback():
    r = get_redis()
    if r is not None:
        return r, False
    return None, True

# --- Device tracking (structured) ---

def cache_device_hit_structured(token: str, ip: str, user_agent: str, hwid: str = "", ttl_seconds: int = 900):
    """Регистрирует обращение к подписке.
    
    Устройства считаются по IP-адресу — это самый надёжный способ:
    - Один клиент с разными версиями VPN-приложения = 1 устройство ✅
    - Один клиент с разными User-Agent = 1 устройство ✅
    - Разные клиенты за разными IP = разные устройства ✅
    
    При каждом обращении обновляется User-Agent и HWID (метаданные),
    чтобы в панели отображалась актуальная информация.
    """
    r, fallback = _redis_or_fallback()
    device_key = f"dev_struct:{token}"
    device_id = _device_id(ip, hwid)
    now = datetime.utcnow().isoformat()
    
    if fallback:
        if device_key not in _fallback_devices:
            _fallback_devices[device_key] = {}
        # Обновляем или создаём запись по IP
        _fallback_devices[device_key][device_id] = {
            "ip": ip, "user_agent": user_agent, "hwid": hwid,
            "last_seen": now
        }
        return len(_fallback_devices[device_key])
    
    payload = json.dumps({
        "ip": ip,
        "user_agent": user_agent,
        "hwid": hwid,
        "last_seen": now,
    }, ensure_ascii=False)
    r.hset(device_key, device_id, payload)
    r.expire(device_key, ttl_seconds)
    # Считаем только активные устройства (обновлены за последние 5 мин)
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
    all_devices = r.hgetall(device_key)
    active = 0
    for dev_id, dev_payload in all_devices.items():
        try:
            dev_data = json.loads(dev_payload)
            if dev_data.get("last_seen", "") >= cutoff:
                active += 1
        except:
            active += 1
    return active

def get_device_structured_list(token: str) -> list[dict]:
    r, fallback = _redis_or_fallback()
    if fallback:
        data = _fallback_devices.get(f"dev_struct:{token}", {})
        devices = []
        for dev_id, payload in data.items():
            obj = dict(payload)
            obj["id"] = dev_id
            devices.append(obj)
        return devices

    key = f"dev_struct:{token}"
    data = r.hgetall(key)
    devices = []
    for dev_id, payload in data.items():
        try:
            obj = json.loads(payload)
            obj["id"] = dev_id
            devices.append(obj)
        except Exception:
            continue
    return devices

def clear_device_limit(token: str):
    r, fallback = _redis_or_fallback()
    if fallback:
        _fallback_devices.pop(f"dev_struct:{token}", None)
        _fallback_devices.pop(f"dev_limit:{token}", None)
        _fallback_cache.pop(f"sub_cache:{token}", None)
        return
    r.delete(f"dev_struct:{token}")
    r.delete(f"dev_limit:{token}")
    r.delete(f"sub_cache:{token}")


def cache_subscription(token: str, content: str, ttl_seconds: int = 600):
    r, fallback = _redis_or_fallback()
    if fallback:
        _fallback_cache[f"sub_cache:{token}"] = content
        return
    r.setex(f"sub_cache:{token}", ttl_seconds, content)

def get_cached_subscription(token: str) -> str | None:
    r, fallback = _redis_or_fallback()
    if fallback:
        return _fallback_cache.get(f"sub_cache:{token}")
    val = r.get(f"sub_cache:{token}")
    return val if val else None

def delete_subscription_cache(token: str):
    r, fallback = _redis_or_fallback()
    if fallback:
        _fallback_cache.pop(f"sub_cache:{token}", None)
        return
    r.delete(f"sub_cache:{token}")

def get_real_ip(request=None) -> str:
    """Получает реальный IP клиента из-за прокси (Nginx, Cloudflare)."""
    if request is None:
        return "unknown"
    # Cloudflare
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.split(",")[0].strip()
    # X-Forwarded-For (Nginx)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    # X-Real-IP
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


def _device_id(ip: str, hwid: str = "") -> str:
    """Уникальный ID устройства.
    
    Приоритет: HWID (аппаратный ID) > IP-адрес (fallback)
    """
    import hashlib
    identifier = hwid.strip() if hwid and hwid.strip() else ip
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]
