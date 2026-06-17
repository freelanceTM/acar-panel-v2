import base64
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ClientKey, ServerConfig, UnlimitedSource, User
from app.redis_client import (
    cache_device_hit_structured,
    get_device_structured_list,
    clear_device_limit,
    get_cached_subscription,
    cache_subscription,
    delete_subscription_cache,
    get_real_ip,
)
from app.happ_crypt import encrypt_subscription
from app.rate_limit import limiter
from app.config import get_settings

router = APIRouter(tags=["subscription"])
settings = get_settings()

@router.get("/sub/{token}")
@limiter.limit("60/minute")
def get_subscription(
    token: str,
    request: Request,
    user_agent: str = Header("", convert_underscores=False),
    hwid: str = Header("", convert_underscores=False),
    db: Session = Depends(get_db)
):
    client_key = db.query(ClientKey).filter(ClientKey.token == token).first()
    if not client_key:
        raise HTTPException(status_code=404, detail="Not found")

    # Check expiration
    if client_key.expires_at and datetime.utcnow() > client_key.expires_at:
        return _blocked_response("🔒 Заблокировано", "Ключ просрочен. Обратитесь к продавцу.")

    if not client_key.is_active:
        return _blocked_response("🔒 Заблокировано", "Ключ отключен дилером.")

    dealer = db.query(User).filter(User.id == client_key.dealer_id).first()
    if not dealer or not dealer.is_active:
        return _blocked_response("🔒 Заблокировано", "Дилер заблокирован.")

    # HWID check
    if hwid and client_key.hwid:
        if hwid != client_key.hwid:
            return _blocked_response("🔒 Привязка устройства", "HWID не совпадает. Сбросьте привязку в панели.")
    elif hwid and not client_key.hwid:
        client_key.hwid = hwid
        db.commit()

    # Device limit check (structured)
    ip = get_real_ip(request)
    count = cache_device_hit_structured(
        token, ip, user_agent, hwid, settings.DEVICE_LIMIT_TTL_MINUTES * 60
    )
    if count > client_key.device_limit:
        return _blocked_response(
            "🔒 Превышен лимит устройств",
            f"Лимит: {client_key.device_limit} устройств. Сбросьте привязки в панели."
        )

    # Check cache
    cached = get_cached_subscription(token)
    if cached:
        return _build_response(cached, dealer.profile_title, dealer.happ_api_key)

    # Build config from cached servers
    sources = db.query(UnlimitedSource).filter(
        UnlimitedSource.owner_id == dealer.id,
        UnlimitedSource.is_active == True
    ).all()

    all_lines = []
    for source in sources:
        servers = db.query(ServerConfig).filter(
            ServerConfig.source_id == source.id,
            ServerConfig.is_active == True
        ).order_by(ServerConfig.priority, ServerConfig.id).all()
        for srv in servers:
            display_name = srv.custom_name or srv.server_name or f"Server {srv.id}"
            display_name = display_name.replace("{USERNAME}", client_key.client_name)
            link = srv.raw_link
            # Replace remark in link if it exists
            if "#" in link:
                body, old_tag = link.rsplit("#", 1)
                link = f"{body}#{display_name}"
            else:
                link = f"{link}#{display_name}"
            all_lines.append(link)

    # Build header and announcement
    profile_title = (dealer.profile_title or "Açar🔐").replace("{USERNAME}", client_key.client_name)
    announcement = (dealer.announcement or "").replace("{USERNAME}", client_key.client_name)

    header_lines = [f"#profile-title: base64:{_b64(profile_title)}"]
    if announcement:
        header_lines.append(f"#announce: base64:{_b64(announcement)}")

    body = "\n".join(header_lines + all_lines)

    # Cache it (raw, before encryption, to avoid re-encrypting every request)
    cache_subscription(token, body, settings.SUBSCRIPTION_CACHE_TTL_MINUTES * 60)

    return _build_response(body, profile_title, dealer.happ_api_key)

def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def _sanitize_header(val: str) -> str:
    # HTTP headers must be latin-1; strip non-ASCII or replace with ?
    return val.encode("ascii", "ignore").decode("ascii")

def _build_response(body: str, profile_title: str, happ_api_key: str = ""):
    content = body
    # If Happ API key is configured, attempt encryption
    if happ_api_key:
        encrypted = encrypt_subscription(body, happ_api_key)
        if encrypted:
            content = encrypted
    safe_title = _sanitize_header(profile_title)
    return Response(
        content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        media_type="text/plain",
        headers={
            "content-disposition": f'attachment; filename="{safe_title}.txt"',
            "profile-title": safe_title,
        }
    )

def _blocked_response(title: str, message: str):
    body = f"#profile-title: base64:{_b64(title)}\n#announce: base64:{_b64(message)}\n"
    safe_title = _sanitize_header(title)
    return Response(
        content=base64.b64encode(body.encode("utf-8")).decode("utf-8"),
        media_type="text/plain",
        headers={
            "content-disposition": 'attachment; filename="blocked.txt"',
            "profile-title": safe_title,
        }
    )
