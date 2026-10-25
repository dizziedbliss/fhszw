"""Rows coming in from Elexon, and the view going out to the API."""

from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel


@dataclass(frozen=True)
class ForecastRow:
    """One hourly WINDFOR value from one publish."""

    publish_time: datetime
    start_time: datetime
    generation_mw: int


@dataclass(frozen=True)
class ActualRow:
    """One FUELHH wind half-hour: average MW over the 30 minutes from start_time."""

    publish_time: datetime
    start_time: datetime
    generation_mw: int


class HourForecast(BaseModel):
    start_time: datetime
    forecast_mw: int
    # Where tomorrow lands if it misses like the band window did. None without a band.
    band_low_mw: float | None
    band_high_mw: float | None


class Extreme(BaseModel):
    mw: int
    start_time: datetime


class Tomorrow(BaseModel):
    delivery_day: date
    publish_time: datetime
    hours: list[HourForecast]
    total_mwh: int
    low: Extreme
    high: Extreme


class WindowMetrics(BaseModel):
    days: int
    half_hours: int
    # Visible half-hours left out because their product publish is missing.
    unscored_half_hours: int
    # Calendar days the window borrows from before the simulated month (e.g. Dec 2025).
    days_before_sim_start: int
    # None when half_hours is 0: there is no honest number to show.
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    # Shape MDA: did hour-to-hour moves go the same way? None when no move was judged.
    mda_pct: float | None
    mda_moves: int
    mda_flat_skipped: int


class Band(BaseModel):
    """The spread of past misses. Tomorrow's band is forecast - upper .. forecast - lower."""

    window_days: int
    half_hours: int
    lower_pct: float
    upper_pct: float
    lower_miss_mw: float
    upper_miss_mw: float
    # True when some band edge would have dipped below 0 MW and was held at 0.
    clipped_at_zero: bool


class HistoryPoint(BaseModel):
    start_time: datetime
    forecast_mw: int
    actual_mw: int
    miss_mw: int


class DecisionView(BaseModel):
    tomorrow: Tomorrow
    band: Band | None
    windows: list[WindowMetrics]
    # Every scored half-hour of the longest window, oldest first.
    history: list[HistoryPoint]
