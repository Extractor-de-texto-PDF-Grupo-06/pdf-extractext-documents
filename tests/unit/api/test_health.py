"""El health de documents dice si puede atender: responde según MongoDB."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200_when_mongodb_answers():
    with patch("app.main.ping_database", new=AsyncMock(return_value=True)):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_mongodb_does_not_answer():
    with patch("app.main.ping_database", new=AsyncMock(return_value=False)):
        response = client.get("/health")

    assert response.status_code == 503
    assert "detail" in response.json()
