"""
Unit tests for backend error hygiene.

Covers:
- App-level 404/405 handlers return the same envelope shape handle_error uses
  ({"error": {"code", "message"}}), not a flat {"error": "string"}.
- TIMEOUT responses use HTTP 504 everywhere (not the 505/506/507 typos).

All CLI adapter calls are mocked -- no real subprocess invocations.
"""

import json
import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def client(mocker):
    """Create a Flask test client with the CLI adapter mocked out."""
    mock_adapter = MagicMock()
    mock_adapter.health_check.return_value = True
    mocker.patch("backend.api.routes.get_adapter", return_value=mock_adapter)
    mocker.patch("backend.api.routes.cli_adapter", mock_adapter)
    mocker.patch(
        "backend.api.routes.resolve_wordlist_paths",
        return_value=["/fake/wordlists/comprehensive.txt"],
    )

    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c, mock_adapter


class TestNotFoundEnvelope:
    def test_unknown_route_returns_envelope_404(self, client):
        c, _ = client
        resp = c.get("/api/nonexistent")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["message"]


class TestMethodNotAllowedEnvelope:
    def test_wrong_method_returns_envelope_405(self, client):
        c, _ = client
        # /api/pattern is POST-only
        resp = c.get("/api/pattern")
        assert resp.status_code == 405
        body = resp.get_json()
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["message"]


class TestTimeoutStatus:
    def test_pattern_timeout_is_504(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=30)
        resp = c.post(
            "/api/pattern",
            data=json.dumps({"pattern": "A?B"}),
            content_type="application/json",
        )
        assert resp.status_code == 504
        assert resp.get_json()["error"]["code"] == "TIMEOUT"
