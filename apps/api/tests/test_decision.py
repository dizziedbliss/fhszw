from datetime import date, datetime, time

import pytest

from tests.builders import FakeSource, at, metered, publish, slot_publishes
from wind.decision import ForecastUnavailableError, build_decision
from wind.models import ActualRow, ForecastRow
from wind.settings import Settings

pytestmark = pytest.mark.anyio

SETTINGS = Settings(windows_days=(1,), band_window_days=1)


async def test_tomorrow_is_the_whole_next_day_from_the_publish_at_the_chosen_slot() -> None:
    # The 09:30 publish on Jan 15 runs 21:00 Jan 14 -> 21:00 Jan 17, like the real one.
    source = FakeSource(
        forecasts=publish(at(15, 9, 30), first=at(14, 21), hours=73, mw=lambda t: t.hour * 100)
    )

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    assert [h.start_time for h in view.tomorrow.hours] == [at(16, h) for h in range(24)]
    assert [h.forecast_mw for h in view.tomorrow.hours] == list(range(0, 2400, 100))


async def test_tomorrow_summarises_total_energy_and_its_lowest_and_highest_hours() -> None:
    # 500 MW at 06:00, rising 100 MW per hour away from it. Hours 0..23 sit
    # 174 hour-steps from 06:00 in total, so energy = 24*500 + 174*100 MWh.
    source = FakeSource(
        forecasts=publish(
            at(15, 9, 30), first=at(14, 21), hours=73, mw=lambda t: 500 + 100 * abs(t.hour - 6)
        )
    )

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    summary = view.tomorrow
    assert (summary.delivery_day, summary.publish_time) == (date(2026, 1, 16), at(15, 9, 30))
    assert summary.total_mwh == 29_400
    assert (summary.low.mw, summary.low.start_time) == (500, at(16, 6))
    assert (summary.high.mw, summary.high.start_time) == (2_200, at(16, 23))


@pytest.mark.parametrize(
    "forecasts",
    [
        pytest.param([], id="no publish at the slot"),
        pytest.param(publish(at(15, 7, 30), at(14, 21), 73, 1000), id="only an earlier slot"),
        pytest.param(publish(at(15, 9, 30), at(14, 21), 48, 1000), id="stops at 21:00 tomorrow"),
    ],
)
async def test_tomorrow_without_a_complete_publish_at_the_slot_is_an_error_not_a_fallback(
    forecasts: list[ForecastRow],
) -> None:
    with pytest.raises(ForecastUnavailableError):
        await build_decision(date(2026, 1, 15), time(9, 30), FakeSource(forecasts), SETTINGS)


async def test_a_window_scores_each_half_hour_against_the_slot_publish_from_the_day_before() -> (
    None
):
    # Window Jan 14 09:30 -> Jan 15 09:30. Forecasts are all 1000 MW.
    # Jan 14 09:30..23:30: 29 half-hours metered 900  -> miss +100 each
    # Jan 15 00:00..09:00: 19 half-hours metered 1300 -> miss -300 each
    actuals = metered(at(14, 9, 30), 29, 900) + metered(at(15, 0), 19, 1300)
    source = FakeSource(slot_publishes(range(13, 16)), actuals)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    [window] = view.windows
    assert (window.days, window.half_hours) == (1, 48)
    assert window.mae_mw == pytest.approx(179.167, abs=1e-3)  # (29*100 + 19*300) / 48
    assert window.bias_mw == pytest.approx(-58.333, abs=1e-3)  # (29*100 - 19*300) / 48
    assert window.rmse_mw == pytest.approx(204.124, abs=1e-3)  # sqrt((29*100^2 + 19*300^2) / 48)


async def test_a_window_with_nothing_to_score_reports_no_numbers_and_says_so() -> None:
    source = FakeSource(slot_publishes(range(13, 16)), actuals=[])

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    [window] = view.windows
    assert (window.half_hours, window.mae_mw, window.rmse_mw, window.bias_mw) == (
        0,
        None,
        None,
        None,
    )


async def test_nothing_published_after_as_of_can_change_anything() -> None:
    clean_forecasts = slot_publishes(range(13, 16))
    clean_actuals = metered(at(14, 9, 30), 29, 900) + metered(at(15, 0), 18, 1300)  # to 08:30
    poison_forecasts = publish(at(15, 9, 31), first=at(14, 21), hours=73, mw=999_999)
    poison_actuals = [
        # The 09:00 half-hour started before 09:30 but Elexon only published it at 09:31.
        ActualRow(publish_time=at(15, 9, 31), start_time=at(15, 9), generation_mw=999_999),
        # This afternoon: real in the historical API, impossible to know at 09:30.
        *metered(at(15, 9, 30), 29, 999_999),
    ]

    clean = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(clean_forecasts, clean_actuals), SETTINGS
    )
    poisoned = await build_decision(
        date(2026, 1, 15),
        time(9, 30),
        FakeSource(clean_forecasts + poison_forecasts, clean_actuals + poison_actuals),
        SETTINGS,
    )

    assert poisoned.model_dump_json() == clean.model_dump_json()


async def test_viewing_an_earlier_slot_scores_that_slot_and_ends_the_window_there() -> None:
    # Three publishes a day that disagree; only the 07:30 ones may be scored at 07:30.
    forecasts = (
        slot_publishes(range(13, 16), 7, 30, mw=1000)
        + slot_publishes(range(13, 16), 9, 30, mw=5000)
        + slot_publishes(range(13, 15), 15, 30, mw=9000)
    )
    source = FakeSource(forecasts, metered(at(14, 0), 96, 900))

    view = await build_decision(date(2026, 1, 15), time(7, 30), source, SETTINGS)

    [window] = view.windows
    assert window.mae_mw == 100  # every half-hour 1000 vs 900
    assert window.half_hours == 48  # Jan 14 07:30 -> Jan 15 07:00


async def test_half_hours_whose_product_publish_is_missing_are_left_out_and_counted() -> None:
    # No Jan 13 09:30 publish, so Jan 14 09:30..23:30 (29 half-hours) can't be scored fairly.
    actuals = metered(at(14, 9, 30), 29, 900) + metered(at(15, 0), 19, 1300)
    source = FakeSource(slot_publishes(range(14, 16)), actuals)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    [window] = view.windows
    assert (window.half_hours, window.unscored_half_hours) == (19, 29)
    assert window.bias_mw == -300  # only the Jan 15 morning remains


async def test_direction_is_judged_hour_to_hour_within_a_day_on_complete_hours_only() -> None:
    def jan14_actual(t: datetime) -> int:
        # Rises 10 MW/hour until 17:00, then falls 10 MW/hour.
        return 1000 + 10 * min(t.hour, 17) - 10 * max(0, t.hour - 17)

    forecasts = (
        publish(at(13, 9, 30), first=at(12, 21), hours=73, mw=lambda t: 10 * t.hour)  # rising
        + publish(at(14, 9, 30), first=at(13, 21), hours=73, mw=1000)  # flat
        + publish(at(15, 9, 30), first=at(14, 21), hours=73, mw=1000)
    )
    actuals = metered(at(14, 9, 30), 29, jan14_actual) + metered(at(15, 0), 19, 1300)
    source = FakeSource(forecasts, actuals)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, SETTINGS)

    [window] = view.windows
    # Jan 14: complete hours 10..23 -> 13 moves, forecast always up, actual up for 7.
    #   (09:00 is half outside the window; the move across midnight mixes two publishes.)
    # Jan 15: complete hours 00..08 -> 8 moves, forecast flat -> skipped, not scored.
    #   (09:00's second half isn't published until 10:00.)
    assert (window.mda_moves, window.mda_flat_skipped) == (13, 8)
    assert window.mda_pct == pytest.approx(53.846, abs=1e-3)  # 7 of 13


async def test_band_shows_where_tomorrow_lands_if_it_misses_like_the_past_did() -> None:
    # Past misses: 29 x +100 and 19 x -300  ->  P10 = -300, P90 = +100.
    # Tomorrow's forecast is 1000 MW, except a 50 MW dip at 03:00.
    forecasts = slot_publishes(range(13, 15)) + publish(
        at(15, 9, 30), first=at(14, 21), hours=73, mw=lambda t: 50 if t == at(16, 3) else 1000
    )
    actuals = metered(at(14, 9, 30), 29, 900) + metered(at(15, 0), 19, 1300)

    view = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(forecasts, actuals), SETTINGS
    )

    assert view.band is not None
    assert (view.band.lower_miss_mw, view.band.upper_miss_mw) == (-300, 100)
    hours = {h.start_time: h for h in view.tomorrow.hours}
    assert (hours[at(16, 0)].band_low_mw, hours[at(16, 0)].band_high_mw) == (900, 1300)
    # 50 - 100 would be negative generation, so the low edge stops at 0 and says so.
    assert (hours[at(16, 3)].band_low_mw, hours[at(16, 3)].band_high_mw) == (0, 350)
    assert view.band.clipped_at_zero is True


async def test_band_uses_its_own_window_whatever_the_scoring_windows_are() -> None:
    settings = Settings(windows_days=(1,), band_window_days=2)
    actuals = metered(at(13, 9, 30), 96, 900)  # Jan 13 09:30 -> Jan 15 09:00

    view = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(slot_publishes(range(12, 16)), actuals), settings
    )

    assert view.band is not None
    assert (view.band.window_days, view.band.half_hours) == (2, 96)
    assert view.windows[0].half_hours == 48


async def test_without_past_misses_there_is_no_band_rather_than_a_made_up_one() -> None:
    view = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(slot_publishes(range(13, 16))), SETTINGS
    )

    assert view.band is None
    assert {(h.band_low_mw, h.band_high_mw) for h in view.tomorrow.hours} == {(None, None)}


async def test_history_lists_every_scored_half_hour_of_the_longest_window_in_order() -> None:
    settings = Settings(windows_days=(1, 2), band_window_days=1)
    actuals = metered(at(13, 9, 30), 96, 900)  # Jan 13 09:30 -> Jan 15 09:00

    view = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(slot_publishes(range(12, 16)), actuals), settings
    )

    first, last = view.history[0], view.history[-1]
    assert len(view.history) == 96
    assert (first.start_time, first.forecast_mw, first.actual_mw, first.miss_mw) == (
        at(13, 9, 30),
        1000,
        900,
        100,
    )
    assert last.start_time == at(15, 9)


async def test_each_window_says_how_many_of_its_days_fall_before_the_simulation_starts() -> None:
    settings = Settings(windows_days=(1, 3), band_window_days=1)
    source = FakeSource(slot_publishes(range(2, 3)))

    view = await build_decision(date(2026, 1, 2), time(9, 30), source, settings)

    # 1 day back from Jan 2 09:30 starts Jan 1; 3 days back starts Dec 30 (Dec 30 + 31).
    assert [w.days_before_sim_start for w in view.windows] == [0, 2]


WHOLE_DAYS = Settings(windows_days=(1,), band_window_days=1, whole_day_window_days=2)


async def test_whole_days_are_the_last_complete_days_with_their_signed_energy_miss() -> None:
    # Forecast 1000 MW every hour -> 24,000 MWh a day. Today's partial morning must not count.
    actuals = (
        metered(at(13), 48, 900)  # 21,600 MWh -> miss +2,400 (+10%)
        + metered(at(14), 48, 1100)  # 26,400 MWh -> miss -2,400 (-10%)
        + metered(at(15), 19, 1000)  # this morning, up to 09:00: not a whole day
    )
    source = FakeSource(slot_publishes(range(12, 16)), actuals)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, WHOLE_DAYS)

    assert [
        (d.day, d.forecast_mwh, d.actual_mwh, d.miss_mwh, d.miss_pct) for d in view.whole_days.days
    ] == [
        (date(2026, 1, 13), 24_000, 21_600, 2_400, 10),
        (date(2026, 1, 14), 24_000, 26_400, -2_400, -10),
    ]


def two_days_missing_by(jan13_actual_mw: int, jan14_actual_mw: int) -> FakeSource:
    actuals = metered(at(13), 48, jan13_actual_mw) + metered(at(14), 48, jan14_actual_mw)
    return FakeSource(slot_publishes(range(12, 16)), actuals)


async def test_whole_days_report_their_average_miss_in_mwh_and_as_a_share_of_forecast() -> None:
    # Misses +2,400 and +1,200 MWh on 24,000 MWh days: average +1,800; 3,600 / 48,000 = 7.5%
    source = two_days_missing_by(900, 950)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, WHOLE_DAYS)

    assert (view.whole_days.average_miss_mwh, view.whole_days.average_miss_pct) == (1_800, 7.5)


async def test_eight_in_ten_of_the_past_day_misses_applied_to_tomorrows_total() -> None:
    # Misses 1,200 and 2,400: P10 = 1,320, P90 = 2,280. Tomorrow's forecast is 24,000 MWh.
    view = await build_decision(
        date(2026, 1, 15), time(9, 30), two_days_missing_by(900, 950), WHOLE_DAYS
    )

    days = view.whole_days
    assert (days.lower_pct, days.upper_pct) == (10, 90)
    assert (days.lower_miss_mwh, days.upper_miss_mwh) == pytest.approx((1_320, 2_280))
    assert (days.tomorrow_low_mwh, days.tomorrow_high_mwh) == pytest.approx((21_720, 22_680))
    assert days.clipped_at_zero is False


async def test_a_day_missing_any_half_hour_is_left_out_of_whole_days_and_counted() -> None:
    # Jan 13 is one half-hour short (47 of 48 metered), so it can't be a whole day.
    actuals = metered(at(13), 47, 900) + metered(at(14), 48, 1100)
    source = FakeSource(slot_publishes(range(12, 16)), actuals)

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, WHOLE_DAYS)

    assert [d.day for d in view.whole_days.days] == [date(2026, 1, 14)]
    assert view.whole_days.skipped_days == 1


async def test_with_no_whole_days_there_is_no_range_rather_than_a_made_up_one() -> None:
    source = FakeSource(slot_publishes(range(12, 16)), metered(at(15), 19, 1000))

    view = await build_decision(date(2026, 1, 15), time(9, 30), source, WHOLE_DAYS)

    days = view.whole_days
    assert (days.days, days.skipped_days, days.average_miss_mwh, days.tomorrow_low_mwh) == (
        [],
        2,
        None,
        None,
    )


async def test_the_day_range_never_goes_below_zero_energy_and_says_when_it_was_held() -> None:
    # Tomorrow is a calm 50 MW all day (1,200 MWh), but past days missed by ~2,000 MWh.
    forecasts = slot_publishes(range(12, 15)) + publish(at(15, 9, 30), at(14, 21), 73, 50)
    actuals = metered(at(13), 48, 900) + metered(at(14), 48, 950)
    view = await build_decision(
        date(2026, 1, 15), time(9, 30), FakeSource(forecasts, actuals), WHOLE_DAYS
    )

    assert view.whole_days.tomorrow_low_mwh == 0
    assert view.whole_days.clipped_at_zero is True
