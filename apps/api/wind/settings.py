"""Operational values. Every one can be overridden with a WIND_* env var."""

from datetime import date, time

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WIND_", frozen=True)

    # Successful answers: browsers re-check after 5 min, the CDN keeps them a year
    # (the simulated month is history and never changes).
    cache_browser_max_age_s: int = 300
    cache_cdn_max_age_s: int = 31_536_000
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_s: float = 20.0
    market_timezone: str = "Europe/London"
    sim_first_day: date = date(2026, 1, 1)
    sim_last_day: date = date(2026, 1, 31)
    # Publishes that cover all of tomorrow and land before the 09:50 gate.
    slots: tuple[time, ...] = (time(2, 30), time(4, 30), time(7, 30), time(9, 30))
    windows_days: tuple[int, ...] = (7, 14)
    band_window_days: int = 14
    band_lower_pct: float = 10
    band_upper_pct: float = 90
    # Whole days for the day-total range; it uses the band's percentiles (the same 8 in 10).
    whole_day_window_days: int = 14

    @property
    def lookback_days(self) -> int:
        """How far back to fetch: far enough for every window that looks back."""
        return max((*self.windows_days, self.band_window_days, self.whole_day_window_days))
