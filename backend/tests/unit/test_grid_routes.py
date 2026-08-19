"""Unit tests for backend/api/grid_routes.py — POST /api/grid/validate."""

import pytest

from backend.app import create_app
from backend.tests.response_diag import resp_diag


@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


class TestValidateGridStructuralChecks:
    """Structural checks (connectivity + short-word scan) merged into /api/grid/validate (D1:C)."""

    def test_validate_merges_structural_errors(self, client):
        grid = [["." for _ in range(11)] for _ in range(11)]
        for col in range(11):
            grid[5][col] = "#"
        resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
        assert resp.status_code == 200, resp_diag(resp)
        data = resp.get_json()
        assert data["valid"] is False and any("isolated" in w.lower() for w in data["warnings"])

    def test_validate_clean_grid_unaffected(self, client):
        grid = [["." for _ in range(11)] for _ in range(11)]
        resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
        assert resp.status_code == 200 and resp.get_json()["valid"] is True

    def test_validate_degrades_gracefully_on_non_cli_string_cells(self, client):
        """DD1 guard: dict-shaped cells (webapp format) throw AttributeError inside
        Grid.from_dict (cell.isalpha() has no meaning for a dict) — the local
        try/except Exception around the structural block must catch this and
        degrade to an empty structural result, never reaching the (broken)
        handle_error(...default_status=) fallback, and always keep HTTP 200."""
        grid = [[{"isBlack": False, "letter": ""} for _ in range(11)] for _ in range(11)]
        resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
        assert resp.status_code == 200, resp_diag(resp)
        data = resp.get_json()
        assert data["valid"] is True
        assert data["warnings"] == []
