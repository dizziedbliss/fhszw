# Production image for the API. Build with uv, run the locked venv on plain slim Python.
FROM ghcr.io/astral-sh/uv:0.13.5-python3.14-trixie-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY main.py ./
COPY wind ./wind

# Same Python (3.14.9, /usr/local/bin/python) as the build stage, so the venv runs as-is.
FROM python:3.14.9-slim-trixie
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app /app
USER app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
