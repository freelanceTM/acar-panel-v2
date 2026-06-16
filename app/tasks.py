import httpx
import base64
import json
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import UnlimitedSource, ServerConfig

PROTOCOLS = ["vless", "trojan", "vmess", "ss", "ssr"]

@shared_task
def fetch_all_sources():
    db = SessionLocal()
    try:
        sources = db.query(UnlimitedSource).filter(UnlimitedSource.is_active == True).all()
        for source in sources:
            fetch_single_source.delay(source.id)
    finally:
        db.close()

@shared_task(bind=True, max_retries=3)
def fetch_single_source(self, source_id: int):
    db = SessionLocal()
    try:
        source = db.query(UnlimitedSource).filter(UnlimitedSource.id == source_id).first()
        if not source:
            return
        try:
            resp = httpx.get(source.url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)

        text = resp.text.strip()
        # Try base64 decode first (common for subscription links)
        try:
            decoded = base64.b64decode(text).decode("utf-8")
            lines = [ln.strip() for ln in decoded.splitlines() if ln.strip()]
        except Exception:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # Delete old cached servers for this source
        db.query(ServerConfig).filter(ServerConfig.source_id == source.id).delete()

        for idx, line in enumerate(lines):
            parsed = parse_proxy_link(line)
            if parsed:
                sc = ServerConfig(
                    source_id=source.id,
                    protocol=parsed["protocol"],
                    raw_link=line,
                    server_name=parsed.get("name", ""),
                    host=parsed.get("host", ""),
                    port=parsed.get("port", 0),
                    priority=idx,
                )
                db.add(sc)

        source.last_fetched_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def parse_proxy_link(link: str) -> dict | None:
    if link.startswith("vless://"):
        return _parse_vless_trojan(link, "vless")
    if link.startswith("trojan://"):
        return _parse_vless_trojan(link, "trojan")
    if link.startswith("vmess://"):
        return _parse_vmess(link)
    if link.startswith("ss://"):
        return _parse_ss(link)
    if link.startswith("ssr://"):
        return _parse_ssr(link)
    return None

def _parse_vless_trojan(link: str, protocol: str) -> dict | None:
    try:
        rest = link.split("://", 1)[1]
        tag = ""
        if "#" in rest:
            body, tag = rest.rsplit("#", 1)
            tag = unquote(tag)
        else:
            body = rest

        if "?" in body:
            url_part, query = body.split("?", 1)
        else:
            url_part = body
            query = ""

        if "@" in url_part:
            userinfo, host_port = url_part.split("@", 1)
        else:
            host_port = url_part
            userinfo = ""

        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str.split("/")[0])
        else:
            host = host_port
            port = 443 if protocol == "trojan" else 443

        return {"protocol": protocol, "host": host, "port": port, "name": tag}
    except Exception:
        return None

def _parse_vmess(link: str) -> dict | None:
    try:
        b64 = link.split("://", 1)[1]
        decoded = base64.b64decode(b64 + "==").decode("utf-8")
        obj = json.loads(decoded)
        return {
            "protocol": "vmess",
            "host": obj.get("add", ""),
            "port": int(obj.get("port", 0)),
            "name": obj.get("ps", ""),
        }
    except Exception:
        return None

def _parse_ss(link: str) -> dict | None:
    try:
        rest = link.split("://", 1)[1]
        tag = ""
        if "#" in rest:
            body, tag = rest.rsplit("#", 1)
            tag = unquote(tag)
        else:
            body = rest

        # ss://base64(method:password)@host:port#tag
        if "@" in body:
            b64_userinfo, host_port = body.split("@", 1)
        else:
            # Try decode entire body as base64 if no @
            try:
                decoded = base64.b64decode(body + "==").decode("utf-8")
                if "@" in decoded:
                    b64_userinfo, host_port = decoded.split("@", 1)
                else:
                    return None
            except Exception:
                return None

        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str.split("/")[0])
        else:
            host = host_port
            port = 8388

        return {"protocol": "ss", "host": host, "port": port, "name": tag}
    except Exception:
        return None

def _parse_ssr(link: str) -> dict | None:
    try:
        b64 = link.split("://", 1)[1]
        decoded = base64.b64decode(b64 + "==").decode("utf-8")
        # ssr://server:port:protocol:method:obfs:password_base64/?params_base64
        parts = decoded.split("://", 1)[0] if "://" in decoded else decoded
        if not parts:
            return None
        # Simple heuristic: take host and port from beginning
        match = re.match(r"([^:]+):(\d+):", decoded)
        if match:
            host = match.group(1)
            port = int(match.group(2))
        else:
            host = ""
            port = 0
        return {"protocol": "ssr", "host": host, "port": port, "name": ""}
    except Exception:
        return None
