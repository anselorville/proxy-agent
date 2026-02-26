import os
import sys
from dataclasses import dataclass
from typing import List


def _as_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _as_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _as_list(name: str, default: List[str]) -> List[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    database_pool_size: int
    database_max_overflow: int
    redis_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    auth_username: str
    auth_password: str
    cors_allowed_origins: List[str]
    proxy_pool_size: int
    request_interval: float
    max_retries: int
    data_fetch_batch_size: int

    @property
    def is_test(self) -> bool:
        if self.app_env == "test":
            return True
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            return True
        return any("pytest" in arg for arg in sys.argv)


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development")
    is_test_runtime = app_env == "test" or os.getenv("PYTEST_CURRENT_TEST") is not None or any("pytest" in arg for arg in sys.argv)
    default_database_url = "sqlite:///./test.db" if is_test_runtime else "postgresql://user:password@localhost:5432/stock_data"
    database_url = os.getenv("DATABASE_URL", default_database_url)
    database_pool_size = _as_int("DATABASE_POOL_SIZE", 20)
    database_max_overflow = _as_int("DATABASE_MAX_OVERFLOW", 10)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    secret_key = os.getenv("SECRET_KEY", "")
    algorithm = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes = _as_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    auth_username = os.getenv("AUTH_USERNAME", "admin" if is_test_runtime else "")
    auth_password = os.getenv("AUTH_PASSWORD", "admin" if is_test_runtime else "")
    cors_allowed_origins = _as_list("CORS_ALLOWED_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"])
    proxy_pool_size = _as_int("PROXY_POOL_SIZE", 5)
    request_interval = _as_float("REQUEST_INTERVAL", 2.0)
    max_retries = _as_int("MAX_RETRIES", 3)
    data_fetch_batch_size = _as_int("DATA_FETCH_BATCH_SIZE", 50)

    settings = Settings(
        app_env=app_env,
        database_url=database_url,
        database_pool_size=database_pool_size,
        database_max_overflow=database_max_overflow,
        redis_url=redis_url,
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        auth_username=auth_username,
        auth_password=auth_password,
        cors_allowed_origins=cors_allowed_origins,
        proxy_pool_size=proxy_pool_size,
        request_interval=request_interval,
        max_retries=max_retries,
        data_fetch_batch_size=data_fetch_batch_size,
    )

    if not settings.is_test and not settings.secret_key:
        raise RuntimeError("SECRET_KEY is required when APP_ENV is not test")
    if not settings.is_test and (not settings.auth_username or not settings.auth_password):
        raise RuntimeError("AUTH_USERNAME and AUTH_PASSWORD are required when APP_ENV is not test")

    return settings


settings = load_settings()
