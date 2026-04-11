"""Unit tests for BlackSquareSuggester and validate_grid_for_black_squares."""

from typing import Optional

from backend.core.black_square_suggester import (
    BlackSquareSuggester,
    BlackSquareSuggestion,
    validate_grid_for_black_squares,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_cell():
    return {"letter": "", "isBlack": False}


def _black_cell():
    return {"letter": "", "isBlack": True}


def _letter_cell(ch: str):
    return {"letter": ch, "isBlack": False}


def _empty_grid(size: int):
    """Return a size x size grid of empty dict cells."""
    return [[_empty_cell() for _ in range(size)] for _ in range(size)]


def _slot(row: int, col: int, direction: str, length: int, pattern: Optional[str] = None):
    if pattern is None:
        pattern = "?" * length
    return {
        "row": row,
        "col": col,
        "direction": direction,
        "length": length,
        "pattern": pattern,
    }


# ---------------------------------------------------------------------------
# BlackSquareSuggestion.to_dict
# ---------------------------------------------------------------------------


class TestBlackSquareSuggestionToDict:
    def test_to_dict_keys(self):
        s = BlackSquareSuggestion(
            position=2,
            row=0,
            col=2,
            score=350,
            reasoning="test",
            left_length=2,
            right_length=4,
            symmetric_position={"row": 14, "col": 12},
            new_word_count=74,
            constraint_reduction=3,
        )
        d = s.to_dict()
        assert set(d.keys()) == {
            "position",
            "row",
            "col",
            "score",
            "reasoning",
            "left_length",
            "right_length",
            "symmetric_position",
            "new_word_count",
            "constraint_reduction",
        }
        assert d["score"] == 350
        assert d["row"] == 0


# ---------------------------------------------------------------------------
# suggest_placements
# ---------------------------------------------------------------------------


class TestSuggestPlacements:
    def test_across_slot_returns_suggestions(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 15)
        results = suggester.suggest_placements(grid, slot)
        assert len(results) > 0
        for r in results:
            assert r["score"] > 0

    def test_down_slot_returns_suggestions(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "down", 15)
        results = suggester.suggest_placements(grid, slot)
        assert len(results) > 0

    def test_max_suggestions_limits_output(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 15)
        results = suggester.suggest_placements(grid, slot, max_suggestions=2)
        assert len(results) <= 2

    def test_short_slot_returns_empty(self):
        """Slots shorter than 6 should produce no suggestions."""
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 5)
        assert suggester.suggest_placements(grid, slot) == []

    def test_length_exactly_6_returns_suggestions(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 6)
        results = suggester.suggest_placements(grid, slot)
        # Position 1..4 tried; at least one should score > 0
        assert len(results) > 0

    def test_results_sorted_by_score_descending(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 15)
        results = suggester.suggest_placements(grid, slot, max_suggestions=10)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_slot_at_grid_edge(self):
        """Slot starting at the right edge going down."""
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 14, "down", 15)
        results = suggester.suggest_placements(grid, slot)
        assert isinstance(results, list)

    def test_single_cell_slot_returns_empty(self):
        grid = _empty_grid(15)
        suggester = BlackSquareSuggester(grid_size=15)
        slot = _slot(0, 0, "across", 1)
        assert suggester.suggest_placements(grid, slot) == []


# ---------------------------------------------------------------------------
# Symmetric position calculation
# ---------------------------------------------------------------------------


class TestSymmetricPosition:
    def test_across_center(self):
        """Center of 15x15: (7, 7) should map to itself."""
        suggester = BlackSquareSuggester(grid_size=15)
        grid = _empty_grid(15)
        slot = _slot(7, 0, "across", 15)
        sym = suggester._get_symmetric_position(grid, slot, 7)
        assert sym == {"row": 7, "col": 7}

    def test_across_top_left_corner(self):
        """Position (0,0) across pos 0 -> symmetric at (14,14)."""
        suggester = BlackSquareSuggester(grid_size=15)
        grid = _empty_grid(15)
        slot = _slot(0, 0, "across", 15)
        sym = suggester._get_symmetric_position(grid, slot, 0)
        assert sym == {"row": 14, "col": 14}

    def test_down_bottom_right_corner(self):
        """Down slot at col 14, position at last row -> symmetric at (0, 0)."""
        suggester = BlackSquareSuggester(grid_size=15)
        grid = _empty_grid(15)
        slot = _slot(0, 14, "down", 15)
        sym = suggester._get_symmetric_position(grid, slot, 14)
        assert sym == {"row": 0, "col": 0}

    def test_across_edge(self):
        """Position at end of row 0."""
        suggester = BlackSquareSuggester(grid_size=15)
        grid = _empty_grid(15)
        slot = _slot(0, 0, "across", 15)
        sym = suggester._get_symmetric_position(grid, slot, 14)
        assert sym == {"row": 14, "col": 0}

    def test_various_grid_size_11(self):
        suggester = BlackSquareSuggester(grid_size=11)
        grid = _empty_grid(11)
        slot = _slot(0, 0, "across", 11)
        sym = suggester._get_symmetric_position(grid, slot, 0)
        assert sym == {"row": 10, "col": 10}


# ---------------------------------------------------------------------------
# Cell type detection (_is_black / _is_black_cell)
# ---------------------------------------------------------------------------


class TestCellTypeDetection:
    def setup_method(self):
        self.suggester = BlackSquareSuggester(grid_size=5)

    def test_dict_black_cell(self):
        assert self.suggester._is_black_cell({"isBlack": True}) is True

    def test_dict_empty_cell(self):
        assert self.suggester._is_black_cell({"isBlack": False}) is False

    def test_dict_letter_cell(self):
        assert self.suggester._is_black_cell({"letter": "A"}) is False

    def test_string_hash_is_black(self):
        assert self.suggester._is_black_cell("#") is True

    def test_string_dot_is_not_black(self):
        assert self.suggester._is_black_cell(".") is False

    def test_string_letter_is_not_black(self):
        assert self.suggester._is_black_cell("A") is False

    def test_is_black_grid_lookup_dict(self):
        grid = [[_black_cell()]]
        assert self.suggester._is_black(grid, 0, 0) is True

    def test_is_black_grid_lookup_string(self):
        grid = [["#"]]
        assert self.suggester._is_black(grid, 0, 0) is True


# ---------------------------------------------------------------------------
# Word counting
# ---------------------------------------------------------------------------


class TestWordCounting:
    def test_empty_grid_full_rows_and_cols(self):
        """5x5 empty grid: 5 across words + 5 down words = 10."""
        grid = _empty_grid(5)
        suggester = BlackSquareSuggester(grid_size=5)
        assert suggester._count_words(grid) == 10

    def test_grid_with_black_splitting_row(self):
        """Black square in middle of row splits it; words < 3 not counted."""
        grid = _empty_grid(5)
        grid[0][2] = _black_cell()
        suggester = BlackSquareSuggester(grid_size=5)
        count = suggester._count_words(grid)
        # Row 0 split into length 2 + length 2 (neither counted)
        # Other 4 rows still have length-5 across words = 4
        # Col 2 split into 0+4 for down; cols 0,1,3,4 still length 5 = 4 down
        # Total: 4 across + 4+1 down => depends on exact splits
        assert count > 0

    def test_grid_all_black(self):
        grid = [[_black_cell() for _ in range(5)] for _ in range(5)]
        suggester = BlackSquareSuggester(grid_size=5)
        assert suggester._count_words(grid) == 0

    def test_string_format_grid(self):
        """Word counting works with string-format cells too."""
        grid = [["." for _ in range(5)] for _ in range(5)]
        suggester = BlackSquareSuggester(grid_size=5)
        assert suggester._count_words(grid) == 10


# ---------------------------------------------------------------------------
# validate_grid_for_black_squares
# ---------------------------------------------------------------------------


class TestValidateGridForBlackSquares:
    def test_valid_grid(self):
        grid = _empty_grid(15)
        result = validate_grid_for_black_squares(grid, 15)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []

    def test_size_mismatch_error(self):
        grid = _empty_grid(10)
        result = validate_grid_for_black_squares(grid, 15)
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "mismatch" in result["errors"][0].lower()

    def test_too_many_black_squares_warning(self):
        grid = _empty_grid(15)
        # 16% of 225 = 36; place 40 black squares to trigger warning
        count = 0
        for r in range(15):
            for c in range(15):
                if count >= 40:
                    break
                grid[r][c] = _black_cell()
                count += 1
            if count >= 40:
                break
        result = validate_grid_for_black_squares(grid, 15)
        assert result["valid"] is True  # warning, not error
        assert len(result["warnings"]) == 1
        assert "black square count" in result["warnings"][0].lower()

    def test_acceptable_black_square_count_no_warning(self):
        grid = _empty_grid(15)
        # Place just a few black squares (well under 16%)
        grid[0][0] = _black_cell()
        grid[14][14] = _black_cell()
        result = validate_grid_for_black_squares(grid, 15)
        assert result["warnings"] == []
