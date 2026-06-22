from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "relaxpanel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "fetch-all-sources": {
            "task": "app.tasks.fetch_all_sources",
            "schedule": 300.0,  # every 5 minutes
        },
        "delete-expired-keys": {
            "task": "app.tasks.delete_expired_keys",
            "schedule": 120.0,  # every 2 minutes — удаляем просроченные ключи
        },
    },
)
