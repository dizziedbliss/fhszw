from wind.api import create_app

# Vercel and `fastapi dev` both load this module-level app (see [tool.fastapi] entrypoint).
app = create_app()
