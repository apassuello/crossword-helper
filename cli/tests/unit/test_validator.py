"""
Unit tests for GridValidator class.
"""

import pytest
from src.core.grid import Grid
from src.core.validator import GridValidator


class TestSymmetryValidation:
    """Test symmetry validation."""

    def test_symmetric_grid_passes(self):
        """Test that symmetric grid passes validation."""
        grid = Grid(11)
        grid.set_black_square(0, 0)  # Automatically sets (10, 10)
        grid.set_black_square(1, 5)  # Automatically sets (9, 5)

        is_valid, errors = GridValidator.validate_all(grid)

        # Should have no symmetry errors
        symmetry_errors = [e for e in errors if "symmetry" in e.lower()]
        assert len(symmetry_errors) == 0

    def test_asymmetric_grid_fails(self):
        """Test that asymmetric grid fails validation."""
        grid = Grid(11)
        grid.set_black_square(0, 0, enforce_symmetry=False)
        # (10, 10) is not black, breaking symmetry

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("symmetry" in e.lower() for e in errors)


class TestConnectivityValidation:
    """Test connectivity validation."""

    def test_empty_grid_is_connected(self):
        """Test that empty grid is connected."""
        grid = Grid(11)

        is_valid, errors = GridValidator.validate_all(grid)

        # Should have no connectivity errors
        connectivity_errors = [e for e in errors if "connected" in e.lower() or "isolated" in e.lower()]
        assert len(connectivity_errors) == 0

    def test_connected_grid_passes(self):
        """Test that connected grid passes validation."""
        grid = Grid(11)
        # Add black squares but keep grid connected
        grid.set_black_square(0, 5)
        grid.set_black_square(1, 5)
        grid.set_black_square(2, 5)

        is_valid, errors = GridValidator.validate_all(grid)

        # Should have no connectivity errors
        connectivity_errors = [e for e in errors if "connected" in e.lower() or "isolated" in e.lower()]
        assert len(connectivity_errors) == 0

    def test_disconnected_grid_fails(self):
        """Test that disconnected grid fails validation."""
        grid = Grid(11)
        # Create a wall of black squares that disconnects the grid
        for col in range(11):
            grid.set_black_square(5, col, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("connected" in e.lower() or "isolated" in e.lower() for e in errors)

    def test_isolated_corner_fails(self):
        """Test that grid with isolated corner fails validation."""
        grid = Grid(11)
        # Isolate top-left corner
        for row in range(11):
            grid.set_black_square(row, 1, enforce_symmetry=False)
        for col in range(11):
            grid.set_black_square(1, col, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("connected" in e.lower() or "isolated" in e.lower() for e in errors)


class TestMinimumWordLength:
    """Test minimum word length validation."""

    def test_grid_with_long_words_passes(self):
        """Test that grid with all words ≥3 letters passes."""
        grid = Grid(11)
        # Create pattern with 3+ letter words
        grid.set_black_square(0, 3)
        grid.set_black_square(0, 7)
        # This creates words of length 3 and 4

        is_valid, errors = GridValidator.validate_all(grid)

        # Should have no word length errors
        word_length_errors = [e for e in errors if "word" in e.lower() and ("short" in e.lower() or "letter" in e.lower())]
        assert len(word_length_errors) == 0

    def test_grid_with_short_across_word_fails(self):
        """Test that grid with 2-letter across word fails with a word-length error."""
        grid = Grid(11)
        # Create 2-letter word: row 0, columns 0-1
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_black_square(0, 3, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("Across word at (0, 0)" in e and "2 letters" in e for e in errors)

    def test_grid_with_short_down_word_fails(self):
        """Test that grid with 2-letter down word fails with a word-length error."""
        grid = Grid(11)
        # Create 2-letter word: column 0, rows 0-1
        grid.set_black_square(2, 0, enforce_symmetry=False)
        grid.set_black_square(3, 0, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("Down word at (0, 0)" in e and "2 letters" in e for e in errors)

    def test_single_letter_word_fails(self):
        """Test that grid with 1-letter word fails."""
        grid = Grid(11)
        # Create isolated cell surrounded by black squares
        grid.set_black_square(1, 0, enforce_symmetry=False)
        grid.set_black_square(0, 1, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        # This fails connectivity (isolated cell) AND minimum word length
        assert not is_valid
        assert any("1 letter" in e for e in errors)

    def test_symmetric_grid_with_short_word_fails(self):
        """Regression test: a symmetric, connected grid whose only flaw is a
        2-letter word must be INVALID (the short-word check used to be dead
        code because get_word_slots() filtered out slots shorter than 3)."""
        grid = Grid(11)
        # Black at (0, 2) with symmetry adds (10, 8): creates 2-letter across
        # words at (0,0)-(0,1) and (10,9)-(10,10). Grid stays connected.
        grid.set_black_square(0, 2)

        assert grid.check_symmetry()

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        short_word_errors = [e for e in errors if "only 2 letters" in e]
        assert len(short_word_errors) == 2
        assert any("Across word at (0, 0)" in e for e in short_word_errors)
        assert any("Across word at (10, 9)" in e for e in short_word_errors)


class TestBlackSquarePercentage:
    """Test black square percentage validation."""

    def test_low_black_square_percentage_passes(self):
        """Test that grid with <17% black squares passes."""
        grid = Grid(11)
        # 11×11 = 121 cells, 17% = ~20 cells
        # Add 10 black squares (with symmetry = 20 total) = 16.5%
        for i in range(10):
            grid.set_black_square(0, i)

        is_valid, errors = GridValidator.validate_all(grid)

        # Should have no black square percentage errors
        percentage_errors = [e for e in errors if "black square" in e.lower() and "%" in e]
        assert len(percentage_errors) == 0

    def test_high_black_square_percentage_fails(self):
        """Test that grid with >17% black squares fails."""
        grid = Grid(11)
        # 11×11 = 121 cells, 17% = ~20 cells
        # Add 30 black squares (with symmetry = 60 total) = 49.6%
        for i in range(30):
            row = i // 11
            col = i % 11
            if row < 11 and col < 11:
                grid.set_black_square(row, col)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        assert any("black square" in e.lower() and ("%" in e or "percentage" in e.lower()) for e in errors)


class TestValidateAll:
    """Test comprehensive validation."""

    def test_perfect_grid_passes(self):
        """Test that well-formed grid passes all validations."""
        grid = Grid(15)
        # Add some symmetric black squares in a good pattern
        grid.set_black_square(0, 3)
        grid.set_black_square(0, 11)
        grid.set_black_square(3, 0)
        grid.set_black_square(3, 7)

        is_valid, errors = GridValidator.validate_all(grid)

        assert is_valid
        assert len(errors) == 0

    def test_multiple_violations(self):
        """Test that grid with multiple violations reports all of them."""
        grid = Grid(11)
        # Violate symmetry
        grid.set_black_square(0, 0, enforce_symmetry=False)
        # Create short word
        grid.set_black_square(1, 2, enforce_symmetry=False)

        is_valid, errors = GridValidator.validate_all(grid)

        assert not is_valid
        # Should have at least 1 error (symmetry)
        assert len(errors) >= 1


class TestGridStats:
    """Test grid statistics."""

    def test_empty_grid_stats(self):
        """Test statistics for empty grid."""
        grid = Grid(11)
        stats = GridValidator.get_grid_stats(grid)

        assert stats["size"] == 11
        assert stats["total_squares"] == 121
        assert stats["black_squares"] == 0
        assert stats["white_squares"] == 121
        assert stats["black_square_percentage"] == 0.0
        assert stats["is_symmetric"] is True
        assert stats["is_connected"] is True

    def test_grid_with_content_stats(self):
        """Test statistics for grid with content."""
        grid = Grid(11)
        # Add 10 black squares (20 with symmetry)
        for i in range(10):
            grid.set_black_square(0, i)

        stats = GridValidator.get_grid_stats(grid)

        assert stats["size"] == 11
        assert stats["total_squares"] == 121
        assert stats["black_squares"] == 20
        assert stats["white_squares"] == 101
        assert 16.0 < stats["black_square_percentage"] < 17.0
        assert stats["is_symmetric"] is True
        assert stats["is_connected"] is True

    def test_word_count_estimate(self):
        """Test word count estimation."""
        grid = Grid(11)
        # Create simple grid with known word count
        # Grid with one horizontal divider creates roughly 22 words (11 across top + 11 across bottom)
        for col in range(11):
            grid.set_black_square(5, col, enforce_symmetry=False)

        stats = GridValidator.get_grid_stats(grid)

        # Should have some word count estimate
        assert "word_count" in stats
        assert stats["word_count"] > 0

    def test_meets_nyt_standards(self):
        """Test NYT standards flag."""
        grid = Grid(15)
        # Create a good grid
        grid.set_black_square(0, 3)
        grid.set_black_square(0, 11)

        stats = GridValidator.get_grid_stats(grid)

        # Should meet NYT standards (symmetric, connected, <17% black, no short words)
        assert "meets_nyt_standards" in stats
        assert stats["meets_nyt_standards"] is True

    def test_fails_nyt_standards(self):
        """Test NYT standards detection for bad grid."""
        grid = Grid(11)
        # Break symmetry
        grid.set_black_square(0, 0, enforce_symmetry=False)

        stats = GridValidator.get_grid_stats(grid)

        assert stats["meets_nyt_standards"] is False


class TestValidateStructural:
    """Test validate_structural: connectivity + short-word(<3) via _check_minimum_word_length
    (the single implementation of the min-word-length rule; see D1:C / #10)."""

    def test_isolated_region_reported(self):
        grid = Grid(11)
        for col in range(11):
            grid.set_black_square(5, col, enforce_symmetry=False)
        ok, errors = GridValidator.validate_structural(grid)
        assert ok is False and any("isolated" in e.lower() for e in errors)

    def test_clean_grid_passes(self):
        ok, errors = GridValidator.validate_structural(Grid(11))
        assert ok is True and errors == []

    def test_short_word_reported(self):  # loose match: satisfied by either message format
        grid = Grid(11)
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_black_square(0, 3, enforce_symmetry=False)  # 2-letter across run at (0,0)-(0,1)
        ok, errors = GridValidator.validate_structural(grid)
        assert ok is False and any("2" in e and "across" in e.lower() for e in errors)

    def test_short_word_uses_check_minimum_word_length_format(self):
        """validate_structural must route through _check_minimum_word_length, not a
        separate run-length walker — its error strings match that function's exact
        format ("Across word at (0, 0) is only 2 letters (minimum is 3)"), not the
        deleted _scan_short_words format ("2-letter across word at (0,0)")."""
        grid = Grid(11)
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_black_square(0, 3, enforce_symmetry=False)  # 2-letter across run at (0,0)-(0,1)
        ok, errors = GridValidator.validate_structural(grid)
        assert ok is False
        assert "Across word at (0, 0) is only 2 letters (minimum is 3)" in errors


class TestGetWordSlotsUnchangedByRunEnumeratorRefactor:
    """Regression: get_word_slots() must be byte-identical after being refactored to
    filter(length>=3) over the new shared Grid.enumerate_white_runs() (DD2)."""

    @staticmethod
    def _expected_slots(grid: Grid) -> list:
        """Pre-refactor algorithm, reimplemented verbatim as an oracle."""
        slots = []

        for row in range(grid.size):
            col = 0
            while col < grid.size:
                if not grid.is_black(row, col):
                    start_col = col
                    length = 0
                    pattern = []
                    while col < grid.size and not grid.is_black(row, col):
                        pattern.append(grid.get_cell(row, col))
                        length += 1
                        col += 1
                    if length >= 3:
                        slots.append(
                            {
                                "direction": "across",
                                "row": row,
                                "col": start_col,
                                "length": length,
                                "pattern": "".join(pattern),
                            }
                        )
                else:
                    col += 1

        for col in range(grid.size):
            row = 0
            while row < grid.size:
                if not grid.is_black(row, col):
                    start_row = row
                    length = 0
                    pattern = []
                    while row < grid.size and not grid.is_black(row, col):
                        pattern.append(grid.get_cell(row, col))
                        length += 1
                        row += 1
                    if length >= 3:
                        slots.append(
                            {
                                "direction": "down",
                                "row": start_row,
                                "col": col,
                                "length": length,
                                "pattern": "".join(pattern),
                            }
                        )
                else:
                    row += 1

        return slots

    def test_empty_grid(self):
        grid = Grid(11)
        assert grid.get_word_slots() == self._expected_slots(grid)

    def test_grid_with_black_squares(self):
        grid = Grid(15)
        grid.set_black_square(0, 3)
        grid.set_black_square(0, 11)
        grid.set_black_square(3, 0)
        grid.set_black_square(3, 7)
        assert grid.get_word_slots() == self._expected_slots(grid)

    def test_grid_with_short_and_isolated_runs(self):
        grid = Grid(11)
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_black_square(0, 3, enforce_symmetry=False)
        grid.set_black_square(1, 0, enforce_symmetry=False)
        grid.set_black_square(0, 1, enforce_symmetry=False)
        assert grid.get_word_slots() == self._expected_slots(grid)

    def test_disconnected_wall_grid(self):
        grid = Grid(11)
        for col in range(11):
            grid.set_black_square(5, col, enforce_symmetry=False)
        assert grid.get_word_slots() == self._expected_slots(grid)


def _all_black(size: int) -> Grid:
    """A grid with every cell black — zero white squares."""
    grid = Grid(size, validate_size=False)
    for row in range(size):
        for col in range(size):
            grid.set_black_square(row, col, enforce_symmetry=False)
    return grid


def _single_white_cell(size: int, row: int, col: int) -> Grid:
    """Every cell black except (row, col) — a length-1 run in both directions."""
    grid = Grid(size, validate_size=False)
    for r in range(size):
        for c in range(size):
            if (r, c) != (row, col):
                grid.set_black_square(r, c, enforce_symmetry=False)
    return grid


def _black_row(size: int, row: int) -> Grid:
    """An otherwise-empty grid with one full black row."""
    grid = Grid(size)
    for col in range(size):
        grid.set_black_square(row, col, enforce_symmetry=False)
    return grid


def _black_col(size: int, col: int) -> Grid:
    """An otherwise-empty grid with one full black column."""
    grid = Grid(size)
    for row in range(size):
        grid.set_black_square(row, col, enforce_symmetry=False)
    return grid


def _short_words_from_runs(grid: Grid) -> list:
    """Short (length 1-2) words as found by Grid.enumerate_white_runs() — the walker
    _scan_short_words used before its deletion."""
    return sorted(
        (direction, r, c, n) for (cells, n, direction) in grid.enumerate_white_runs() if 1 <= n <= 2 for (r, c) in [cells[0]]
    )


def _short_words_from_slots(grid: Grid) -> list:
    """Short (length 1-2) words as found by Grid.get_word_slots(min_length=1) — the
    walker _check_minimum_word_length uses (the surviving implementation)."""
    return sorted(
        (slot["direction"], slot["row"], slot["col"], slot["length"])
        for slot in grid.get_word_slots(min_length=1)
        if slot["length"] < 3
    )


class TestShortWordWalkerEquivalence:
    """Equivalence gate for #10: enumerate_white_runs() and get_word_slots(min_length=1)
    must identify the exact same set of short (<3 letter) words on every grid, including
    degenerate ones. This is what licenses deleting _scan_short_words in favour of routing
    validate_structural through _check_minimum_word_length alone — it stays in the suite
    permanently to catch any future divergence between the two call paths.

    Grids use validate_size=False for non-standard sizes, matching how grid_routes.py:231
    builds structural-check grids in production (Grid.from_dict(..., strict_size=False))."""

    @pytest.mark.parametrize(
        "grid",
        [
            pytest.param(_all_black(5), id="all_black"),
            pytest.param(_all_black(11), id="zero_white_squares_standard_size"),
            pytest.param(Grid(11), id="all_white"),
            pytest.param(_single_white_cell(5, 0, 0), id="single_cell_top_left_corner"),
            pytest.param(_single_white_cell(5, 0, 4), id="single_cell_top_right_corner"),
            pytest.param(_single_white_cell(5, 4, 0), id="single_cell_bottom_left_corner"),
            pytest.param(_single_white_cell(5, 4, 4), id="single_cell_bottom_right_corner"),
            pytest.param(_single_white_cell(5, 0, 2), id="single_cell_top_edge"),
            pytest.param(_single_white_cell(5, 4, 2), id="single_cell_bottom_edge"),
            pytest.param(_single_white_cell(5, 2, 0), id="single_cell_left_edge"),
            pytest.param(_single_white_cell(5, 2, 4), id="single_cell_right_edge"),
            pytest.param(_black_row(11, 0), id="full_black_row_top"),
            pytest.param(_black_row(11, 5), id="full_black_row_middle"),
            pytest.param(_black_row(11, 10), id="full_black_row_bottom"),
            pytest.param(_black_col(11, 0), id="full_black_col_left"),
            pytest.param(_black_col(11, 5), id="full_black_col_middle"),
            pytest.param(_black_col(11, 10), id="full_black_col_right"),
        ],
    )
    def test_walkers_agree_on_short_words(self, grid):
        assert _short_words_from_runs(grid) == _short_words_from_slots(grid)
