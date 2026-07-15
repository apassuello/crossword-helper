"""Unit tests for backend/api/grid_routes.py — POST /api/grid/validate."""

import pytest

from backend.app import create_app


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
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is False and any("isolated" in w.lower() for w in data["warnings"])

    def test_validate_clean_grid_unaffected(self, client):
        grid = [["." for _ in range(11)] for _ in range(11)]
        resp = client.post("/api/grid/validate", json={"grid": grid, "grid_size": 11})
        assert resp.status_code == 200 and resp.get_json()["valid"] is True
