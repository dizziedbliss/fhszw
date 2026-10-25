# fhszw: wind day-ahead decision screen

A January 2026 simulation for a UK supplier with a wind deal. He picks "today", and the screen shows tomorrow's Elexon wind forecast as it looked that morning, plus how accurate that same forecast has been. Data only, never advice.

## Commands

- `make install`: `uv sync --frozen` (api) + `npm ci` (web).
- `make check`: ruff, ruff format, pyright, pytest (including one **live Elexon** test, so it needs the internet), a check that the generated TS types match the API, oxlint, tsc, vitest, vite build. A stage is done only when this passes. Offline: `cd apps/api && uv run pytest -m "not live"`.
- `make api-types`: regenerate `apps/web/src/api/` from the API's OpenAPI schema. Run it after changing any response model.
- `make dev`: `docker compose --profile dev up`. Web at http://localhost:5173, API at http://localhost:8000/api/docs.
- Without Docker: `cd apps/api && uv run fastapi dev` and `cd apps/web && npm run dev`.
- Engine from the terminal (live Elexon): `cd apps/api && uv run python -m wind.cli 2026-01-15 09:30` prints the full decision view as JSON.

## Architecture

- `apps/api`: FastAPI on Python 3.14, managed by uv (`uv.lock`).
  - `main.py` holds `app = create_app()` (the entrypoint is declared in `pyproject.toml` under `[tool.fastapi]`).
  - Every route lives under `/api`, including `/api/openapi.json` and `/api/docs`, because Vercel forwards `/api/*` with the prefix intact.
  - `wind/` is the domain package. Its one front door is `decision.build_decision(today, slot, source, settings) -> DecisionView`, and callers never see what's behind it:
    - `source.py`: the `Source` protocol (`forecasts(publish_from, publish_to)`, `actuals(settlement_from, settlement_to)`).
    - `elexon.py`: `ElexonSource`, the real Source over the BMRS Insights API. Every failure (network, timeout, non-2xx, bad shape, non-WIND rows) raises `ElexonError`.
    - `barrier.py`: `behind_barrier(source, as_of)` is a bouncer that wraps any Source and refuses rows published after as-of. `build_decision` wraps its source with it as the first step, so unfiltered rows never enter the engine.
    - `track_record.py`: `TrackRecord` pairs every visible past half-hour with its product forecast (held flat over the hour). `.last(days)` returns a `Window` (scored half-hours, unscored count, days before the sim start). The "last N days" rule lives only here.
    - `scoring.py`: pure formulas (MAE, RMSE, bias, linear percentile, direction agreement).
    - `models.py`: input rows (dataclasses) and the `DecisionView` output (pydantic, becoming the API schema).
    - `settings.py`: every operational value, overridable via `WIND_*` env vars.
    - `cli.py`: prints `DecisionView` JSON for a day and slot.
    - `api.py`: `create_app(settings, source, clock)`; tests inject fakes for the last two.
      - `GET /api/decision?today=YYYY-MM-DD&slot=HH:MM` returns `DecisionView` plus `fetched_at`. Success is `Cache-Control: public, max-age=300, s-maxage=31536000`.
      - Errors are always `{"detail": "<sentence>"}` with `no-store`: 422 bad input, 404 missing publish, 502 Elexon failed (the reason is logged).
      - `GET /api/health` probes one known publish and returns 200 `ok` or 503 `degraded`, plus an Elexon failure counter for the instance.
      - An httpx client is opened per request, because serverless runtimes don't reliably run startup hooks.
  - Tests are in `tests/`. Agreed seams: `build_decision` (with `FakeSource`), `ElexonSource` (with httpx `MockTransport`), `scoring` (pure), and a golden test running recorded real Elexon data (`tests/fixtures/`) through both, against numbers from an independent script.
- `apps/web`: Vite + React 19 + TypeScript.
  - One screen (`App.tsx`):
    - **Header:** wordmark and the 09:50 gate.
    - **Hero sentence with the two `<select>`s** (`Controls`). The choice lives in the URL (`?today=&slot=`), so links can be shared and Back works.
    - **`Tomorrow`:** summary sentence, then a Chart ⇄ Table switch (`ForecastChart`, hourly steps plus the band), then the band caption.
    - **`Accuracy`:** a 7d | 14d scorecard with each metric's meaning, plus notes on skipped half-hours and December days.
    - **`History`:** a length switch built from the API's windows, then Chart ⇄ Table (`HistoryChart`, two pens), newest first.
    - **Footer:** sources and fetch time.
  - `useDecision` fetches via `api.ts`. Loading is derived, never stored. Errors show the API's sentence plus *Try again*.
  - `format.ts` is the only place numbers, signs and UK times are formatted (Intl, `Europe/London`, non-breaking spaces, real minus sign).
  - `simulation.ts` holds the offered days, slots and gate time. The API stays the authority.
  - Styling: CSS Modules plus `tokens.css` (chart-recorder palette, light and dark via `prefers-color-scheme`, validated for colour-blind separation and AA contrast). Font: self-hosted Atkinson Hyperlegible Next, with `tabular-nums` everywhere.
  - Tests (Vitest + Testing Library) use two seams: the whole page with only the network faked (`src/test/fake-api.ts`, serving a real recorded Jan 15 response), and `format.ts`. Chart pixels aren't unit-tested.
  - `@playwright/test` is installed but has no tests yet.
  - `src/api/` is **generated** (`@hey-api/openapi-ts`, types only). Never edit it by hand. `package.json` overrides `js-yaml` to 4.3.2 to patch an advisory in the generator's dependency.
  - The dev server binds `0.0.0.0:5173` via the `--host` flag in `npm run dev`, not via config: Vite drops a config-file host when it restarts after a config change and proxies `/api` to `API_PROXY_TARGET` (default `http://localhost:8000`; in compose, `http://api-dev:8000`).
- `compose.yaml`: `dev` profile with `api-dev` (uv image, `fastapi dev`) and `web-dev` (node image, `vite`). Source is bind-mounted; deps live in named volumes.

## Conventions

- Tests come first for any logic (red-green). Every piece of code gets tests.
- Dependencies are pinned. Python: `uv.lock` with `--frozen`. JS: exact versions (`.npmrc` `save-exact`) and `npm ci`. Docker images are pinned to exact tags.
- Python: ruff (lint + format) and pyright strict. TypeScript: `strict`, `noUncheckedIndexedAccess`, oxlint with `--deny-warnings`. No `any`.
- Operational values (windows, percentiles, slots, URLs, timeouts, cache ages) are settings, never literals.
- Never swallow an error. Elexon failures surface as visible errors, never as empty or fake data.
- Numbers: error = forecast − actual, so positive means the forecast was too high. Signed numbers always carry words ("forecast higher").
- Times are shown in UK time (`Europe/London`, 24h).
- UI copy is sentence case, with typographic apostrophes (ruff allows `’`), and `…` for in-progress states.

## Glossary

- **Today / decision day (D):** the simulated day he's deciding on, Jan 1–31 2026.
- **Tomorrow / delivery day (D+1):** the day he's buying power for.
- **Slot:** a WINDFOR publish time he can view as of: 02:30, 04:30, 07:30 or 09:30. The GB day-ahead gate (N2EX) closes at 09:50.
- **As-of:** D at the chosen slot. Nothing published after it is visible or used.
- **Product:** the forecast from the same slot on the day before a given half-hour. It's what gets scored.
- **Half-hour:** one FUELHH settlement period (average MW). The hourly forecast is held flat across both half-hours of its hour.
- **Miss:** forecast − actual for one half-hour.
- **Track record:** every visible past half-hour with its actual and its product forecast (or none, if that publish is missing). Windows are slices of it.
- **Window:** the rolling 7 or 14 days of half-hours ending at as-of: `track_record.last(7)`.
- **Band:** tomorrow's forecast minus the P90/P10 of the last 14 days' misses, i.e. "8 in 10 past half-hours landed in this range".

## Not built (deliberately)

- Showing tomorrow's actuals, or any back-test view (they don't exist at decision time).
- Buy/sell suggestions or any nudging copy.
- Dates outside January 2026.
- A database: the data is public, immutable Elexon history.
