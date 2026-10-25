"""The boundary to Elexon. Anything with these two methods can feed the engine."""

from datetime import date, datetime
from typing import Protocol

from wind.models import ActualRow, ForecastRow


class Source(Protocol):
    async def forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastRow]:
        """WINDFOR rows published within [publish_from, publish_to]."""
        ...

    async def actuals(self, settlement_from: date, settlement_to: date) -> list[ActualRow]:
        """FUELHH wind rows for settlement days settlement_from..settlement_to."""
        ...
