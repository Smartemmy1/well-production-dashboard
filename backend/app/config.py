"""Application settings, read from environment variables (or a .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Well Production Dashboard API"
    database_url: str = "sqlite:///./production.db"
    seed_demo_data: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Alert thresholds (tunable without code changes)
    drop_warning_pct: float = 25.0  # recent oil rate down this much vs baseline -> warning
    drop_critical_pct: float = 50.0  # ...down this much -> critical
    high_water_cut: float = 0.80  # water cut above this -> warning
    recent_window_days: int = 7
    baseline_window_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
