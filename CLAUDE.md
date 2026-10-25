# fhszw

A January 2026 simulation of the 09:30 read before the GB day-ahead gate (09:50). Pick a day as "today", and the screen shows tomorrow's Elexon wind forecast as it looked that morning, plus how far off that same forecast has been. Data only, never advice. Live at https://wind-day-ahead.vercel.app.

## Commands

- `make install`: `uv sync --frozen` (api) + `npm ci` (web).
- `make dev`: `docker compose --profile dev up`. Web at http://localhost:5173, API docs at http://localhost:8000/api/docs.
- Without Docker: `cd apps/api && uv sync && uv run fastapi dev`, and `cd apps/web && npm ci && npm run dev`.
- `make check`: ruff, ruff format, pyright, pytest (including one **live Elexon** test, so it needs the internet), a check that the generated TS types match the API, oxlint, tsc, vitest, vite build. A stage is done only when this passes. Offline: `cd apps/api && uv run pytest -m "not live"`.
- `make smoke`: builds and starts the production images (`docker compose --profile prod`, web on http://localhost:8080), runs the Playwright smoke test (`apps/web/e2e/`, live Elexon data), then tears down.
- `make smoke-url SMOKE_URL=https://…`: the same smoke test against any deployment. For a protected Vercel preview, run it from the repo root through `npx vercel@65.2.0 env run -- make smoke-url SMOKE_URL=https://…`, which injects the short-lived `VERCEL_OIDC_TOKEN`; Playwright sends it as `x-vercel-trusted-oidc-idp-token`. For API checks on a preview, use `npx vercel@65.2.0 curl <url>`.
- `make api-types`: regenerate `apps/web/src/api/` from the API's OpenAPI schema. Run it after changing any response model.
- `cd apps/api && uv run python -m wind.cli 2026-01-15 09:30`: the engine's full answer as JSON (live Elexon).
- Release (manual): `npx vercel@65.2.0 deploy` (preview), check it, then `npx vercel@65.2.0 deploy --prod`, then `make smoke-url SMOKE_URL=https://wind-day-ahead.vercel.app`.

## Architecture

- **`apps/api`:** FastAPI on Python 3.14, managed by uv (`uv.lock`).
  - `main.py` holds `app = create_app()`. The entrypoint is declared in `pyproject.toml` under `[tool.fastapi]`.
  - Every route lives under `/api`, including `/api/openapi.json` and `/api/docs`, because Vercel forwards `/api/*` with the prefix intact.
  - `wind/` is the domain package. Its one front door is `decision.build_decision(today, slot, source, settings) -> DecisionView`, and callers never see what's behind it:
    - `source.py`: the `Source` protocol (`forecasts(publish_from, publish_to)`, `actuals(settlement_from, settlement_to)`).
    - `elexon.py`: `ElexonSource`, the real Source over the BMRS Insights API. Every failure (network, timeout, non-2xx, bad shape, non-WIND rows) raises `ElexonError`.
    - `barrier.py`: `behind_barrier(source, as_of)` is a bouncer that wraps any Source and refuses rows published after as-of. `build_decision` wraps its source with it as the first step, so unfiltered rows never enter the engine.
    - `track_record.py`: `TrackRecord` pairs every visible past half-hour with its product forecast (held flat over the hour).
      - `.last(days)` returns a `Window`: scored half-hours, unscored count, and days before the sim start. The "last N days" rule lives only here.
      - `.whole_days(n)` returns the last *n* complete local days before today. A day counts only if every half-hour was scored (48, or 46/50 on clock-change days); others are skipped and counted.
    - `scoring.py`: pure formulas (MAE, RMSE, bias, linear percentile, direction agreement).
    - `decision.py`: one `_Spread` (P10/P90 of some misses) with `.apply(value) -> (low, high, clipped)` serves both the hourly band and the whole-day range. The 0-MWh hold lives only there.
    - `models.py`: input rows (dataclasses) and the `DecisionView` output (pydantic; it *is* the API schema).
    - `settings.py`: every operational value, overridable via `WIND_*` env vars. `lookback_days` is how far back to fetch, so it covers every window (scoring, band, whole days).
    - `cli.py`: prints `DecisionView` JSON for a day and slot.
    - `api.py`: `create_app(settings, source, clock)`; tests inject fakes for the last two.
      - `GET /api/decision?today=YYYY-MM-DD&slot=HH:MM` returns `DecisionView` plus `fetched_at`. Success is `Cache-Control: public, max-age=300, s-maxage=31536000`.
      - Errors are always `{"detail": "<sentence>"}` with `no-store`: 422 bad input, 404 missing publish, 502 Elexon failed (the reason is logged).
      - `GET /api/health` probes one known publish and returns 200 `ok` or 503 `degraded`, plus the instance's Elexon failure counter.
      - An httpx client is opened per request, because serverless runtimes don't reliably run startup hooks.
  - Tests are in `tests/`. The agreed seams are:
    - `build_decision`, with `FakeSource`;
    - `ElexonSource`, with httpx `MockTransport`;
    - `scoring` (pure);
    - the HTTP API, via `create_app`;
    - a golden test running recorded real Elexon data (`tests/fixtures/`) against an independent answer key;
    - one live Elexon test.
- **`apps/web`:** Vite + React 19 + TypeScript.
  - One screen (`App.tsx`):
    - **Header:** wordmark and the 09:50 gate.
    - **Hero sentence with the two `<select>`s** (`Controls`). The choice lives in the URL (`?today=&slot=`), so links can be shared and Back works.
    - **`Tomorrow`:** summary sentence, then the **day range** sentence (`DayRange`), the **hourly miss** sentence (`HourlyMiss`, from the shortest scoring window), a Chart ⇄ Table switch (`ForecastChart`, hourly steps plus the band), and the band caption.
    - **`Accuracy`:** a 7d | 14d scorecard with each metric's meaning, plus notes on skipped half-hours and December days.
    - **`WholeDaysTable`:** the 14 whole days behind the day range, newest first. Actual and miss MWh are shown to one decimal place so each row adds up exactly.
    - **`History`:** a length switch built from the API's windows, then Chart ⇄ Table (`HistoryChart`, two pens), newest first.
    - **Footer:** sources and fetch time.
  - `useDecision` fetches via `api.ts`. Loading is derived, never stored. Errors show the API's sentence plus *Try again*.
  - `format.ts` is the only place numbers, signs and UK times are formatted (Intl, `Europe/London`, non-breaking spaces, real minus sign).
    - `lean(value, decimals)` is the one sign rule: round the size, keep the sign, so −0.5 and +0.5 lean alike. Every signed number and every "higher/lower/above/below" word uses it.
    - `inTen(lower, upper)` turns percentiles into "8 in 10".
  - **Shared pieces:**
    - `components/chartStyle.ts`: axes, grid, cursor, the two pens, step lines, and the Chart/Table switch options. The history legend draws from the same pens.
    - `components/Shared.module.css`: section spacing, subheads, head rows, notes and `.visuallyHidden`. The scorecard is the base `Table.module.css` table plus `table.scorecard` overrides (no sticky header).
  - **Charts are lazy-loaded** (`React.lazy`), so Recharts downloads alongside the data instead of in front of it, with fixed-height placeholders.
  - `simulation.ts` holds the offered days (`SIM_DAYS`), slots, gate time, `DAY_MS`, and `toQuery()`, the one `?today=&slot=` builder used by both the address bar and the API call. The API stays the authority.
  - **Styling:** CSS Modules plus `tokens.css` (chart-recorder palette, light and dark via `prefers-color-scheme`, validated for colour-blind separation and AA contrast). Font: self-hosted Atkinson Hyperlegible Next, with `tabular-nums` everywhere.
  - **Tests:**
    - Vitest + Testing Library on two seams: the whole page with only the network faked (`src/test/fake-api.ts`, serving a real recorded Jan 15 response), and `format.ts`. Chart pixels aren't unit-tested.
    - Playwright (`e2e/smoke.spec.ts`) runs a real browser against a running deployment.
  - `src/api/` is **generated** (`@hey-api/openapi-ts`, types only). Never edit it by hand. `package.json` overrides `js-yaml` to 4.3.2 to patch an advisory in the generator's dependency.
  - **Dev server:** binds `0.0.0.0:5173` via the `--host` flag in `npm run dev`, not via config, because Vite drops a config-file host when it restarts after a config change. It proxies `/api` to `API_PROXY_TARGET` (default `http://localhost:8000`; in compose, `http://api-dev:8000`).
- **`compose.yaml`** has two profiles:
  - **`dev`:** `api-dev` (uv image, `fastapi dev`) and `web-dev` (node image, `vite`). Source is bind-mounted; deps live in named volumes.
  - **`prod`:** the production images. The API healthcheck is liveness via `/api/openapi.json`, deliberately *not* `/api/health`, which calls Elexon.
- **Production images** (pinned, non-root):
  - `apps/api/Dockerfile`: uv build stage, then the locked venv on `python:3.14.9-slim-trixie` with uvicorn, uid 10001.
  - `apps/web/Dockerfile`: node build, then `nginx-unprivileged:1.31.7-alpine3.24` (uid 101). The build stage copies only build inputs, and both Dockerfiles use BuildKit cache mounts for npm/uv downloads.
  - `apps/web/nginx.conf`: serves the SPA (deep links fall back to `index.html`, which is `no-cache`), proxies `/api/` to the api, and caches `/assets/` for a year.
- **`vercel.json`** uses Vercel Services: `web` (Vite, `npm ci`, SPA rewrite, `/assets/*` cached a year as immutable) and `api` (`entrypoint: main:app`). Top-level rewrites send `/api/(.*)` → api and everything else → web. `.vercelignore` keeps local envs and tests out of uploads.
- **Live:** https://wind-day-ahead.vercel.app (Vercel project `dizziedbliss/wind-day-ahead`, production).
  - Deploys are **manual only**: the GitHub repo is deliberately *disconnected*, so pushes and merges deploy nothing.
  - `.vercel/` and `.env.local` (Vercel OIDC token) are local and gitignored.

## Conventions

- Tests come first for any logic (red-green). Every piece of code gets tests.
- Dependencies are pinned. Python: `uv.lock` with `--frozen`. JS: exact versions (`.npmrc` `save-exact`) and `npm ci`. Docker images are pinned to exact tags.
- Python: ruff (lint + format) and pyright strict. TypeScript: `strict`, `noUncheckedIndexedAccess`, oxlint with `--deny-warnings`. No `any`.
- Operational values (windows, percentiles, slots, URLs, timeouts, cache ages) are settings, never literals.
- Never swallow an error. Elexon failures surface as visible errors, never as empty or fake data.
- Numbers: error = forecast − actual, so positive means the forecast was too high. Signed numbers always carry words ("forecast higher").
- Times are shown in UK time (`Europe/London`, 24h).
- How-far-off numbers (day range, average miss, typical hourly miss and lean) are wrapped in `<mark>`.
  - The highlighter is the band's blue tint (`--highlight`, ink on it 11.3:1 light / 10.0:1 dark), so they read as one family with the shaded band.
  - Forecast numbers stay plain bold.
  - No underline (it reads as a link), and no red or green (it reads as good/bad, i.e. a nudge).
- UI copy is sentence case, with typographic apostrophes (ruff allows `’`), and `…` for in-progress states.
- **README rules:**
  - Never name the client or who it was built for. Describe the use, not the user.
  - No product-name title.
  - Keep the Credits line crediting Claude.

## Glossary

- **Today / decision day (D):** the simulated day of the decision, Jan 1–31 2026.
- **Tomorrow / delivery day (D+1):** the day the power is being bought for.
- **Slot:** a WINDFOR publish time to view as of: 02:30, 04:30, 07:30 or 09:30. The GB day-ahead gate (N2EX) closes at 09:50.
- **As-of:** D at the chosen slot. Nothing published after it is visible or used.
- **Product:** the forecast from the same slot on the day before a given half-hour. It's what gets scored.
- **Half-hour:** one FUELHH settlement period (average MW). The hourly forecast is held flat across both half-hours of its hour.
- **Miss:** forecast − actual for one half-hour.
- **Track record:** every visible past half-hour with its actual and its product forecast (or none, if that publish is missing). Windows are slices of it.
- **Window:** the rolling 7 or 14 days of half-hours ending at as-of: `track_record.last(7)`.
- **Band:** tomorrow's forecast minus the P90/P10 of the last 14 days' misses, i.e. "8 in 10 past half-hours landed in this range".
- **Whole day:** a complete past local day where every half-hour was scored. Its miss is forecast MWh − actual MWh, *signed* (at day level, highs and lows really do cancel).
- **Day range:** tomorrow's total minus the P90/P10 of the last 14 whole days' misses (the same 8 in 10 as the band), plus the average whole-day miss in MWh and %. It's worded as history, never a promise.

## Not built (deliberately)

- Showing tomorrow's actuals, or any back-test view (they don't exist at decision time).
- Buy/sell suggestions or any nudging copy.
- Dates outside January 2026.
- A database: the data is public, immutable Elexon history.
- Auto-deploy from GitHub.
- CSV export, a theme toggle, a 30-day window.
