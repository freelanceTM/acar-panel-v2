import httpx
from app.config import get_settings

settings = get_settings()

HAPP_API_URL = getattr(settings, "HAPP_API_URL", "https://happ.su/api/encrypt")

def encrypt_subscription(text: str, api_key: str) -> str | None:
    """Encrypt subscription text via Happ-compatible API.

    Returns encrypted payload string on success, None on failure.
    """
    try:
        resp = httpx.post(
            HAPP_API_URL,
            json={"text": text, "key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("encrypted") or data.get("payload") or data.get("result")
    except Exception:
        return None
