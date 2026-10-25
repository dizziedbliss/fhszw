"""The HTTP layer. create_app() wires settings, an Elexon source and a clock; tests
pass fakes for the last two. Every route lives under /api (Vercel keeps the prefix)."""

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from wind.decision import ForecastUnavailableError, build_decision
from wind.elexon import ElexonError, ElexonSource
from wind.models import DecisionView
from wind.settings import Settings
from wind.source import Source

NO_STORE = {"Cache-Control": "no-store"}
ELEXON_DOWN = (
    "Couldn't get data from Elexon right now. "
    "Nothing is shown rather than guessed. Try again in a minute."
)

log = logging.getLogger("wind.api")


class DecisionResponse(DecisionView):
    # When this answer was pulled from Elexon (real time, not the simulated one).
    fetched_at: datetime


class ErrorBody(BaseModel):
    """Every error: one plain sentence the UI can show as-is."""

    detail: str


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorBody, "description": "The chosen publish is missing or incomplete"},
    422: {"model": ErrorBody, "description": "today or slot is not allowed"},
    502: {"model": ErrorBody, "description": "Elexon could not be reached or answered badly"},
}


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    elexon: Literal["up", "down"]
    # Elexon failures this instance has seen since it started (also logged).
    elexon_failures: int


def _now() -> datetime:
    return datetime.now(UTC)


def _reject(status: int, detail: str) -> HTTPException:
    # Errors are never cached: a hiccup must not stick in the CDN for a year.
    return HTTPException(status_code=status, detail=detail, headers=NO_STORE)


def _parse_today(text: str, config: Settings) -> date:
    try:
        today = date.fromisoformat(text)
    except ValueError:
        raise _reject(422, "today must be a date like 2026-01-15") from None
    if not config.sim_first_day <= today <= config.sim_last_day:
        raise _reject(
            422, f"today must be between {config.sim_first_day} and {config.sim_last_day}"
        )
    return today


def _parse_slot(text: str, config: Settings) -> time:
    allowed = ", ".join(f"{s:%H:%M}" for s in config.slots)
    try:
        slot = time.fromisoformat(text)
    except ValueError:
        raise _reject(422, f"slot must be one of {allowed}") from None
    if slot not in config.slots:
        raise _reject(422, f"slot must be one of {allowed}")
    return slot


async def _plain_validation_error(_: Request, error: Exception) -> JSONResponse:
    """FastAPI's default 422 is a nested list; the UI gets one plain sentence instead."""
    problems: list[dict[str, Any]] = (
        list(error.errors()) if isinstance(error, RequestValidationError) else []
    )
    first: dict[str, Any] = problems[0] if problems else {}
    location: tuple[Any, ...] = tuple(first.get("loc", ("request",)))
    field = str(location[-1])
    kind = str(first.get("type", ""))
    detail = (
        f"missing query parameter: {field}"
        if kind == "missing"
        else f"invalid query parameter: {field}"
    )
    return JSONResponse(status_code=422, content={"detail": detail}, headers=NO_STORE)


def create_app(
    settings: Settings | None = None,
    source: Source | None = None,
    clock: Callable[[], datetime] = _now,
) -> FastAPI:
    config = settings or Settings()
    elexon_failures = 0

    def elexon_failed(context: str, error: ElexonError) -> None:
        nonlocal elexon_failures
        elexon_failures += 1
        log.warning("elexon failure %s: %s", context, error)

    @asynccontextmanager
    async def open_source() -> AsyncGenerator[Source]:
        # One client per request: serverless runtimes don't reliably run startup hooks,
        # and successful answers are CDN-cached, so the extra connection is rare.
        if source is not None:
            yield source
            return
        async with httpx.AsyncClient(timeout=config.http_timeout_s) as http:
            yield ElexonSource(http, config.elexon_base_url)

    app = FastAPI(
        title="Wind day-ahead API",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_exception_handler(RequestValidationError, _plain_validation_error)

    @app.get("/api/decision", responses=ERROR_RESPONSES)
    async def decision(today: str, slot: str, response: Response) -> DecisionResponse:
        day = _parse_today(today, config)
        at = _parse_slot(slot, config)
        try:
            async with open_source() as elexon:
                view = await build_decision(day, at, elexon, config)
                fetched_at = clock()
        except ElexonError as error:
            elexon_failed(f"serving decision today={day} slot={slot}", error)
            raise _reject(502, ELEXON_DOWN) from error
        except ForecastUnavailableError as error:
            raise _reject(404, str(error)) from error
        response.headers["Cache-Control"] = (
            f"public, max-age={config.cache_browser_max_age_s}, "
            f"s-maxage={config.cache_cdn_max_age_s}"
        )
        return DecisionResponse(**view.model_dump(), fetched_at=fetched_at)

    @app.get("/api/health")
    async def health(response: Response) -> HealthResponse:
        # Probe one small, known publish: the first slot of the simulated month.
        probe = datetime.combine(
            config.sim_first_day, config.slots[0], tzinfo=ZoneInfo(config.market_timezone)
        )
        response.headers.update(NO_STORE)
        try:
            async with open_source() as elexon:
                rows = await elexon.forecasts(probe, probe)
            if not rows:
                raise ElexonError(f"probe publish {probe.isoformat()} came back empty")
        except ElexonError as error:
            elexon_failed("health probe", error)
            response.status_code = 503
            return HealthResponse(status="degraded", elexon="down", elexon_failures=elexon_failures)
        return HealthResponse(status="ok", elexon="up", elexon_failures=elexon_failures)

    return app
