"""Print the engine's answer as JSON:  uv run python -m wind.cli 2026-01-15 09:30"""

import argparse
import asyncio
from datetime import date, time

import httpx

from wind.decision import build_decision
from wind.elexon import ElexonSource
from wind.models import DecisionView
from wind.settings import Settings


async def _run(
    today: date, slot: time, settings: Settings, transport: httpx.AsyncBaseTransport | None
) -> DecisionView:
    async with httpx.AsyncClient(timeout=settings.http_timeout_s, transport=transport) as client:
        source = ElexonSource(client, settings.elexon_base_url)
        return await build_decision(today, slot, source, settings)


def main(argv: list[str] | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("today", type=date.fromisoformat, help="decision day, e.g. 2026-01-15")
    parser.add_argument("slot", type=time.fromisoformat, help="publish slot, e.g. 09:30")
    args = parser.parse_args(argv)
    view = asyncio.run(_run(args.today, args.slot, Settings(), transport))
    print(view.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
