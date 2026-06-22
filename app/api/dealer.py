from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from app.database import get_db
from app.models import UnlimitedSource, ServerConfig, ClientKey, User
from app.schemas import (
    UnlimitedSourceCreate, UnlimitedSourceOut,
    ServerConfigUpdate, ServerConfigOut,
    ClientKeyBase, ClientKeyCreate, ClientKeyOut, ClientKeyReset, PaginatedKeys,
    UserUpdate, UserOut,
)
from app.auth import get_current_dealer
from app.redis_client import (
    clear_device_limit, delete_subscription_cache, get_device_structured_list
)

router = APIRouter(prefix="/dealer", tags=["dealer"])

BAD_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]


def _clear_all_sub_caches(db):
    import redis as rlib
    from app.config import get_settings
    s = get_settings()
    try:
        r = rlib.Redis.from_url(s.REDIS_URL, decode_responses=True)
        keys = r.keys("sub_cache:*")
        if keys:
            r.delete(*keys)
    except Exception:
        pass


def _get_all_source_ids(dealer, db):
    admin_ids = [u.id for u in db.query(User).filter(User.is_admin == True).all()]
    owner_ids = list(set([dealer.id] + admin_ids))
    return [s.id for s in db.query(UnlimitedSource).filter(
        UnlimitedSource.owner_id.in_(owner_ids),
        UnlimitedSource.is_active == True
    ).all()]


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_dealer)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(update: UserUpdate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only Admin can change settings.")
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    _clear_all_sub_caches(db)
    return current_user


@router.get("/stats")
def dealer_stats(current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    total_keys = db.query(func.count(ClientKey.id)).filter(ClientKey.dealer_id == current_user.id).scalar()
    active_keys = db.query(func.count(ClientKey.id)).filter(ClientKey.dealer_id == current_user.id, ClientKey.is_active == True).scalar()
    source_ids = _get_all_source_ids(current_user, db)
    total_sources = len(source_ids)
    total_servers = db.query(func.count(ServerConfig.id)).filter(
        ServerConfig.source_id.in_(source_ids),
        ServerConfig.is_active == True,
        ServerConfig.host.notin_(BAD_HOSTS)
    ).scalar() if source_ids else 0
    return {"total_keys": total_keys, "active_keys": active_keys, "total_sources": total_sources, "total_servers": total_servers}


@router.post("/sources", response_model=UnlimitedSourceOut)
def create_source(source_in: UnlimitedSourceCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(403, "Forbidden")
    source = UnlimitedSource(**source_in.dict(), owner_id=current_user.id)
    db.add(source)
    db.commit()
    db.refresh(source)
    _clear_all_sub_caches(db)
    return source


@router.get("/sources", response_model=list[UnlimitedSourceOut])
def list_sources(current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    admin_ids = [u.id for u in db.query(User).filter(User.is_admin == True).all()]
    owner_ids = list(set([current_user.id] + admin_ids))
    return db.query(UnlimitedSource).filter(UnlimitedSource.owner_id.in_(owner_ids)).all()


@router.patch("/sources/{source_id}", response_model=UnlimitedSourceOut)
def update_source(source_id: int, data: UnlimitedSourceCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(403, "Forbidden")
    source = db.query(UnlimitedSource).filter(UnlimitedSource.id == source_id, UnlimitedSource.owner_id == current_user.id).first()
    if not source:
        raise HTTPException(404, "Not found")
    for field, val in data.dict().items():
        setattr(source, field, val)
    db.commit()
    db.refresh(source)
    _clear_all_sub_caches(db)
    return source


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(403, "Forbidden")
    source = db.query(UnlimitedSource).filter(UnlimitedSource.id == source_id, UnlimitedSource.owner_id == current_user.id).first()
    if source:
        db.delete(source)
        db.commit()
        _clear_all_sub_caches(db)
    return {"detail": "Deleted"}


@router.post("/sources/{source_id}/refresh")
def fetch_source_now(source_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    from app.tasks import fetch_single_source
    fetch_single_source.delay(source_id)
    _clear_all_sub_caches(db)
    return {"detail": "Fetch queued"}


@router.get("/servers", response_model=list[ServerConfigOut])
def list_servers(current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    source_ids = _get_all_source_ids(current_user, db)
    if not source_ids:
        return []
    q = db.query(ServerConfig).filter(ServerConfig.source_id.in_(source_ids))
    if not current_user.is_admin:
        q = q.filter(ServerConfig.host.notin_(BAD_HOSTS))
        q = q.filter(ServerConfig.is_active == True)
    return q.order_by(ServerConfig.priority).all()


@router.patch("/servers/{server_id}", response_model=ServerConfigOut)
def update_server(server_id: int, data: ServerConfigUpdate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(403, "Forbidden")
    server = db.query(ServerConfig).join(UnlimitedSource).filter(ServerConfig.id == server_id, UnlimitedSource.owner_id == current_user.id).first()
    if not server:
        raise HTTPException(404, "Not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(server, field, value)
    db.commit()
    db.refresh(server)
    _clear_all_sub_caches(db)
    return server


@router.post("/keys", response_model=ClientKeyOut)
def create_key(key_in: ClientKeyCreate, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    existing = db.query(ClientKey).filter(ClientKey.dealer_id == current_user.id, ClientKey.client_name == key_in.client_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Key with name '{}' already exists.".format(key_in.client_name))
    key = ClientKey(**key_in.dict(), dealer_id=current_user.id)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@router.get("/keys", response_model=PaginatedKeys)
def list_keys(page: int = Query(1, ge=1), q: Optional[str] = None, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    limit = 15
    query = db.query(ClientKey).filter(ClientKey.dealer_id == current_user.id)
    if q:
        query = query.filter(ClientKey.client_name.ilike("%{}%".format(q)))
    total = query.count()
    items = query.order_by(desc(ClientKey.created_at)).offset((page - 1) * limit).limit(limit).all()
    return PaginatedKeys(items=items, total=total, page=page, pages=(total + limit - 1) // limit)


@router.patch("/keys/{key_id}", response_model=ClientKeyOut)
def update_key(key_id: int, data: ClientKeyBase, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(key, field, value)
    db.commit()
    db.refresh(key)
    delete_subscription_cache(key.token)
    return key


@router.delete("/keys/{key_id}")
def delete_key(key_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if key:
        db.delete(key)
        db.commit()
        delete_subscription_cache(key.token)
    return {"detail": "Deleted"}


@router.post("/keys/{key_id}/reset")
def reset_key(key_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if key:
        key.hwid = ""
        db.commit()
        clear_device_limit(key.token)
        delete_subscription_cache(key.token)
    return {"detail": "Reset Done"}


@router.get("/keys/{key_id}/devices")
def key_devices(key_id: int, current_user: User = Depends(get_current_dealer), db: Session = Depends(get_db)):
    key = db.query(ClientKey).filter(ClientKey.id == key_id, ClientKey.dealer_id == current_user.id).first()
    if not key:
        raise HTTPException(404, "Not found")
    return get_device_structured_list(key.token)
