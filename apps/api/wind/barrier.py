"""The information barrier, as a bouncer at the Source seam.

At decision time nothing published after as-of exists yet. The historical API
happily returns it anyway, so build_decision wraps its source in this first thing:
rows published after as-of are refused on the way in and never reach the engine.
The cut is by publish time, not start time: a half-hour can start before as-of and
still be published after it.
"""

from datetime import date, datetime

from wind.models import ActualRow, ForecastRow
from wind.source import Source


class _Barrier:
    def __init__(self, source: Source, as_of: datetime) -> None:
        self._source = source
        self._as_of = as_of

    async def forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastRow]:
        rows = await self._source.forecasts(publish_from, publish_to)
        return [r for r in rows if r.publish_time <= self._as_of]

    async def actuals(self, settlement_from: date, settlement_to: date) -> list[ActualRow]:
        rows = await self._source.actuals(settlement_from, settlement_to)
        return [r for r in rows if r.publish_time <= self._as_of]


def behind_barrier(source: Source, as_of: datetime) -> Source:
    """The same Source, minus anything published after as_of."""
    return _Barrier(source, as_of)
