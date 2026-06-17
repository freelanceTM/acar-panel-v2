import logging
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import DDoSProtectionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limit import limiter
from app.database import engine, Base
from app.api import auth, dealer, subscription, admin, health
from app.config import get_settings
from app.auth import get_password_hash
from app.models import User
from app.database import SessionLocal

settings = get_settings()

# --- Logging setup ---
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("acar")

Base.metadata.create_all(bind=engine)


def bootstrap_admin():
    """Создаёт первого админа, если настроено через env."""
    first_admin = os.getenv("FIRST_ADMIN_USERNAME")
    first_pass = os.getenv("FIRST_ADMIN_PASSWORD")
    if not first_admin or not first_pass:
        return
    if not first_pass or len(first_pass) < 6:
        logger.warning(
            "FIRST_ADMIN_PASSWORD too short or not set — admin bootstrap skipped"
        )
        return
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == first_admin).first()
        if not existing:
            user = User(
                username=first_admin,
                email=f"{first_admin}@admin.local",
                hashed_password=get_password_hash(first_pass),
                is_admin=True,
                is_dealer=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
            logger.info(f"Created admin user: {first_admin}")
    finally:
        db.close()


bootstrap_admin()

app = FastAPI(
    title=settings.APP_NAME,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(DDoSProtectionMiddleware)

# CORS — в production ограничьте origins конкретным доменом
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

app.include_router(auth.router, prefix="/api")
app.include_router(dealer.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(subscription.router)


@app.get("/")
def root():
    if os.path.exists(os.path.join(frontend_path, "index.html")):
        return FileResponse(os.path.join(frontend_path, "index.html"))
    return {"message": "Açar🔐 API is running"}


@app.on_event("startup")
async def startup_event():
    logger.info(
        f"{settings.APP_NAME} started | DB: {settings.DATABASE_URL} | "
        f"Redis: {settings.REDIS_URL}"
    )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Açar🔐 shutting down...")


# Admin OpenAPI unlock (optional guard) — disabled in production
@app.get("/admin/docs")
def admin_docs():
    raise HTTPException(403, "Disabled")
