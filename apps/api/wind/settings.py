"""Operational values. Every one can be overridden with a WIND_* env var."""

from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WIND_", frozen=True)

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_s: float = 20.0
    market_timezone: str = "Europe/London"
    sim_first_day: date = date(2026, 1, 1)
    windows_days: tuple[int, ...] = (7, 14)
    band_window_days: int = 14
    band_lower_pct: float = 10
    band_upper_pct: float = 90
