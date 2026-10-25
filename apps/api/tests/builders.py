"""Test data builders. January is GMT, so UTC here equals UK time."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta

from wind.models import ActualRow, ForecastRow

type MwRule = int | Callable[[datetime], int]


def at(day: int, hour: int = 0, minute: int = 0, month: int = 1, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _mw(rule: MwRule, t: datetime) -> int:
    return rule if isinstance(rule, int) else rule(t)


def publish(published: datetime, first: datetime, hours: int, mw: MwRule) -> list[ForecastRow]:
    """One WINDFOR publish: hourly values starting at `first`."""
    return [
        ForecastRow(
            publish_time=published,
            start_time=first + timedelta(hours=h),
            generation_mw=_mw(mw, first + timedelta(hours=h)),
        )
        for h in range(hours)
    ]


def metered(first: datetime, half_hours: int, mw: MwRule) -> list[ActualRow]:
    """FUELHH half-hours starting at `first`; each is published 30 minutes after it starts."""
    rows: list[ActualRow] = []
    for k in range(half_hours):
        start = first + timedelta(minutes=30 * k)
        rows.append(
            ActualRow(
                publish_time=start + timedelta(minutes=30),
                start_time=start,
                generation_mw=_mw(mw, start),
            )
        )
    return rows


class FakeSource:
    """In-memory Elexon. Ignores the requested ranges on purpose: like the real
    historical API, it can hand over rows the decision maker couldn't have seen yet."""

    def __init__(
        self, forecasts: Sequence[ForecastRow] = (), actuals: Sequence[ActualRow] = ()
    ) -> None:
        self._forecasts = list(forecasts)
        self._actuals = list(actuals)

    async def forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastRow]:
        return self._forecasts

    async def actuals(self, settlement_from: date, settlement_to: date) -> list[ActualRow]:
        return self._actuals
