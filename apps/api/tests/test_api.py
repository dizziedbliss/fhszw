from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from tests.builders import FailingSource, FakeSource, slot_publishes
from wind.api import create_app
from wind.settings import Settings
from wind.source import Source

SETTINGS = Settings(
    windows_days=(1,), band_window_days=1, cache_browser_max_age_s=60, cache_cdn_max_age_s=86_400
)
FETCHED = datetime(2026, 10, 25, 12, 40, tzinfo=UTC)
JAN15 = {"today": "2026-01-15", "slot": "09:30"}


def client(source: Source) -> TestClient:
    return TestClient(create_app(settings=SETTINGS, source=source, clock=lambda: FETCHED))


def test_decision_returns_the_engine_view_and_when_it_was_fetched() -> None:
    response = client(FakeSource(slot_publishes(range(13, 16)))).get("/api/decision", params=JAN15)

    assert response.status_code == 200
    body = response.json()
    assert (body["tomorrow"]["delivery_day"], body["fetched_at"]) == (
        "2026-01-16",
        "2026-10-25T12:40:00Z",
    )


def test_a_successful_answer_is_cached_long_at_the_cdn_because_january_never_changes() -> None:
    response = client(FakeSource(slot_publishes(range(13, 16)))).get("/api/decision", params=JAN15)

    assert response.headers["cache-control"] == "public, max-age=60, s-maxage=86400"


@pytest.mark.parametrize(
    ("params", "detail"),
    [
        pytest.param(
            {"today": "2026-02-01", "slot": "09:30"},
            "today must be between 2026-01-01 and 2026-01-31",
            id="outside january",
        ),
        pytest.param(
            {"today": "15/01/2026", "slot": "09:30"},
            "today must be a date like 2026-01-15",
            id="not a date",
        ),
        pytest.param(
            {"today": "2026-01-15", "slot": "10:00"},
            "slot must be one of 02:30, 04:30, 07:30, 09:30",
            id="not a publish slot",
        ),
        pytest.param(
            {"today": "2026-01-15", "slot": "half nine"},
            "slot must be one of 02:30, 04:30, 07:30, 09:30",
            id="not a time",
        ),
        pytest.param({"slot": "09:30"}, "missing query parameter: today", id="no today"),
    ],
)
def test_bad_input_gets_a_plain_sentence_and_is_never_cached(
    params: dict[str, str], detail: str
) -> None:
    response = client(FakeSource(slot_publishes(range(13, 16)))).get("/api/decision", params=params)

    assert (response.status_code, response.json()) == (422, {"detail": detail})
    assert response.headers["cache-control"] == "no-store"


def test_when_elexon_fails_he_gets_a_plain_502_and_the_logs_get_the_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = client(FailingSource("WINDFOR answered 503")).get("/api/decision", params=JAN15)

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Couldn't get data from Elexon right now. "
        "Nothing is shown rather than guessed. Try again in a minute."
    }
    assert response.headers["cache-control"] == "no-store"
    assert "WINDFOR answered 503" in caplog.text


def test_a_missing_publish_is_a_404_that_says_exactly_what_is_missing() -> None:
    no_jan15_publish = FakeSource(slot_publishes(range(13, 15)))

    response = client(no_jan15_publish).get("/api/decision", params=JAN15)

    assert (response.status_code, response.json()) == (
        404,
        {"detail": "Elexon has 0 of 24 hours for 2026-01-16 in the 09:30 publish on 2026-01-15"},
    )
    assert response.headers["cache-control"] == "no-store"


def test_health_is_ok_only_when_a_real_elexon_probe_succeeds() -> None:
    response = client(FakeSource(slot_publishes(range(2, 3)))).get("/api/health")

    assert (response.status_code, response.json()) == (
        200,
        {"status": "ok", "elexon": "up", "elexon_failures": 0},
    )
    assert response.headers["cache-control"] == "no-store"


def test_health_says_degraded_with_a_503_and_counts_every_elexon_failure() -> None:
    api = client(FailingSource())
    api.get("/api/decision", params=JAN15)  # one failure while serving a decision

    response = api.get("/api/health")  # and the probe itself fails: two in total

    assert (response.status_code, response.json()) == (
        503,
        {"status": "degraded", "elexon": "down", "elexon_failures": 2},
    )
    assert response.headers["cache-control"] == "no-store"
