"""The track record: every visible past half-hour, paired with its product forecast.

Windows are slices of it (`track_record.last(7)`), so the "last N days" rule lives
here and nowhere else.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from wind.models import ActualRow, ForecastRow


@dataclass(frozen=True)
class ScoredHalfHour:
    """One past half-hour: what the product forecast said, and what was metered."""

    start_time: datetime
    forecast_mw: int
    actual_mw: int

    @property
    def miss_mw(self) -> int:
        return self.forecast_mw - self.actual_mw


@dataclass(frozen=True)
class Window:
    """The rolling N days of half-hours ending at as-of."""

    days: int
    scored: tuple[ScoredHalfHour, ...]  # oldest first
    unscored: int  # visible half-hours whose product publish is missing
    days_before_sim_start: int  # calendar days borrowed from before the simulated month

    @property
    def misses(self) -> list[int]:
        return [s.miss_mw for s in self.scored]


class TrackRecord:
    def __init__(
        self,
        forecasts: Sequence[ForecastRow],
        actuals: Sequence[ActualRow],
        slot: time,
        as_of: datetime,
        tz: ZoneInfo,
        sim_first_day: date,
    ) -> None:
        self._as_of = as_of
        self._tz = tz
        self._sim_first_day = sim_first_day
        self._scored, self._unscored = _pair_with_product(forecasts, actuals, slot, tz)

    def last(self, days: int) -> Window:
        start = self._as_of - timedelta(days=days)

        def inside(t: datetime) -> bool:
            return start <= t < self._as_of

        first_day = start.astimezone(self._tz).date()
        return Window(
            days=days,
            scored=tuple(s for s in self._scored if inside(s.start_time)),
            unscored=sum(1 for t in self._unscored if inside(t)),
            days_before_sim_start=max(0, (self._sim_first_day - first_day).days),
        )


def _pair_with_product(
    forecasts: Sequence[ForecastRow], actuals: Sequence[ActualRow], slot: time, tz: ZoneInfo
) -> tuple[tuple[ScoredHalfHour, ...], tuple[datetime, ...]]:
    """Match each half-hour with the slot publish from the day before it, held flat over
    the hour: the 10:00 forecast value covers both 10:00 and 10:30.

    Returns the scored half-hours (oldest first), plus the start times that had no
    product forecast to pair with."""
    by_key = {(r.publish_time, r.start_time): r.generation_mw for r in forecasts}
    scored: list[ScoredHalfHour] = []
    unscored: list[datetime] = []
    for actual in actuals:
        day = actual.start_time.astimezone(tz).date()
        product = datetime.combine(day - timedelta(days=1), slot, tzinfo=tz).astimezone(UTC)
        hour = actual.start_time.astimezone(UTC).replace(minute=0)
        forecast = by_key.get((product, hour))
        if forecast is None:
            unscored.append(actual.start_time)
        else:
            scored.append(ScoredHalfHour(actual.start_time, forecast, actual.generation_mw))
    return tuple(sorted(scored, key=lambda s: s.start_time)), tuple(unscored)
