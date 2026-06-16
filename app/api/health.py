from fastapi import APIRouter
from sqlalchemy import text
from app.database import engine
from app.redis_client import get_redis

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_check():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        r = get_redis()
        r.ping()
        redis_ok = True
    except Exception:
        pass

    status = "healthy" if (db_ok and redis_ok) else "degraded"
    code = 200 if (db_ok and redis_ok) else 503
    return {"status": status, "database": db_ok, "redis": redis_ok, "code": code}
