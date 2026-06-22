from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models import User, ClientKey, UnlimitedSource, ServerConfig
from app.schemas import UserOut, UserCreate, AdminUserUpdate
from app.auth import get_current_admin, get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[UserOut])
def list_users(
    q: Optional[str] = None,
    is_dealer: Optional[bool] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    query = db.query(User)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))
    if is_dealer is not None:
        query = query.filter(User.is_dealer == is_dealer)
    return query.order_by(User.created_at.desc()).all()

@router.post("/users", response_model=UserOut)
def create_user(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(400, "Username already taken")
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        is_dealer=data.is_dealer,
        is_admin=data.is_admin,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/users/{user_id}", response_model=UserOut)
def update_user_admin(user_id: int, data: AdminUserUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    update_data = data.dict(exclude_unset=True)
    if "password" in update_data:
        user.hashed_password = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.patch("/users/{user_id}/toggle", response_model=UserOut)
def toggle_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "Cannot toggle yourself")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    db.delete(user)
    db.commit()
    return {"detail": "Deleted"}

@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(User).count()
    total_dealers = db.query(User).filter(User.is_dealer == True).count()
    total_keys = db.query(ClientKey).count()
    total_sources = db.query(UnlimitedSource).count()
    total_servers = db.query(ServerConfig).count()
    active_keys = db.query(ClientKey).filter(ClientKey.is_active == True).count()
    return {
        "total_users": total_users,
        "total_dealers": total_dealers,
        "total_keys": total_keys,
        "active_keys": active_keys,
        "total_sources": total_sources,
        "total_servers": total_servers,
    }

