from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Canoptek Calculator"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "sqlite:///./data/canoptek.sqlite3"
    fixtures_dir: Path = Field(default=Path("fixtures/wahapedia/wh40k10ed"))
    wahapedia_game_system: str = "wh40k10ed"
    wahapedia_base_url: str = "https://www.wahapedia.ru"
    default_simulation_trials: int = 5000
    max_simulation_trials: int = 50000
    auto_sync_on_startup: bool = False
    app_allowed_hosts: str = "127.0.0.1,localhost,testserver"
    unit_effect_ai_enabled: bool = False
    unit_effect_ai_model: str = "gpt-5-mini"
    unit_effect_ai_base_url: str = "https://api.openai.com/v1"
    unit_effect_ai_timeout_seconds: float = 45.0
    unit_effect_ai_batch_size: int = 12
    openai_api_key: str | None = None

    @property
    def allowed_hosts(self) -> list[str]:
        """Return the trusted host list for Host header protection."""

        hosts = [host.strip() for host in self.app_allowed_hosts.split(",") if host.strip()]
        return hosts or ["*"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
