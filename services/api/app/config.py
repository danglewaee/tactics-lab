from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tactics Lab API"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/tactics_lab"
    editorial_team_slugs: list[str] = ["manchester-united", "portugal"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

