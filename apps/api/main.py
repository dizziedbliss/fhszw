from fastapi import FastAPI

# Every route lives under /api: Vercel forwards /api/* here with the prefix intact.
app = FastAPI(
    title="Wind day-ahead API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)
