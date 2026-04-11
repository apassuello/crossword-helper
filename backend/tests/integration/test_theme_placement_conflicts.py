"""
Integration tests for theme word placement conflict detection.

This test suite ensures that theme word placements correctly detect and prevent
letter conflicts at intersections (gibberish bug fix).

Created: 2025-12-30
Purpose: Regression protection for intersection conflict detection
"""

import pytest


class TestThemePlacementConflictDetection:
    """Test conflict detection in theme word placement."""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client."""
        from backend.app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_apply_placement_detects_letter_conflicts(self, app_client):
        """
        Test that apply-placement endpoint detects letter conflicts at intersections.

        Scenario: Grid has "CAT" horizontally, trying to place "DOG" vertically
        where they intersect - should fail because 'A' != 'O'.
        """
        # Create grid with "CAT" across row 1
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "C", "isBlack": False},
                {"letter": "A", "isBlack": False},
                {"letter": "T", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Try to place "DOG" vertically at col 1 (would intersect 'A' with 'O')
        request_data = {
            "grid": grid,
            "placement": {"word": "DOG", "row": 0, "col": 1, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should return 400 error with conflict details
        assert response.status_code == 400, "Should reject placement with letter conflict"
        data = response.get_json()
        assert "conflicts" in data, "Response should include conflict details"
        assert len(data["conflicts"]) > 0, "Should report at least one conflict"
        assert (
            "O" in data["conflicts"][0] and "A" in data["conflicts"][0]
        ), "Conflict message should mention both conflicting letters"
        assert data["applied"] is False, "Should indicate placement was not applied"

    def test_apply_placement_allows_matching_intersections(self, app_client):
        """
        Test that apply-placement allows intersections when letters match.

        Scenario: Grid has "CAT" horizontally, placing "MAP" vertically where 'A' matches.
        """
        # Create grid with "CAT" across row 1
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "C", "isBlack": False},
                {"letter": "A", "isBlack": False},
                {"letter": "T", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Place "MAP" vertically at col 1 (second letter 'A' intersects with row 1's 'A')
        # Row 0 col 1: M
        # Row 1 col 1: A (matches existing 'A')
        # Row 2 col 1: P
        request_data = {
            "grid": grid,
            "placement": {"word": "MAP", "row": 0, "col": 1, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should succeed
        assert response.status_code == 200, "Should allow placement with matching intersection"
        data = response.get_json()
        assert data["applied"] is True, "Should indicate placement was applied"

        # Verify grid state
        result_grid = data["grid"]
        assert result_grid[0][1]["letter"] == "M", "Should place 'M' at row 0, col 1"
        assert result_grid[1][1]["letter"] == "A", "Should keep 'A' at row 1, col 1"
        assert result_grid[2][1]["letter"] == "P", "Should place 'P' at row 2, col 1"

        # All placed letters should be theme-locked
        assert result_grid[0][1]["isThemeLocked"] is True, "Placed letter should be theme-locked"
        assert result_grid[1][1]["isThemeLocked"] is True, "Intersection should be theme-locked"
        assert result_grid[2][1]["isThemeLocked"] is True, "Placed letter should be theme-locked"

    def test_apply_placement_prevents_overwriting_black_squares(self, app_client):
        """Test that placement cannot overwrite black squares."""
        # Create grid with black square at (1, 1)
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": True},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Try to place "CAT" across row 1 (would hit black square at col 1)
        request_data = {
            "grid": grid,
            "placement": {"word": "CAT", "row": 1, "col": 0, "direction": "across"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should return 400 error
        assert response.status_code == 400, "Should reject placement over black square"
        data = response.get_json()
        assert "conflicts" in data, "Response should include conflict details"
        assert "black" in data["conflicts"][0].lower(), "Conflict should mention black square"
        assert data["applied"] is False, "Should indicate placement was not applied"

    def test_apply_placement_handles_empty_cells(self, app_client):
        """Test that placement works on empty cells (normal case)."""
        # Create empty grid
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Place "CAT" across row 1
        request_data = {
            "grid": grid,
            "placement": {"word": "CAT", "row": 1, "col": 0, "direction": "across"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should succeed
        assert response.status_code == 200, "Should allow placement on empty cells"
        data = response.get_json()
        assert data["applied"] is True

        # Verify grid
        result_grid = data["grid"]
        assert result_grid[1][0]["letter"] == "C"
        assert result_grid[1][1]["letter"] == "A"
        assert result_grid[1][2]["letter"] == "T"

        # All should be theme-locked
        assert all(result_grid[1][i]["isThemeLocked"] for i in range(3))

    def test_apply_placement_with_multiple_conflicts(self, app_client):
        """Test that all conflicts are reported when there are multiple."""
        # Create grid with letters that will conflict
        grid = [
            [
                {"letter": "X", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "Y", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "Z", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Try to place "CAT" down at col 0 (all letters conflict)
        request_data = {
            "grid": grid,
            "placement": {"word": "CAT", "row": 0, "col": 0, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should return 400 with all conflicts listed
        assert response.status_code == 400
        data = response.get_json()
        assert len(data["conflicts"]) == 3, "Should report all 3 conflicts"
        assert data["applied"] is False

    def test_apply_placement_handles_string_grid_format(self, app_client):
        """Test that placement works with string grid format (backward compatibility)."""
        # Some grids might use string format instead of dict
        grid = [
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
        ]

        request_data = {
            "grid": grid,
            "placement": {"word": "CAT", "row": 1, "col": 0, "direction": "across"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should succeed and convert to dict format
        assert response.status_code == 200
        data = response.get_json()
        result_grid = data["grid"]

        # Should be converted to dict format with theme locking
        assert isinstance(result_grid[1][0], dict)
        assert result_grid[1][0]["letter"] == "C"
        assert result_grid[1][0]["isThemeLocked"] is True

    def test_apply_placement_case_insensitive_matching(self, app_client):
        """Test that letter matching is case-insensitive."""
        # Grid has lowercase letter
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "c", "isBlack": False},
                {"letter": "a", "isBlack": False},
                {"letter": "t", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Place uppercase "MAP" down (should match lowercase 'a')
        request_data = {
            "grid": grid,
            "placement": {"word": "MAP", "row": 0, "col": 1, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should succeed (case-insensitive match)
        assert response.status_code == 200, "Should allow case-insensitive intersection"
        data = response.get_json()
        assert data["applied"] is True

    def test_apply_all_placements_stops_on_conflict(self, app_client):
        """
        Test that Apply All button behavior correctly skips conflicting placements.

        Note: This tests the scenario where multiple theme words are applied
        sequentially and later words may conflict with earlier placements.
        """
        # Create empty grid
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Apply first word successfully
        request1 = {
            "grid": grid,
            "placement": {"word": "CAT", "row": 1, "col": 0, "direction": "across"},
        }
        response1 = app_client.post("/api/theme/apply-placement", json=request1)
        assert response1.status_code == 200
        updated_grid = response1.get_json()["grid"]

        # Try to apply second word that conflicts
        request2 = {
            "grid": updated_grid,
            "placement": {"word": "DOG", "row": 0, "col": 1, "direction": "down"},
        }
        response2 = app_client.post("/api/theme/apply-placement", json=request2)

        # Should fail with conflict
        assert response2.status_code == 400
        data = response2.get_json()
        assert data["applied"] is False
        assert len(data["conflicts"]) > 0


class TestThemePlacementEdgeCases:
    """Test edge cases in theme placement."""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client."""
        from backend.app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_apply_placement_out_of_bounds(self, app_client):
        """Test that placement detects out-of-bounds errors."""
        grid = [
            [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
            [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        ]

        # Try to place word that goes out of bounds
        request_data = {
            "grid": grid,
            "placement": {
                "word": "TOOLONG",  # 7 letters in 2x2 grid
                "row": 0,
                "col": 0,
                "direction": "across",
            },
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should return 400 with out-of-bounds conflicts
        assert response.status_code == 400
        data = response.get_json()
        assert "conflicts" in data
        assert any("out of bounds" in c.lower() for c in data["conflicts"])

    def test_apply_placement_preserves_existing_theme_lock(self, app_client):
        """Test that placing over already theme-locked cell preserves the lock."""
        # Grid with theme-locked 'A'
        grid = [
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "A", "isBlack": False, "isThemeLocked": True},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Place "MAP" down at col 1 (matches existing 'A' at row 1)
        request_data = {
            "grid": grid,
            "placement": {"word": "MAP", "row": 0, "col": 1, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        assert response.status_code == 200
        result_grid = response.get_json()["grid"]

        # Theme lock should be preserved
        assert result_grid[1][1]["isThemeLocked"] is True

    def test_apply_placement_with_whitespace_in_letters(self, app_client):
        """Test that whitespace in existing letters is handled correctly."""
        # Grid with whitespace around letters
        grid = [
            [
                {"letter": " ", "isBlack": False},
                {"letter": " A ", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
            [
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
                {"letter": "", "isBlack": False},
            ],
        ]

        # Place "APE" down at col 1 (should trim and match 'A')
        request_data = {
            "grid": grid,
            "placement": {"word": "APE", "row": 0, "col": 1, "direction": "down"},
        }

        response = app_client.post(
            "/api/theme/apply-placement",
            json=request_data,
            content_type="application/json",
        )

        # Should succeed (whitespace trimmed)
        assert response.status_code == 200, "Should allow case-insensitive intersection with whitespace trimmed"
        data = response.get_json()
        assert data["applied"] is True
