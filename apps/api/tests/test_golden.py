"""Golden check: real recorded Elexon data -> ElexonSource -> build_decision.

Expected numbers come from an independent script written from the plan's
definitions, not from this code, so this test can genuinely disagree with it."""

from datetime import date, time

import httpx
import pytest

from tests.builders import at
from tests.recorded import recorded_elexon
from wind.decision import build_decision
from wind.elexon import ElexonSource
from wind.models import DecisionView
from wind.settings import Settings

pytestmark = pytest.mark.anyio

BASE = "https://elexon.test/bmrs/api/v1"
PRODUCT_SETTINGS = Settings(
    windows_days=(7, 14), band_window_days=14, band_lower_pct=10, band_upper_pct=90
)


@pytest.fixture
async def jan15() -> DecisionView:
    async with httpx.AsyncClient(transport=recorded_elexon()) as client:
        return await build_decision(
            date(2026, 1, 15), time(9, 30), ElexonSource(client, BASE), PRODUCT_SETTINGS
        )


async def test_jan15_tomorrow_matches_the_answer_key(jan15: DecisionView) -> None:
    t = jan15.tomorrow
    assert (t.delivery_day, len(t.hours), t.total_mwh) == (date(2026, 1, 16), 24, 191_402)
    assert (t.low.mw, t.low.start_time) == (5_881, at(16, 6))
    assert (t.high.mw, t.high.start_time) == (10_850, at(16, 21))


@pytest.mark.parametrize(
    ("index", "days", "half_hours", "mae", "rmse", "bias", "mda", "moves"),
    [
        (0, 7, 336, 2200.886905, 2942.974886, 1534.035714, 62.264151, 159),
        (1, 14, 672, 2123.721726, 2703.597081, 1703.388393, 63.322884, 319),
    ],
)
async def test_jan15_windows_match_the_answer_key(
    jan15: DecisionView,
    index: int,
    days: int,
    half_hours: int,
    mae: float,
    rmse: float,
    bias: float,
    mda: float,
    moves: int,
) -> None:
    w = jan15.windows[index]
    assert (w.days, w.half_hours, w.unscored_half_hours, w.mda_moves) == (
        days,
        half_hours,
        0,
        moves,
    )
    assert (w.mae_mw, w.rmse_mw, w.bias_mw, w.mda_pct) == pytest.approx(
        (mae, rmse, bias, mda), abs=1e-5
    )


async def test_jan15_band_matches_the_answer_key(jan15: DecisionView) -> None:
    assert jan15.band is not None
    # The answer key is printed to 6 decimals; interpolation leaves float crumbs below that.
    assert (jan15.band.lower_miss_mw, jan15.band.upper_miss_mw) == pytest.approx(
        (-949.5, 4491.5), abs=1e-6
    )
    noon = next(h for h in jan15.tomorrow.hours if h.start_time == at(16, 12))
    assert noon.forecast_mw == 7_802
    assert (noon.band_low_mw, noon.band_high_mw) == pytest.approx((3310.5, 8751.5), abs=1e-6)
