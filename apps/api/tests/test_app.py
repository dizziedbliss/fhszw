from fastapi.testclient import TestClient

from main import app


def test_openapi_is_served_under_api_prefix() -> None:
    # Vercel forwards /api/* to this service with the prefix intact,
    # so the docs must live under /api too.
    response = TestClient(app).get("/api/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Wind day-ahead API"
