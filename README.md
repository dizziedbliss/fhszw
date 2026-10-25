# Wind day-ahead

**Live: https://wind-day-ahead.vercel.app**

Tomorrow's GB wind forecast as it looked at 09:30, and how accurate that same forecast has been, for a supplier deciding what to buy before the 09:50 day-ahead gate. It simulates January 2026 using Elexon BMRS data (WINDFOR forecasts, FUELHH actuals).

## Run it

```sh
make dev      # docker compose: web on :5173, API on :8000
make check    # lint, types, tests, build
make smoke    # production images + a real browser test on :8080
```

See `CLAUDE.md` for architecture and conventions.
