from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List
from app.database import get_db
from app.models import UnlimitedSource, ServerConfig, ClientKey, User
from app.schemas import (
    UnlimitedSourceCreate, UnlimitedSourceOut,
    ServerConfigUpdate, ServerConfigOut,
    ClientKeyCreate, ClientKeyOut, ClientKeyReset, PaginatedKeys,
    UserUpdate, UserOut,
)
from pydantic import BaseModel
from app.auth import get_current_dealer
from app.redis_client import (
    clear_device_limit, get_cached_subscription, cache_subscription,
    cache_device_hit_structured, get_device_structured_list, delete_subscription_cache
)

router = APIRouter(prefix="/dealer", tags=["dealer"])

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_dealer)):
    return current_user

@router.patch("/me", response_model=UserOut)
def update_me(update: UserUpdate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    for field, value in update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user

# Stats
@router.get("/stats")
def dealer_stats(current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    total_keys = db.query(func.count(ClientKey.id)).filter(ClientKey.dealer_id == current_user.id).scalar()
    active_keys = db.query(func.count(ClientKey.id)).filter(
        ClientKey.dealer_id == current_user.id, ClientKey.is_active == True
    ).scalar()
    total_sources = db.query(func.count(UnlimitedSource.id)).filter(
        UnlimitedSource.owner_id == current_user.id
    ).scalar()
    total_servers = db.query(func.count(ServerConfig.id)).join(UnlimitedSource).filter(
        UnlimitedSource.owner_id == current_user.id
    ).scalar()
    return {
        "total_keys": total_keys,
        "active_keys": active_keys,
        "total_sources": total_sources,
        "total_servers": total_servers,
    }

# Sources
@router.post("/sources", response_model=UnlimitedSourceOut)
def create_source(source_in: UnlimitedSourceCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    source = UnlimitedSource(**source_in.dict(), owner_id=current_user.id)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source

@router.get("/sources", response_model=list[UnlimitedSourceOut])
def list_sources(current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    return db.query(UnlimitedSource).filter(UnlimitedSource.owner_id == current_user.id).all()

@router.delete("/sources/{source_id}")
def delete_source(source_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    source = db.query(UnlimitedSource).filter(
        UnlimitedSource.id == source_id, UnlimitedSource.owner_id == current_user.id
    ).first()
    if not source:
        raise HTTPException(404, "Source not found")
    db.delete(source)
    db.commit()
    # Invalidate all dealer subscription caches since source changed
    delete_subscription_cache_for_dealer(current_user.id, db)
    return {"detail": "Deleted"}

@router.post("/sources/{source_id}/fetch")
def fetch_source_now(source_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    from app.tasks import fetch_single_source
    source = db.query(UnlimitedSource).filter(
        UnlimitedSource.id == source_id, UnlimitedSource.owner_id == current_user.id
    ).first()
    if not source:
        raise HTTPException(404, "Source not found")
    fetch_single_source.delay(source_id)
    return {"detail": "Fetch queued"}

# Servers
@router.get("/servers", response_model=list[ServerConfigOut])
def list_servers(
    source_id: Optional[int] = None,
    current_user: User = Depends(get_current_dealer),
    db: Session = Depends(get_db)
):
    query = db.query(ServerConfig).join(UnlimitedSource).filter(
        UnlimitedSource.owner_id == current_user.id
    )
    if source_id:
        query = query.filter(ServerConfig.source_id == source_id)
    return query.order_by(ServerConfig.priority, ServerConfig.id).all()

@router.patch("/servers/{server_id}", response_model=ServerConfigOut)
def update_server(
    server_id: int, data: ServerConfigUpdate,
    current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)
):
    server = db.query(ServerConfig).join(UnlimitedSource).filter(
        ServerConfig.id == server_id,
        UnlimitedSource.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(404, "Server not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(server, field, value)
    db.commit()
    db.refresh(server)
    # Invalidate caches for dealer keys
    delete_subscription_cache_for_dealer(current_user.id, db)
    return server

class ReorderItem(BaseModel):
    id: int
    priority: int

@router.post("/servers/reorder")
def reorder_servers(
    items: List[ReorderItem],
    current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)
):
    for it in items:
        server = db.query(ServerConfig).join(UnlimitedSource).filter(
            ServerConfig.id == it.id,
            UnlimitedSource.owner_id == current_user.id
        ).first()
        if server:
            server.priority = it.priority
    db.commit()
    delete_subscription_cache_for_dealer(current_user.id, db)
    return {"detail": "Reordered"}

# Client Keys
@router.post("/keys", response_model=ClientKeyOut)
def create_key(key_in: ClientKeyCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = ClientKey(**key_in.dict(), dealer_id=current_user.id)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key

@router.get("/keys", response_model=PaginatedKeys)
def list_keys(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    q: Optional[str] = None,
    current_user: User = Depends(get_current_dealer),
    db: Session = Depends(get_db)
):
    query = db.query(ClientKey).filter(ClientKey.dealer_id == current_user.id)
    if q:
        query = query.filter(ClientKey.client_name.ilike(f"%{q}%"))
    total = query.count()
    items = query.order_by(desc(ClientKey.created_at)).offset((page - 1) * limit).limit(limit).all()
    pages = (total + limit - 1) // limit
    return PaginatedKeys(items=items, total=total, page=page, pages=pages)

@router.patch("/keys/{key_id}", response_model=ClientKeyOut)
def update_key(key_id: int, data: ClientKeyCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Key not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(key, field, value)
    db.commit()
    db.refresh(key)
    delete_subscription_cache(key.token)
    return key

@router.delete("/keys/{key_id}")
def delete_key(key_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Key not found")
    db.delete(key)
    db.commit()
    clear_device_limit(key.token)
    delete_subscription_cache(key.token)
    return {"detail": "Deleted"}

@router.post("/keys/{key_id}/reset")
def reset_key(key_id: int, data: ClientKeyReset, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Key not found")
    if data.reset_bindings:
        clear_device_limit(key.token)
    if data.reset_hwid:
        key.hwid = ""
    db.commit()
    db.refresh(key)
    delete_subscription_cache(key.token)
    return {"detail": "Reset performed"}

@router.get("/keys/{key_id}/devices")
def key_devices(key_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Key not found")
    devices = get_device_structured_list(key.token)
    return {"token": key.token, "devices": devices, "limit": key.device_limit}

# Helper to invalidate caches for ALL dealer keys
def delete_subscription_cache_for_dealer(dealer_id: int, db: Session):
    keys = db.query(ClientKey).filter(ClientKey.dealer_id == dealer_id).all()
    for k in keys:
        delete_subscription_cache(k.token)
