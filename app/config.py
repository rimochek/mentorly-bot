from functools import lru_cache
from urllib.parse import quote

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_ids: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mentorly"
    postgres_user: str = "mentorly"
    postgres_password: str = "mentorly"

    redis_connection_url: str | None = Field(default=None, validation_alias="REDIS_URL")
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    @field_validator("redis_connection_url", mode="before")
    @classmethod
    def empty_redis_url_is_none(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return str(value).strip()

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_connection_url:
            return self.redis_connection_url

        if self.redis_password:
            encoded_password = quote(self.redis_password, safe="")
            return (
                f"redis://:{encoded_password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )

        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
