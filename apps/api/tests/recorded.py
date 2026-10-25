"""Recorded real Elexon responses, served the way Elexon serves them."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads((FIXTURES / name).read_text())
    return rows


def _iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def recorded_elexon() -> httpx.MockTransport:
    """Serves the recorded rows, filtered by the request's own parameters like Elexon does."""
    windfor = _load("windfor_0930_2025-12-31_to_2026-01-15.json")
    fuelhh = _load("fuelhh_wind_2026-01-01_to_2026-01-15.json")

    def handle(request: httpx.Request) -> httpx.Response:
        q = request.url.params
        if request.url.path.endswith("/datasets/WINDFOR/stream"):
            lo, hi = _iso(q["publishDateTimeFrom"]), _iso(q["publishDateTimeTo"])
            return httpx.Response(
                200, json=[r for r in windfor if lo <= _iso(r["publishTime"]) <= hi]
            )
        if request.url.path.endswith("/datasets/FUELHH/stream"):
            lo, hi = q["settlementDateFrom"], q["settlementDateTo"]
            return httpx.Response(200, json=[r for r in fuelhh if lo <= r["settlementDate"] <= hi])
        return httpx.Response(404)

    return httpx.MockTransport(handle)
