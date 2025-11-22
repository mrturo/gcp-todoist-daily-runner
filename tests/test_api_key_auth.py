"""
Tests for API key authentication functionality in src/main.py.
"""

from unittest import mock

from fastapi.testclient import TestClient

from src.main import app


def test_endpoint_without_api_key_when_not_configured(monkeypatch):
    """Test that endpoint works without API key when API_KEY is not configured."""
    # Ensure API_KEY is not set
    monkeypatch.delenv("API_KEY", raising=False)

    client = TestClient(app)

    # Mock the entire integration flow
    with mock.patch("src.main.get_todoist_token", return_value="fake-token"):
        with mock.patch("src.main.fetch_tasks", return_value=[]):
            response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_endpoint_with_valid_api_key(monkeypatch):
    """Test that endpoint works with valid API key when API_KEY is configured."""
    monkeypatch.setenv("API_KEY", "my-secret-key")

    client = TestClient(app)

    with mock.patch("src.main.get_todoist_token", return_value="fake-token"):
        with mock.patch("src.main.fetch_tasks", return_value=[]):
            response = client.get("/", headers={"X-API-Key": "my-secret-key"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_endpoint_without_api_key_header_when_required(monkeypatch):
    """Test that endpoint returns 401 when API key is required but not provided."""
    monkeypatch.setenv("API_KEY", "my-secret-key")

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key. Provide X-API-Key header."
    assert response.headers.get("WWW-Authenticate") == "ApiKey"


def test_endpoint_with_invalid_api_key(monkeypatch):
    """Test that endpoint returns 403 when API key is invalid."""
    monkeypatch.setenv("API_KEY", "correct-key")

    client = TestClient(app)
    response = client.get("/", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API key"
