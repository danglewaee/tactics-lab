from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    BaseSettings = None
    SettingsConfigDict = None


if BaseSettings is not None and SettingsConfigDict is not None:
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
else:
    class Settings(BaseModel):
        app_name: str = Field(default_factory=lambda: getenv("APP_NAME", "Tactics Lab API"))
        app_env: str = Field(default_factory=lambda: getenv("APP_ENV", "development"))
        api_prefix: str = Field(default_factory=lambda: getenv("API_PREFIX", "/api"))
        database_url: str = Field(
            default_factory=lambda: getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tactics_lab")
        )
        editorial_team_slugs: list[str] = Field(
            default_factory=lambda: [item.strip() for item in getenv("EDITORIAL_TEAM_SLUGS", "manchester-united,portugal").split(",") if item.strip()]
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
