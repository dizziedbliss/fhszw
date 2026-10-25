.PHONY: install check api-check web-check dev

install:
	cd apps/api && uv sync --frozen
	cd apps/web && npm ci

# A stage is done only when this passes.
check: api-check web-check

api-check:
	cd apps/api && uv run --frozen ruff check .
	cd apps/api && uv run --frozen ruff format --check .
	cd apps/api && uv run --frozen pyright
	cd apps/api && uv run --frozen pytest

web-check:
	cd apps/web && npm run lint
	cd apps/web && npm run typecheck
	cd apps/web && npm test
	cd apps/web && npm run build

dev:
	docker compose --profile dev up
