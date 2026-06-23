from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Açar🔐"
    DATABASE_URL: str = "sqlite:///./relaxpanel.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours (было 7 дней)
    SUBSCRIPTION_CACHE_TTL_MINUTES: int = 2
    DEVICE_LIMIT_TTL_MINUTES: int = 15
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW: int = 600  # 10 minutes
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()