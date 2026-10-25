"""ElexonSource: the real Source, over the public BMRS Insights API (no key needed)."""

from datetime import UTC, date, datetime

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from wind.models import ActualRow, ForecastRow


class ElexonError(Exception):
    """Elexon couldn't give us usable data: network, timeout, bad status or bad payload."""


class _WindforRow(BaseModel):
    publishTime: datetime
    startTime: datetime
    generation: int


class _FuelhhRow(BaseModel):
    publishTime: datetime
    startTime: datetime
    fuelType: str
    generation: int


_WINDFOR = TypeAdapter(list[_WindforRow])
_FUELHH = TypeAdapter(list[_FuelhhRow])


def _utc(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonSource:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastRow]:
        body = await self._get(
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": _utc(publish_from), "publishDateTimeTo": _utc(publish_to)},
        )
        return [
            ForecastRow(
                publish_time=r.publishTime, start_time=r.startTime, generation_mw=r.generation
            )
            for r in _parse(_WINDFOR, body, "WINDFOR")
        ]

    async def actuals(self, settlement_from: date, settlement_to: date) -> list[ActualRow]:
        body = await self._get(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": settlement_from.isoformat(),
                "settlementDateTo": settlement_to.isoformat(),
                "fuelType": "WIND",
            },
        )
        rows = _parse(_FUELHH, body, "FUELHH")
        other = {r.fuelType for r in rows} - {"WIND"}
        if other:
            # Quietly dropping them would hide an API change that corrupts the actuals.
            raise ElexonError(f"Elexon sent FUELHH rows for {sorted(other)} when asked for WIND")
        return [
            ActualRow(
                publish_time=r.publishTime, start_time=r.startTime, generation_mw=r.generation
            )
            for r in rows
        ]

    async def _get(self, path: str, params: dict[str, str]) -> bytes:
        try:
            response = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as error:
            raise ElexonError(f"couldn't reach Elexon for {path}: {error!r}") from error
        if not response.is_success:
            raise ElexonError(
                f"Elexon answered {response.status_code} for {path}: {response.text[:200]}"
            )
        return response.content


def _parse[Row: BaseModel](adapter: TypeAdapter[list[Row]], body: bytes, dataset: str) -> list[Row]:
    try:
        return adapter.validate_json(body)
    except ValidationError as error:
        raise ElexonError(f"Elexon sent {dataset} data in an unexpected shape: {error}") from error
