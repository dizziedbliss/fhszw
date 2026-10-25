.PHONY: install check api-check web-check api-types api-types-check dev smoke smoke-url

install:
	cd apps/api && uv sync --frozen
	cd apps/web && npm ci

# A stage is done only when this passes.
check: api-check api-types-check web-check

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

# Frontend types come from the API's own OpenAPI schema, never written by hand.
OPENAPI_DUMP = cd apps/api && uv run --frozen python -c "import json, main; print(json.dumps(main.app.openapi(), indent=2))"
GEN_CACHE = apps/web/node_modules/.cache/api-types

api-types:
	mkdir -p $(GEN_CACHE)
	$(OPENAPI_DUMP) > ../../$(GEN_CACHE)/openapi.json
	cd apps/web && npx --no-install openapi-ts -i node_modules/.cache/api-types/openapi.json -o src/api -p @hey-api/typescript

# Fails when the committed types no longer match the API: run `make api-types`.
api-types-check:
	mkdir -p $(GEN_CACHE)
	$(OPENAPI_DUMP) > ../../$(GEN_CACHE)/openapi.json
	cd apps/web && npx --no-install openapi-ts -i node_modules/.cache/api-types/openapi.json -o node_modules/.cache/api-types/out -p @hey-api/typescript > /dev/null
	diff -r apps/web/src/api $(GEN_CACHE)/out

dev:
	docker compose --profile dev up

# Real browser against the production images on http://localhost:8080 (live Elexon data).
smoke:
	docker compose --profile prod up -d --build --wait
	cd apps/web && npm run smoke; status=$$?; cd ../.. && docker compose --profile prod down; exit $$status

# Same test against any deployment: make smoke-url SMOKE_URL=https://...
smoke-url:
	@test -n "$(SMOKE_URL)" || (echo "set SMOKE_URL=https://..." && exit 1)
	cd apps/web && SMOKE_URL=$(SMOKE_URL) npm run smoke
