"""Unit tests for constraint API routes."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


class TestConstraintsEndpoint:

    def test_post_constraints_returns_200(self, client):
        """POST /api/constraints with valid grid returns 200."""
        with patch("backend.api.constraint_routes.CLIAdapter") as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_constraints.return_value = {
                "constraints": {"0,0": {"across_options": 10, "down_options": 5, "min_options": 5}},
                "summary": {
                    "total_cells": 1,
                    "critical_cells": 0,
                    "average_min_options": 5.0,
                },
            }
            mock_cls.return_value = mock_adapter

            response = client.post(
                "/api/constraints",
                json={
                    "grid": [["." for _ in range(5)] for _ in range(5)],
                    "wordlists": ["comprehensive"],
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "constraints" in data
            assert "summary" in data

    def test_post_constraints_missing_grid_returns_400(self, client):
        """POST /api/constraints without grid returns 400."""
        response = client.post("/api/constraints", json={"wordlists": ["comprehensive"]})
        assert response.status_code == 400

    def test_post_constraints_empty_body_returns_400(self, client):
        """POST /api/constraints with empty body returns 400."""
        response = client.post("/api/constraints", data="", content_type="application/json")
        assert response.status_code == 400

    def test_post_constraints_unknown_wordlist_returns_400(self, client):
        """POST /api/constraints with unresolvable wordlist returns 400."""
        from unittest.mock import patch

        with patch("backend.api.constraint_routes.resolve_wordlist_paths", return_value=[]):
            response = client.post(
                "/api/constraints",
                json={
                    "grid": [["." for _ in range(5)] for _ in range(5)],
                    "wordlists": ["nonexistent_xyzzy"],
                },
            )
        assert response.status_code == 400


class TestImpactEndpoint:

    def test_post_impact_returns_200(self, client):
        """POST /api/constraints/impact with valid data returns 200."""
        with patch("backend.api.constraint_routes.CLIAdapter") as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_placement_impact.return_value = {
                "impacts": {"0,1,down": {"before": 100, "after": 10, "delta": -90, "length": 5}},
                "summary": {
                    "total_crossings": 1,
                    "worst_delta": -90,
                    "crossings_eliminated": 0,
                },
            }
            mock_cls.return_value = mock_adapter

            response = client.post(
                "/api/constraints/impact",
                json={
                    "grid": [["." for _ in range(5)] for _ in range(5)],
                    "word": "CATCH",
                    "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
                    "wordlists": ["comprehensive"],
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "impacts" in data

    def test_post_impact_missing_word_returns_400(self, client):
        """POST /api/constraints/impact without word returns 400."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": [["." for _ in range(5)] for _ in range(5)],
                "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
            },
        )
        assert response.status_code == 400

    def test_post_impact_missing_slot_returns_400(self, client):
        """POST /api/constraints/impact without slot returns 400."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": [["." for _ in range(5)] for _ in range(5)],
                "word": "CATCH",
            },
        )
        assert response.status_code == 400

    def test_post_impact_missing_slot_key_returns_400(self, client):
        """POST /api/constraints/impact with incomplete slot returns 400."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": [["." for _ in range(5)] for _ in range(5)],
                "word": "CATCH",
                "slot": {"row": 0, "col": 0, "direction": "across"},  # missing length
            },
        )
        assert response.status_code == 400
