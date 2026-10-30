from fastapi.testclient import TestClient

from lost_crypto.core.config import Settings
from lost_crypto.main import create_app


def _client() -> TestClient:
    # Port 1 is closed, so the database is unreachable: readiness must report 503.
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://x:x@127.0.0.1:1/x",
    )
    return TestClient(create_app(settings))


def test_liveness_does_not_need_database() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_unavailable_without_database() -> None:
    with _client() as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
