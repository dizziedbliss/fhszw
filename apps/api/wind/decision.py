"""build_decision: the one door. Fetching, the barrier, pairing and scoring hide behind it."""

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from wind import scoring
from wind.barrier import behind_barrier
from wind.models import (
    Band,
    DecisionView,
    Extreme,
    ForecastRow,
    HistoryPoint,
    HourForecast,
    PastDay,
    Tomorrow,
    WholeDays,
    WindowMetrics,
)
from wind.settings import Settings
from wind.source import Source
from wind.track_record import ScoredHalfHour, TrackRecord, Window


class ForecastUnavailableError(Exception):
    """The chosen slot's publish is missing or doesn't cover the whole of tomorrow."""


@dataclass(frozen=True)
class _Spread:
    """Where the band window's misses fell: tomorrow's band is forecast - upper .. - lower."""

    window: Window
    lower_pct: float
    upper_pct: float
    lower_miss_mw: float
    upper_miss_mw: float


async def build_decision(
    today: date, slot: time, source: Source, settings: Settings
) -> DecisionView:
    tz = ZoneInfo(settings.market_timezone)
    as_of = datetime.combine(today, slot, tzinfo=tz).astimezone(UTC)
    # The bouncer: from here on, nothing published after as-of can get in.
    source = behind_barrier(source, as_of)

    fetch_days = max((*settings.windows_days, settings.band_window_days))
    forecasts, actuals = await asyncio.gather(
        # One extra day: the oldest half-hours are scored against the publish before them.
        source.forecasts(as_of - timedelta(days=fetch_days + 1), as_of),
        source.actuals((as_of - timedelta(days=fetch_days)).astimezone(tz).date(), today),
    )
    record = TrackRecord(forecasts, actuals, slot, as_of, tz, settings.sim_first_day)

    spread = _spread(record.last(settings.band_window_days), settings)
    tomorrow, band = _tomorrow(forecasts, today, slot, as_of, tz, spread)
    whole_days = _whole_days(record, tomorrow.total_mwh, settings)
    return DecisionView(
        tomorrow=tomorrow,
        band=band,
        windows=[_score(record.last(days), tz) for days in settings.windows_days],
        whole_days=whole_days,
        history=_history(record.last(max(settings.windows_days))),
    )


def _spread(window: Window, settings: Settings) -> _Spread | None:
    """Spread of the band window's misses. Always its own window, whatever the scoring
    windows are: a band promising 8 in 10 needs enough history to keep that promise."""
    misses = window.misses
    if not misses:
        return None
    return _Spread(
        window=window,
        lower_pct=settings.band_lower_pct,
        upper_pct=settings.band_upper_pct,
        lower_miss_mw=scoring.percentile(misses, settings.band_lower_pct),
        upper_miss_mw=scoring.percentile(misses, settings.band_upper_pct),
    )


def _tomorrow(
    forecasts: Sequence[ForecastRow],
    today: date,
    slot: time,
    as_of: datetime,
    tz: ZoneInfo,
    spread: _Spread | None,
) -> tuple[Tomorrow, Band | None]:
    """Tomorrow from the publish at as-of, with each hour's band edges, or an error when
    that publish is missing or incomplete (never a fallback to another publish)."""
    delivery_day = today + timedelta(days=1)
    start = datetime.combine(delivery_day, time(0), tzinfo=tz)
    end = start + timedelta(days=1)
    rows = sorted(
        (r for r in forecasts if r.publish_time == as_of and start <= r.start_time < end),
        key=lambda r: r.start_time,
    )
    # Count hours in UTC so a 23- or 25-hour clock-change day is measured correctly.
    expected = (end.astimezone(UTC) - start.astimezone(UTC)) // timedelta(hours=1)
    if len(rows) != expected:
        raise ForecastUnavailableError(
            f"Elexon has {len(rows)} of {expected} hours for {delivery_day} "
            f"in the {slot:%H:%M} publish on {today}"
        )

    hours: list[HourForecast] = []
    clipped = False
    for row in rows:
        low: float | None = None
        high: float | None = None
        if spread is not None:
            raw_low = row.generation_mw - spread.upper_miss_mw
            # A big miss subtracted from a small forecast would mean negative wind: hold at 0.
            clipped = clipped or raw_low < 0
            low = max(0.0, raw_low)
            high = max(0.0, row.generation_mw - spread.lower_miss_mw)
        hours.append(
            HourForecast(
                start_time=row.start_time,
                forecast_mw=row.generation_mw,
                band_low_mw=low,
                band_high_mw=high,
            )
        )

    lowest = min(rows, key=lambda r: r.generation_mw)
    highest = max(rows, key=lambda r: r.generation_mw)
    tomorrow = Tomorrow(
        delivery_day=delivery_day,
        publish_time=as_of,
        hours=hours,
        # Each value is MW held for one hour, so MW sums straight to MWh.
        total_mwh=sum(r.generation_mw for r in rows),
        low=Extreme(mw=lowest.generation_mw, start_time=lowest.start_time),
        high=Extreme(mw=highest.generation_mw, start_time=highest.start_time),
    )
    band = (
        None
        if spread is None
        else Band(
            window_days=spread.window.days,
            half_hours=len(spread.window.scored),
            lower_pct=spread.lower_pct,
            upper_pct=spread.upper_pct,
            lower_miss_mw=spread.lower_miss_mw,
            upper_miss_mw=spread.upper_miss_mw,
            clipped_at_zero=clipped,
        )
    )
    return tomorrow, band


def _whole_days(record: TrackRecord, tomorrow_mwh: float, settings: Settings) -> WholeDays:
    days, skipped = record.whole_days(settings.whole_day_window_days)
    past = [
        PastDay(
            day=d.day,
            forecast_mwh=d.forecast_mwh,
            actual_mwh=d.actual_mwh,
            miss_mwh=d.forecast_mwh - d.actual_mwh,
            miss_pct=100 * (d.forecast_mwh - d.actual_mwh) / d.forecast_mwh,
        )
        for d in days
    ]
    misses = [p.miss_mwh for p in past]
    forecast_total = sum(p.forecast_mwh for p in past)
    lower = scoring.percentile(misses, settings.band_lower_pct) if misses else None
    upper = scoring.percentile(misses, settings.band_upper_pct) if misses else None
    raw_low = None if upper is None else tomorrow_mwh - upper
    return WholeDays(
        window_days=settings.whole_day_window_days,
        days=past,
        skipped_days=skipped,
        average_miss_mwh=scoring.bias(misses) if misses else None,
        average_miss_pct=100 * sum(misses) / forecast_total if misses else None,
        lower_pct=settings.band_lower_pct,
        upper_pct=settings.band_upper_pct,
        lower_miss_mwh=lower,
        upper_miss_mwh=upper,
        # A day can't generate negative energy: hold the edges at 0 and say so.
        tomorrow_low_mwh=None if raw_low is None else max(0.0, raw_low),
        tomorrow_high_mwh=None if lower is None else max(0.0, tomorrow_mwh - lower),
        clipped_at_zero=raw_low is not None and raw_low < 0,
    )


def _score(window: Window, tz: ZoneInfo) -> WindowMetrics:
    misses = window.misses
    direction = scoring.direction_agreement(_hourly_moves(window.scored, tz))
    has_misses = bool(misses)
    return WindowMetrics(
        days=window.days,
        half_hours=len(misses),
        unscored_half_hours=window.unscored,
        days_before_sim_start=window.days_before_sim_start,
        mae_mw=scoring.mae(misses) if has_misses else None,
        rmse_mw=scoring.rmse(misses) if has_misses else None,
        bias_mw=scoring.bias(misses) if has_misses else None,
        mda_pct=direction.pct,
        mda_moves=direction.scored,
        mda_flat_skipped=direction.flat_skipped,
    )


def _history(window: Window) -> list[HistoryPoint]:
    return [
        HistoryPoint(
            start_time=s.start_time,
            forecast_mw=s.forecast_mw,
            actual_mw=s.actual_mw,
            miss_mw=s.miss_mw,
        )
        for s in window.scored
    ]


def _hourly_moves(scored: Sequence[ScoredHalfHour], tz: ZoneInfo) -> list[tuple[float, float]]:
    """(forecast change, actual change) between consecutive complete hours of one day.

    The forecast only moves hourly, so direction is judged per hour. An hour counts
    only when both of its half-hours are scored; its actual is their mean. Moves never
    cross midnight, because the two hours would come from different publishes."""
    halves: defaultdict[datetime, list[ScoredHalfHour]] = defaultdict(list)
    for s in scored:
        halves[s.start_time.astimezone(UTC).replace(minute=0)].append(s)
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
