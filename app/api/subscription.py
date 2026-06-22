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


def _get_admin(db):
    return db.query(User).filter(User.is_admin == True).first()


def _get_all_sources(dealer, db):
    admin_ids = [u.id for u in db.query(User).filter(User.is_admin == True).all()]
    owner_ids = list(set([dealer.id] + admin_ids))
    return db.query(UnlimitedSource).filter(
        UnlimitedSource.owner_id.in_(owner_ids),
        UnlimitedSource.is_active == True
    ).all()


@router.get("/sub/{token}")
@limiter.limit("120/minute")
def get_subscription(
    token: str,
    request: Request,
    user_agent: str = Header("", convert_underscores=False),
    hwid: str = Header("", convert_underscores=False),
    db: Session = Depends(get_db)
):
    client_key = db.query(ClientKey).filter(ClientKey.token == token).first()
    if not client_key:
        raise HTTPException(status_code=404, detail="Key not found")

    if not client_key.is_active:
        return _blocked_response("\U0001f512 Доступ ограничен", "Ключ отключен или заблокирован.")

    if client_key.expires_at and datetime.utcnow() > client_key.expires_at:
        return _blocked_response("\U0001f512 Срок истек", "Подписка закончилась. Продлите у продавца.")

    dealer = db.query(User).filter(User.id == client_key.dealer_id).first()
    if not dealer or not dealer.is_active:
        return _blocked_response("\U0001f512 Ошибка", "Аккаунт дилера недоступен.")

    admin = _get_admin(db)

    # Дилер ВСЕГДА использует настройки админа
    if dealer.is_admin:
        profile_title = dealer.profile_title or "Acar"
        announcement = dealer.announcement or ""
        vless_template = dealer.vless_template or ""
        happ_api_key = dealer.happ_api_key or ""
    else:
        profile_title = (admin.profile_title if admin else "") or "Acar"
        announcement = (admin.announcement if admin else "") or ""
        vless_template = (admin.vless_template if admin else "") or ""
        happ_api_key = (admin.happ_api_key if admin else "") or ""

    # Device Limit
    ip = get_real_ip(request)
    count = cache_device_hit_structured(
        token, ip, user_agent, hwid, settings.DEVICE_LIMIT_TTL_MINUTES * 60
    )
    if count > client_key.device_limit:
        return _blocked_response("\U0001f512 Лимит", "Превышено кол-во устройств ({}).".format(client_key.device_limit))

    # Cache
    cached = get_cached_subscription(token)
    if cached:
        return _build_response(cached, profile_title, happ_api_key)

    # Build lines
    all_lines = []

    # VLESS templates
    templates = set()
    if vless_template:
        templates.add(vless_template.strip())

    sources = _get_all_sources(dealer, db)
    for src in sources:
        if src.vless_template:
            templates.add(src.vless_template.strip())

    for tmpl in templates:
        clean_tmpl = tmpl.split('#')[0]
        all_lines.append("{}#{}".format(clean_tmpl, client_key.client_name))

    # Servers from all sources
    for src in sources:
        servers = db.query(ServerConfig).filter(
            ServerConfig.source_id == src.id,
            ServerConfig.is_active == True
        ).order_by(ServerConfig.priority).all()
        for srv in servers:
            display_name = (srv.custom_name or srv.server_name or "Server").replace("{USERNAME}", client_key.client_name)
            link_body = srv.raw_link.split('#')[0]
            all_lines.append("{}#{}".format(link_body, display_name))

    # Deduplicate
    seen = set()
    final_lines = []
    for line in all_lines:
        if line not in seen:
            final_lines.append(line)
            seen.add(line)

    profile_title = profile_title.replace("{USERNAME}", client_key.client_name)
    announcement = announcement.replace("{USERNAME}", client_key.client_name)

    header_lines = ["#profile-title: base64:{}".format(_b64(profile_title))]
    if announcement:
        header_lines.append("#announce: base64:{}".format(_b64(announcement)))

    body = "\n".join(header_lines + final_lines)
    cache_subscription(token, body, settings.SUBSCRIPTION_CACHE_TTL_MINUTES * 60)

    return _build_response(body, profile_title, happ_api_key)


def _b64(t):
    return base64.b64encode(t.encode("utf-8")).decode("utf-8")


def _build_response(body, title, key=""):
    content = body
    if key:
        encrypted = encrypt_subscription(body, key)
        if encrypted:
            content = encrypted

    safe_title = title.encode("ascii", "ignore").decode("ascii") or "sub"
    return Response(
        content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        media_type="text/plain",
        headers={
            "content-disposition": 'attachment; filename="{}.txt"'.format(safe_title),
            "profile-title": safe_title,
        }
    )


def _blocked_response(title, msg):
    body = "#profile-title: base64:{}\n#announce: base64:{}\n".format(_b64(title), _b64(msg))
    return Response(
        content=base64.b64encode(body.encode("utf-8")).decode("utf-8"),
        media_type="text/plain",
        headers={"profile-title": "Blocked"}
    )
