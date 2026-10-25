from fastapi.testclient import TestClient

from main import app


def test_openapi_is_served_under_api_prefix() -> None:
    # Vercel forwards /api/* to this service with the prefix intact,
    # so the docs must live under /api too.
    response = TestClient(app).get("/api/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Wind day-ahead API"


def test_the_schema_documents_every_error_as_one_plain_detail_sentence() -> None:
    schema = TestClient(app).get("/api/openapi.json").json()
    responses = schema["paths"]["/api/decision"]["get"]["responses"]

    for status in ("404", "422", "502"):
        body = responses[status]["content"]["application/json"]["schema"]
        assert body == {"$ref": "#/components/schemas/ErrorBody"}, status
    assert schema["components"]["schemas"]["ErrorBody"]["properties"]["detail"]["type"] == "string"
