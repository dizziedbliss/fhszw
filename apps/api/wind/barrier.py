"""The information barrier: the only way rows reach the rest of the engine.

At decision time nothing published after as-of exists yet. The historical API
happily returns it anyway, so the engine has to refuse it here, by publish time
(not start time: a half-hour can start before as-of and still be published after).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from wind.models import ActualRow, ForecastRow


@dataclass(frozen=True)
class Visible:
    as_of: datetime
    forecasts: tuple[ForecastRow, ...]
    actuals: tuple[ActualRow, ...]


def visible_at(
    as_of: datetime, forecasts: Sequence[ForecastRow], actuals: Sequence[ActualRow]
) -> Visible:
    return Visible(
        as_of=as_of,
        forecasts=tuple(r for r in forecasts if r.publish_time <= as_of),
        actuals=tuple(r for r in actuals if r.publish_time <= as_of),
    )
