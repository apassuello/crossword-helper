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

        with patch(
            "backend.api.constraint_routes.resolve_wordlist_paths_strict",
            return_value=([], ["nonexistent_xyzzy"]),
        ):
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


class TestConstraintsGridFormats:
    """Regression tests: /api/constraints must accept frontend dict cells
    and never leak subprocess command lines in error responses."""

    def _dict_grid(self, size=5):
        return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]

    def test_accepts_frontend_dict_cells(self, client):
        """Dict-format cells ({letter, isBlack}) used to 500; they must be
        normalized to CLI strings before reaching the adapter."""
        with patch("backend.api.constraint_routes.CLIAdapter") as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_constraints.return_value = {"constraints": {}, "summary": {}}
            mock_cls.return_value = mock_adapter

            grid = self._dict_grid()
            grid[0][0] = {"letter": "C", "isBlack": False}
            grid[0][1] = {"letter": "", "isBlack": True}

            response = client.post(
                "/api/constraints",
                json={"grid": grid, "wordlists": ["comprehensive"]},
            )

            assert response.status_code == 200
            sent_grid = mock_adapter.analyze_constraints.call_args[0][0]["grid"]
            assert sent_grid[0][0] == "C"
            assert sent_grid[0][1] == "#"
            assert sent_grid[0][2] == "."

    def test_malformed_grid_returns_400(self, client):
        """Malformed cells are a client error, not a 500."""
        response = client.post(
            "/api/constraints",
            json={"grid": [[12345]], "wordlists": ["comprehensive"]},
        )
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_cli_failure_does_not_leak_command_line(self, client):
        """CLI errors must not expose the subprocess command or paths."""
        import subprocess as sp

        with patch("backend.api.constraint_routes.CLIAdapter") as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_constraints.side_effect = sp.CalledProcessError(
                1, ["/home/user/crossword-helper/cli/crossword", "analyze", "/tmp/tmpXYZ.json"]
            )
            mock_cls.return_value = mock_adapter

            response = client.post(
                "/api/constraints",
                json={
                    "grid": [["." for _ in range(5)] for _ in range(5)],
                    "wordlists": ["comprehensive"],
                },
            )

            assert response.status_code == 500
            error_text = response.get_data(as_text=True)
            assert "crossword" not in error_text
            assert "/tmp/" not in error_text
            assert "/home/" not in error_text

    def test_timeout_returns_504(self, client):
        import subprocess as sp

        with patch("backend.api.constraint_routes.CLIAdapter") as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_constraints.side_effect = sp.TimeoutExpired(cmd="x", timeout=30)
            mock_cls.return_value = mock_adapter

            response = client.post(
                "/api/constraints",
                json={
                    "grid": [["." for _ in range(5)] for _ in range(5)],
                    "wordlists": ["comprehensive"],
                },
            )

            assert response.status_code == 504
