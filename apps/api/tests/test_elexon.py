from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import httpx
import pytest

from tests.builders import at
from wind.elexon import ElexonError, ElexonSource
from wind.models import ActualRow, ForecastRow

pytestmark = pytest.mark.anyio

BASE = "https://elexon.test/bmrs/api/v1"

# Real rows from the Jan 15 09:30 publish (one row of the publish, trimmed).
WINDFOR_ROWS = [
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-15T09:30:00Z",
        "startTime": "2026-01-16T00:00:00Z",
        "generation": 7472,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-15T09:30:00Z",
        "startTime": "2026-01-16T01:00:00Z",
        "generation": 7039,
    },
]

# Real FUELHH wind rows for Jan 15 (Elexon returns newest first).
FUELHH_ROWS = [
    {
        "dataset": "FUELHH",
        "publishTime": "2026-01-15T01:00:00Z",
        "startTime": "2026-01-15T00:30:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 2,
        "fuelType": "WIND",
        "generation": 14311,
    },
    {
        "dataset": "FUELHH",
        "publishTime": "2026-01-15T00:30:00Z",
        "startTime": "2026-01-15T00:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 1,
        "fuelType": "WIND",
        "generation": 14602,
    },
]


def serving(path: str, body: Any, seen: list[httpx.Request]) -> ElexonSource:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path != httpx.URL(BASE + path).path:
            return httpx.Response(404)
        return httpx.Response(200, json=body)

    return ElexonSource(httpx.AsyncClient(transport=httpx.MockTransport(handle)), BASE)


async def test_forecasts_ask_for_the_windfor_stream_by_publish_time_and_parse_rows() -> None:
    seen: list[httpx.Request] = []
    source = serving("/datasets/WINDFOR/stream", WINDFOR_ROWS, seen)

    rows = await source.forecasts(at(14, 9, 30), at(15, 9, 30))

    [request] = seen
    assert dict(request.url.params) == {
        "publishDateTimeFrom": "2026-01-14T09:30:00Z",
        "publishDateTimeTo": "2026-01-15T09:30:00Z",
    }
    assert rows == [
        ForecastRow(publish_time=at(15, 9, 30), start_time=at(16, 0), generation_mw=7472),
        ForecastRow(publish_time=at(15, 9, 30), start_time=at(16, 1), generation_mw=7039),
    ]


async def test_actuals_ask_for_wind_from_the_fuelhh_stream_by_settlement_day() -> None:
    seen: list[httpx.Request] = []
    source = serving("/datasets/FUELHH/stream", FUELHH_ROWS, seen)

    rows = await source.actuals(date(2026, 1, 1), date(2026, 1, 15))

    [request] = seen
    assert dict(request.url.params) == {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-15",
        "fuelType": "WIND",
    }
    assert rows == [
        ActualRow(publish_time=at(15, 1), start_time=at(15, 0, 30), generation_mw=14311),
        ActualRow(publish_time=at(15, 0, 30), start_time=at(15, 0), generation_mw=14602),
    ]


def _raise(error: type[httpx.TransportError]) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        raise error("simulated", request=request)

    return handle


FAILURES: dict[str, Callable[[httpx.Request], httpx.Response]] = {
    "server error": lambda _: httpx.Response(503, text="down for maintenance"),
    "bad request": lambda _: httpx.Response(400, json={"title": "validation errors"}),
    "timeout": _raise(httpx.ReadTimeout),
    "connection drop": _raise(httpx.ConnectError),
    "html instead of json": lambda _: httpx.Response(200, text="<html>oops</html>"),
    "wrong shape": lambda _: httpx.Response(200, json={"data": [{"generation": 1}]}),
}

CALLS: dict[str, Callable[[ElexonSource], Awaitable[object]]] = {
    "forecasts": lambda s: s.forecasts(at(14, 9, 30), at(15, 9, 30)),
    "actuals": lambda s: s.actuals(date(2026, 1, 1), date(2026, 1, 15)),
}


@pytest.mark.parametrize("call", CALLS.values(), ids=CALLS.keys())
@pytest.mark.parametrize("failure", FAILURES.values(), ids=FAILURES.keys())
async def test_any_elexon_failure_is_raised_loudly_never_returned_as_empty_data(
    failure: Callable[[httpx.Request], httpx.Response],
    call: Callable[[ElexonSource], Awaitable[object]],
) -> None:
    source = ElexonSource(httpx.AsyncClient(transport=httpx.MockTransport(failure)), BASE)

    with pytest.raises(ElexonError):
        await call(source)


async def test_actuals_refuse_rows_for_any_fuel_other_than_wind() -> None:
    nuclear = {**FUELHH_ROWS[0], "fuelType": "NUCLEAR"}
    source = serving("/datasets/FUELHH/stream", [FUELHH_ROWS[1], nuclear], [])

    with pytest.raises(ElexonError):
        await source.actuals(date(2026, 1, 15), date(2026, 1, 15))
