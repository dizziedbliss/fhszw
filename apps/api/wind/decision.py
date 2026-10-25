"""build_decision: the one door. Fetching, the barrier, pairing and scoring hide behind it."""

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from wind import scoring
from wind.barrier import visible_at
from wind.models import (
    ActualRow,
    Band,
    DecisionView,
    Extreme,
    ForecastRow,
    HistoryPoint,
    HourForecast,
    Tomorrow,
    WindowMetrics,
)
from wind.settings import Settings
from wind.source import Source


class ForecastUnavailableError(Exception):
    """The chosen slot's publish is missing or doesn't cover the whole of tomorrow."""


@dataclass(frozen=True)
class _Pair:
    """One past half-hour: what the product forecast said, and what was metered."""

    start_time: datetime
    forecast_mw: int
    actual_mw: int

    @property
    def miss_mw(self) -> int:
        return self.forecast_mw - self.actual_mw


async def build_decision(
    today: date, slot: time, source: Source, settings: Settings
) -> DecisionView:
    tz = ZoneInfo(settings.market_timezone)
    as_of = datetime.combine(today, slot, tzinfo=tz).astimezone(UTC)
    longest = max((*settings.windows_days, settings.band_window_days))
    raw_forecasts, raw_actuals = await asyncio.gather(
        source.forecasts(as_of - timedelta(days=longest + 1), as_of),
        source.actuals((as_of - timedelta(days=longest)).astimezone(tz).date(), today),
    )
    # Everything below sees only what was published by as-of.
    seen = visible_at(as_of, raw_forecasts, raw_actuals)

    pairs, unpaired = _pair_with_product(seen.forecasts, seen.actuals, slot, tz)
    tomorrow_rows = _tomorrow_rows(seen.forecasts, today, slot, as_of, tz)
    band = _band(pairs, tomorrow_rows, as_of, settings)
    return DecisionView(
        tomorrow=_tomorrow(tomorrow_rows, today + timedelta(days=1), as_of, band),
        band=band,
        windows=[
            _score(pairs, unpaired, as_of, days, tz, settings.sim_first_day)
            for days in settings.windows_days
        ],
        history=_history(pairs, as_of, max(settings.windows_days)),
    )


def _tomorrow_rows(
    forecasts: Sequence[ForecastRow], today: date, slot: time, as_of: datetime, tz: ZoneInfo
) -> list[ForecastRow]:
    """Tomorrow's hourly values from the publish at as-of, or an error if incomplete."""
    start = datetime.combine(today + timedelta(days=1), time(0), tzinfo=tz)
    end = start + timedelta(days=1)
    hours = sorted(
        (r for r in forecasts if r.publish_time == as_of and start <= r.start_time < end),
        key=lambda r: r.start_time,
    )
    # Count hours in UTC so a 23- or 25-hour clock-change day is measured correctly.
    expected = (end.astimezone(UTC) - start.astimezone(UTC)) // timedelta(hours=1)
    if len(hours) != expected:
        raise ForecastUnavailableError(
            f"Elexon has {len(hours)} of {expected} hours for {start.date()} "
            f"in the {slot:%H:%M} publish on {today}"
        )
    return hours


def _band(
    pairs: Sequence[_Pair], tomorrow: Sequence[ForecastRow], as_of: datetime, settings: Settings
) -> Band | None:
    """Spread of the band window's misses. Always its own window, whatever the scoring
    windows are: a band promising 8 in 10 needs enough history to keep that promise."""
    start = as_of - timedelta(days=settings.band_window_days)
    misses = [p.miss_mw for p in pairs if start <= p.start_time < as_of]
    if not misses:
        return None
    lower = scoring.percentile(misses, settings.band_lower_pct)
    upper = scoring.percentile(misses, settings.band_upper_pct)
    return Band(
        window_days=settings.band_window_days,
        half_hours=len(misses),
        lower_pct=settings.band_lower_pct,
        upper_pct=settings.band_upper_pct,
        lower_miss_mw=lower,
        upper_miss_mw=upper,
        clipped_at_zero=any(r.generation_mw - upper < 0 for r in tomorrow),
    )


def _tomorrow(
    hours: Sequence[ForecastRow], delivery_day: date, as_of: datetime, band: Band | None
) -> Tomorrow:
    lowest = min(hours, key=lambda r: r.generation_mw)
    highest = max(hours, key=lambda r: r.generation_mw)
    return Tomorrow(
        delivery_day=delivery_day,
        publish_time=as_of,
        hours=[_with_band(r, band) for r in hours],
        # Each value is MW held for one hour, so MW sums straight to MWh.
        total_mwh=sum(r.generation_mw for r in hours),
        low=Extreme(mw=lowest.generation_mw, start_time=lowest.start_time),
        high=Extreme(mw=highest.generation_mw, start_time=highest.start_time),
    )


def _with_band(row: ForecastRow, band: Band | None) -> HourForecast:
    if band is None:
        return HourForecast(
            start_time=row.start_time,
            forecast_mw=row.generation_mw,
            band_low_mw=None,
            band_high_mw=None,
        )
    # A big miss subtracted from a small forecast would mean negative wind: hold at 0.
    return HourForecast(
        start_time=row.start_time,
        forecast_mw=row.generation_mw,
        band_low_mw=max(0.0, row.generation_mw - band.upper_miss_mw),
        band_high_mw=max(0.0, row.generation_mw - band.lower_miss_mw),
    )


def _pair_with_product(
    forecasts: Sequence[ForecastRow], actuals: Sequence[ActualRow], slot: time, tz: ZoneInfo
) -> tuple[list[_Pair], list[datetime]]:
    """Match each half-hour with the slot publish from the day before it, held flat over
    the hour: the 10:00 forecast value covers both 10:00 and 10:30.

    Returns the pairs, plus the start times that had no product forecast to pair with."""
    by_key = {(r.publish_time, r.start_time): r.generation_mw for r in forecasts}
    pairs: list[_Pair] = []
    unpaired: list[datetime] = []
    for actual in actuals:
        day = actual.start_time.astimezone(tz).date()
        product = datetime.combine(day - timedelta(days=1), slot, tzinfo=tz).astimezone(UTC)
        hour = actual.start_time.astimezone(UTC).replace(minute=0)
        forecast = by_key.get((product, hour))
        if forecast is None:
            unpaired.append(actual.start_time)
        else:
            pairs.append(_Pair(actual.start_time, forecast, actual.generation_mw))
    return sorted(pairs, key=lambda p: p.start_time), unpaired


def _score(
    pairs: Sequence[_Pair],
    unpaired: Sequence[datetime],
    as_of: datetime,
    days: int,
    tz: ZoneInfo,
    sim_first_day: date,
) -> WindowMetrics:
    start = as_of - timedelta(days=days)
    first_day = start.astimezone(tz).date()
    in_window = [p for p in pairs if start <= p.start_time < as_of]
    misses = [p.miss_mw for p in in_window]
    unscored = sum(1 for t in unpaired if start <= t < as_of)
    direction = scoring.direction_agreement(_hourly_moves(in_window, tz))
    has_misses = bool(misses)
    return WindowMetrics(
        days=days,
        half_hours=len(misses),
        unscored_half_hours=unscored,
        days_before_sim_start=max(0, (sim_first_day - first_day).days),
        mae_mw=scoring.mae(misses) if has_misses else None,
        rmse_mw=scoring.rmse(misses) if has_misses else None,
        bias_mw=scoring.bias(misses) if has_misses else None,
        mda_pct=direction.pct,
        mda_moves=direction.scored,
        mda_flat_skipped=direction.flat_skipped,
    )


def _history(pairs: Sequence[_Pair], as_of: datetime, days: int) -> list[HistoryPoint]:
    start = as_of - timedelta(days=days)
    return [
        HistoryPoint(
            start_time=p.start_time,
            forecast_mw=p.forecast_mw,
            actual_mw=p.actual_mw,
            miss_mw=p.miss_mw,
        )
        for p in pairs
        if start <= p.start_time < as_of
    ]


def _hourly_moves(pairs: Sequence[_Pair], tz: ZoneInfo) -> list[tuple[float, float]]:
    """(forecast change, actual change) between consecutive complete hours of one day.

    The forecast only moves hourly, so direction is judged per hour. An hour counts
    only when both of its half-hours are scored; its actual is their mean. Moves never
    cross midnight, because the two hours would come from different publishes."""
    halves: defaultdict[datetime, list[_Pair]] = defaultdict(list)
    for p in pairs:
        halves[p.start_time.astimezone(UTC).replace(minute=0)].append(p)
    hours = {
        hour: (pair[0].forecast_mw, (pair[0].actual_mw + pair[1].actual_mw) / 2)
        for hour, pair in halves.items()
        if len(pair) == 2
    }
    moves: list[tuple[float, float]] = []
    for hour, (forecast, actual) in sorted(hours.items()):
        previous = hour - timedelta(hours=1)
        if previous not in hours:
            continue
        if previous.astimezone(tz).date() != hour.astimezone(tz).date():
            continue
        prev_forecast, prev_actual = hours[previous]
        moves.append((forecast - prev_forecast, actual - prev_actual))
    return moves
