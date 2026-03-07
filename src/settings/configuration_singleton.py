from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="event-router", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_timeout_seconds: int = Field(default=10, alias="APP_TIMEOUT_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="event_router", alias="POSTGRES_DB")
    postgres_user: str = Field(default="event_router", alias="POSTGRES_USER")
    postgres_password: str = Field(default="event_router", alias="POSTGRES_PASSWORD")
    postgres_min_pool_size: int = Field(default=1, alias="POSTGRES_MIN_POOL_SIZE")
    postgres_max_pool_size: int = Field(default=5, alias="POSTGRES_MAX_POOL_SIZE")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
