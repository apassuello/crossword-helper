"""
Integration tests for constraint analysis endpoints.

Tests call the REAL CLI via subprocess (no mocks) to verify the full stack:
    Flask route → CLIAdapter → CLI subprocess → constraint_analyzer → response
"""

import pytest

from backend.app import create_app

SMALL_WORDLIST = "core/crosswordese"

# 5x5 all-white grid (CLI format: "." = empty, "#" = black)
GRID_5X5 = [["." for _ in range(5)] for _ in range(5)]

# 5x5 grid with one black square in the centre
GRID_5X5_WITH_BLACK = [row[:] for row in GRID_5X5]
GRID_5X5_WITH_BLACK[2][2] = "#"


@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as c:
        yield c


class TestConstraintsEndpointIntegration:
    """POST /api/constraints — real CLI execution."""

    @pytest.mark.slow
    def test_constraints_returns_one_cell_per_white_square(self, client):
        """25-cell all-white grid → 25 cells in the constraints dict."""
        response = client.post(
            "/api/constraints",
            json={"grid": GRID_5X5, "wordlists": [SMALL_WORDLIST]},
        )
        assert response.status_code == 200, response.data
        data = response.get_json()
        assert data["summary"]["total_cells"] == 25

    @pytest.mark.slow
    def test_constraints_black_squares_excluded(self, client):
        """5x5 grid with one black square → 24 cells, not 25."""
        response = client.post(
            "/api/constraints",
            json={"grid": GRID_5X5_WITH_BLACK, "wordlists": [SMALL_WORDLIST]},
        )
        assert response.status_code == 200, response.data
        data = response.get_json()
        assert data["summary"]["total_cells"] == 24

    @pytest.mark.slow
    def test_constraints_cell_keys_are_row_col_strings(self, client):
        """Constraint keys are 'row,col' strings for every white cell."""
        response = client.post(
            "/api/constraints",
            json={"grid": GRID_5X5, "wordlists": [SMALL_WORDLIST]},
        )
        assert response.status_code == 200, response.data
        constraints = response.get_json()["constraints"]
        # Spot-check top-left and bottom-right corners
        assert "0,0" in constraints
        assert "4,4" in constraints

    @pytest.mark.slow
    def test_constraints_each_cell_has_required_fields(self, client):
        """Every cell entry has across_options, down_options, min_options."""
        response = client.post(
            "/api/constraints",
            json={"grid": GRID_5X5, "wordlists": [SMALL_WORDLIST]},
        )
        assert response.status_code == 200, response.data
        constraints = response.get_json()["constraints"]
        for key, cell in constraints.items():
            assert "across_options" in cell, f"Missing across_options for {key}"
            assert "down_options" in cell, f"Missing down_options for {key}"
            assert "min_options" in cell, f"Missing min_options for {key}"

    @pytest.mark.slow
    def test_constraints_min_options_is_min_of_across_and_down(self, client):
        """min_options equals min(across_options, down_options) for crossing cells."""
        response = client.post(
            "/api/constraints",
            json={"grid": GRID_5X5, "wordlists": [SMALL_WORDLIST]},
        )
        assert response.status_code == 200, response.data
        constraints = response.get_json()["constraints"]
        for key, cell in constraints.items():
            a, d = cell["across_options"], cell["down_options"]
            if a > 0 and d > 0:  # cell participates in both directions
                assert cell["min_options"] == min(
                    a, d
                ), f"Cell {key}: expected min_options={min(a, d)}, got {cell['min_options']}"


class TestImpactEndpointIntegration:
    """POST /api/constraints/impact — real CLI execution."""

    @pytest.mark.slow
    def test_impact_reports_nonzero_crossings_for_crossing_word(self, client):
        """Placing EARTH across row 0 in a 5x5 grid touches the 5 down slots."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": GRID_5X5,
                "word": "EARTH",
                "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
                "wordlists": [SMALL_WORDLIST],
            },
        )
        assert response.status_code == 200, response.data
        data = response.get_json()
        assert data["summary"]["total_crossings"] > 0

    @pytest.mark.slow
    def test_impact_deltas_are_non_positive(self, client):
        """Placing a word can only reduce or preserve options in crossing slots."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": GRID_5X5,
                "word": "EARTH",
                "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
                "wordlists": [SMALL_WORDLIST],
            },
        )
        assert response.status_code == 200, response.data
        impacts = response.get_json()["impacts"]
        for slot_key, impact in impacts.items():
            assert impact["delta"] <= 0, (
                f"Slot {slot_key}: placing a word should not increase options, " f"got delta={impact['delta']}"
            )

    @pytest.mark.slow
    def test_impact_crossing_count_matches_word_length_in_open_grid(self, client):
        """EARTH (5 letters) across row 0 crosses exactly 5 down slots."""
        response = client.post(
            "/api/constraints/impact",
            json={
                "grid": GRID_5X5,
                "word": "EARTH",
                "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
                "wordlists": [SMALL_WORDLIST],
            },
        )
        assert response.status_code == 200, response.data
        data = response.get_json()
        assert data["summary"]["total_crossings"] == 5
