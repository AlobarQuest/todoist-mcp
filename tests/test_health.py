"""Tests for health and readiness endpoints."""

from starlette.testclient import TestClient


def _get_app():
    """Get the Starlette ASGI app from FastMCP for testing.
    In mcp v1.26.0, use mcp.streamable_http_app() which returns a Starlette app."""
    from src.server import mcp
    return mcp.streamable_http_app()


class TestLiveness:
    def test_health_live_returns_ok(self):
        app = _get_app()
        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestReadiness:
    def test_ready_with_valid_token(self):
        app = _get_app()
        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_ready_without_token(self, monkeypatch):
        monkeypatch.delenv("TODOIST_API_TOKEN")
        app = _get_app()
        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert "TODOIST_API_TOKEN" in response.json().get("error", "")
