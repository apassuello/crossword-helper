"""Test cell locking functionality for theme words in Grid class."""

import pytest

from cli.src.core.grid import Grid


class TestCellLocking:
    """Test cell locking functionality for theme word preservation."""

    def test_lock_cells_on_set_letter(self):
        """Test that cells can be locked when setting letters."""
        grid = Grid(11)

        # Set letter without locking
        grid.set_letter(0, 0, "A", lock=False)
        assert (0, 0) not in grid.locked_cells
        assert not grid.is_locked(0, 0)

        # Set letter with locking
        grid.set_letter(0, 1, "B", lock=True)
        assert (0, 1) in grid.locked_cells
        assert grid.is_locked(0, 1)

        # Set another locked letter
        grid.set_letter(1, 0, "C", lock=True)
        assert (1, 0) in grid.locked_cells
        assert grid.is_locked(1, 0)

        # Check total locked cells
        assert len(grid.locked_cells) == 2

    def test_place_word_with_lock(self):
        """Test that place_word can lock all cells of a word."""
        grid = Grid(11)

        # Place word without locking
        grid.place_word("CAT", 0, 0, "across", lock=False)
        assert (0, 0) not in grid.locked_cells
        assert (0, 1) not in grid.locked_cells
        assert (0, 2) not in grid.locked_cells

        # Place word with locking
        grid.place_word("DOG", 2, 0, "across", lock=True)
        assert (2, 0) in grid.locked_cells
        assert (2, 1) in grid.locked_cells
        assert (2, 2) in grid.locked_cells
        assert grid.is_locked(2, 0)
        assert grid.is_locked(2, 1)
        assert grid.is_locked(2, 2)

        # Verify letters were placed
        assert grid.get_cell(2, 0) == "D"
        assert grid.get_cell(2, 1) == "O"
        assert grid.get_cell(2, 2) == "G"

    def test_cannot_overwrite_locked_cells(self):
        """Test that locked cells cannot be overwritten by place_word."""
        grid = Grid(11)

        # Place and lock theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Try to place a conflicting word - should fail
        with pytest.raises(ValueError, match="would overwrite locked cell"):
            grid.place_word("ABCDE", 0, 0, "across", lock=False)

        # Can place crossing word if letters match
        grid.place_word("TENT", 0, 0, "down", lock=False)  # T matches first letter
        assert grid.get_cell(0, 0) == "T"  # Still T from THEME
        assert grid.get_cell(1, 0) == "E"  # From TENT
        assert grid.get_cell(2, 0) == "N"  # From TENT
        assert grid.get_cell(3, 0) == "T"  # From TENT

    def test_remove_word_preserves_locked_cells(self):
        """Test that remove_word does not clear locked cells."""
        grid = Grid(11)

        # Place and lock theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Place overlapping word (not locked)
        grid.place_word("TEST", 0, 0, "down", lock=False)

        # Remove the down word
        grid.remove_word(0, 0, 4, "down")

        # Theme word should still be there (locked)
        assert grid.get_cell(0, 0) == "T"  # Locked from THEME
        assert grid.get_cell(0, 1) == "H"  # Locked from THEME
        assert grid.get_cell(0, 2) == "E"  # Locked from THEME
        assert grid.get_cell(0, 3) == "M"  # Locked from THEME
        assert grid.get_cell(0, 4) == "E"  # Locked from THEME

        # Non-locked cells should be cleared
        assert grid.is_empty(1, 0)  # Was 'E' from TEST
        assert grid.is_empty(2, 0)  # Was 'S' from TEST
        assert grid.is_empty(3, 0)  # Was 'T' from TEST

    def test_clear_unlocked_preserves_locked_cells(self):
        """Test that clear_unlocked only clears non-locked cells."""
        grid = Grid(11)

        # Place some locked theme words
        grid.place_word("THEME", 0, 0, "across", lock=True)
        grid.place_word("WORD", 2, 0, "across", lock=True)

        # Place some unlocked words
        grid.place_word("CAT", 4, 0, "across", lock=False)
        grid.place_word("DOG", 6, 0, "across", lock=False)

        # Add black squares
        grid.set_black_square(8, 0)
        grid.set_black_square(8, 1)

        # Clear all unlocked cells
        grid.clear_unlocked()

        # Theme words should still be there
        assert grid.get_cell(0, 0) == "T"
        assert grid.get_cell(0, 1) == "H"
        assert grid.get_cell(0, 2) == "E"
        assert grid.get_cell(0, 3) == "M"
        assert grid.get_cell(0, 4) == "E"

        assert grid.get_cell(2, 0) == "W"
        assert grid.get_cell(2, 1) == "O"
        assert grid.get_cell(2, 2) == "R"
        assert grid.get_cell(2, 3) == "D"

        # Unlocked words should be cleared
        assert grid.is_empty(4, 0)
        assert grid.is_empty(4, 1)
        assert grid.is_empty(4, 2)
        assert grid.is_empty(6, 0)
        assert grid.is_empty(6, 1)
        assert grid.is_empty(6, 2)

        # Black squares should remain
        assert grid.is_black(8, 0)
        assert grid.is_black(8, 1)

    def test_clone_preserves_locked_cells(self):
        """Test that cloning a grid preserves locked cells."""
        grid = Grid(11)

        # Set up locked and unlocked cells
        grid.place_word("THEME", 0, 0, "across", lock=True)
        grid.place_word("CAT", 2, 0, "across", lock=False)

        # Clone the grid
        cloned = grid.clone()

        # Verify locked cells are preserved
        assert cloned.locked_cells == grid.locked_cells
        assert cloned.is_locked(0, 0)
        assert cloned.is_locked(0, 1)
        assert cloned.is_locked(0, 2)
        assert cloned.is_locked(0, 3)
        assert cloned.is_locked(0, 4)

        # Verify unlocked cells are not locked
        assert not cloned.is_locked(2, 0)
        assert not cloned.is_locked(2, 1)
        assert not cloned.is_locked(2, 2)

        # Verify independence of cloned locked_cells set
        cloned.set_letter(5, 5, "X", lock=True)
        assert (5, 5) in cloned.locked_cells
        assert (5, 5) not in grid.locked_cells

    def test_from_dict_initializes_empty_locked_cells(self):
        """Test that from_dict creates grid with empty locked_cells."""
        data = {
            "size": 11,
            "grid": [
                ["T", "H", "E", "M", "E", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                ["#", "#", "#", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", "#", "#", "#", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
            ],
        }

        grid = Grid.from_dict(data)

        # Verify grid was created
        assert grid.size == 11
        assert grid.get_cell(0, 0) == "T"
        assert grid.get_cell(0, 1) == "H"
        assert grid.get_cell(0, 2) == "E"

        # Verify locked_cells is initialized but empty
        assert hasattr(grid, "locked_cells")
        assert isinstance(grid.locked_cells, set)
        assert len(grid.locked_cells) == 0

    def test_crossing_locked_words_allowed(self):
        """Test that crossing words work when letters match at locked cells."""
        grid = Grid(11)

        # Place horizontal theme word and lock it
        grid.place_word("THEME", 2, 1, "across", lock=True)

        # Place crossing words that share letters with theme
        # T at (2, 1) - Place a word that has 'T' at position 2
        grid.place_word("ART", 0, 1, "down", lock=False)
        assert grid.get_cell(2, 1) == "T"  # Still locked from THEME

        # H at (2, 2) - Place a word that has 'H' at position 0
        grid.place_word("HASH", 2, 2, "down", lock=False)
        assert grid.get_cell(2, 2) == "H"  # Still locked from THEME

        # Verify all cells are correct
        assert grid.get_cell(0, 1) == "A"  # From ART
        assert grid.get_cell(1, 1) == "R"  # From ART
        assert grid.get_cell(2, 1) == "T"  # From THEME (locked)

        assert grid.get_cell(2, 2) == "H"  # From THEME (locked)
        assert grid.get_cell(3, 2) == "A"  # From HASH
        assert grid.get_cell(4, 2) == "S"  # From HASH
        assert grid.get_cell(5, 2) == "H"  # From HASH

        # Try to place a conflicting crossing word
        with pytest.raises(ValueError, match="would overwrite locked cell"):
            grid.place_word("ABCD", 0, 3, "down", lock=False)  # Would put 'C' where 'E' is at (2,3)

    # ------------------------------------------------------------------
    # novice-readiness spec 0.2.4 §2.1 (C12, C10, D3, D2): normative rows
    # fd1-fd9, td1-td4, sl1-sl3, bs1-bs3 of Task 2.1.
    # ------------------------------------------------------------------

    @staticmethod
    def _g33_cat(**extra):
        """G33 with CAT across row 0; ``extra`` keys are merged into the dict."""
        data = {"size": 3, "grid": [["C", "A", "T"], [".", ".", "."], [".", ".", "."]]}
        data.update(extra)
        return data

    def _fd1_grid(self):
        return Grid.from_dict(self._g33_cat(locked=[[0, 0], [0, 2]]), strict_size=False)

    def test_fd1_from_dict_applies_locked(self):
        assert self._fd1_grid().locked_cells == {(0, 0), (0, 2)}

    def test_fd2_from_dict_empty_locked_locks_nothing(self):
        grid = Grid.from_dict(self._g33_cat(locked=[]), strict_size=False)
        assert grid.locked_cells == set()

    def test_fd3_from_dict_absent_locked_locks_nothing(self):
        grid = Grid.from_dict(self._g33_cat(), strict_size=False)
        assert grid.locked_cells == set()

    def test_fd4_from_dict_out_of_bounds_raises(self):
        with pytest.raises(ValueError):
            Grid.from_dict(self._g33_cat(locked=[[3, 0]]), strict_size=False)

    def test_fd5_from_dict_negative_index_raises(self):
        # A negative index is out of bounds, not Python negative indexing.
        with pytest.raises(ValueError):
            Grid.from_dict(self._g33_cat(locked=[[-1, 0]]), strict_size=False)

    def test_fd5b_negative_col_wrapping_onto_a_letter_raises_out_of_bounds(self):
        # (0, -1) would wrap to (0, 2) == "T" if the lower bound were dropped,
        # so only the bounds check (not the no-letter check) can reject it.
        with pytest.raises(ValueError, match="out of bounds"):
            Grid.from_dict(self._g33_cat(locked=[[0, -1]]), strict_size=False)

    def test_fd5c_negative_row_wrapping_onto_a_letter_raises_out_of_bounds(self):
        # (-1, 0) wraps to (2, 0), which holds a letter here.
        data = {"size": 3, "grid": [[".", ".", "."], [".", ".", "."], ["C", ".", "."]], "locked": [[-1, 0]]}
        with pytest.raises(ValueError, match="out of bounds"):
            Grid.from_dict(data, strict_size=False)

    def test_fd6_from_dict_locked_empty_cell_raises(self):
        with pytest.raises(ValueError):
            Grid.from_dict(self._g33_cat(locked=[[1, 1]]), strict_size=False)

    def test_fd7_from_dict_locked_black_cell_raises(self):
        data = {"size": 3, "grid": [["C", "A", "T"], [".", "#", "."], [".", ".", "."]], "locked": [[1, 1]]}
        with pytest.raises(ValueError):
            Grid.from_dict(data, strict_size=False)

    @pytest.mark.parametrize("locked", [[[0]], [[0, 0, 1]], [["0", 0]], [[True, 0]], "0,0"])
    def test_fd8_from_dict_malformed_locked_raises(self, locked):
        with pytest.raises(ValueError):
            Grid.from_dict(self._g33_cat(locked=locked), strict_size=False)

    def test_fd8b_bool_entry_is_not_an_int(self):
        # True == 1 and (0, 1) holds "A" in this grid, so without the bool
        # rejection the entry would be accepted as a valid lock.
        with pytest.raises(ValueError, match="pair of ints"):
            Grid.from_dict(self._g33_cat(locked=[[0, True]]), strict_size=False)

    def test_fd9_from_dict_duplicate_entries_collapse(self):
        grid = Grid.from_dict(self._g33_cat(locked=[[0, 0], [0, 0]]), strict_size=False)
        assert grid.locked_cells == {(0, 0)}

    def test_td1_to_dict_default_has_no_locked_key(self):
        assert set(self._fd1_grid().to_dict().keys()) == {"size", "grid", "black_squares", "is_symmetric"}

    def test_td2_to_dict_include_locks_lists_locked_cells(self):
        assert self._fd1_grid().to_dict(include_locks=True)["locked"] == [[0, 0], [0, 2]]

    def test_td3_to_dict_include_locks_empty(self):
        grid = Grid.from_dict(self._g33_cat(locked=[]), strict_size=False)
        assert grid.to_dict(include_locks=True)["locked"] == []

    def test_td4_locks_survive_clone_and_dict_round_trip(self):
        grid = self._fd1_grid()
        cloned = grid.clone()
        rebuilt = Grid.from_dict(grid.to_dict(include_locks=True), strict_size=False)
        for other in (cloned, rebuilt):
            assert other.locked_cells == {(0, 0), (0, 2)}
            assert other.to_dict()["grid"] == grid.to_dict()["grid"]

    @pytest.mark.parametrize("letter", ["C", "c"])
    def test_sl1_set_letter_same_letter_on_locked_cell_succeeds(self, letter):
        grid = self._fd1_grid()
        grid.set_letter(0, 0, letter)
        assert grid.get_cell(0, 0) == "C"

    def test_sl2_set_letter_different_letter_on_locked_cell_raises(self):
        grid = self._fd1_grid()
        with pytest.raises(ValueError):
            grid.set_letter(0, 0, "D")
        assert grid.get_cell(0, 0) == "C"

    def test_sl3_set_letter_on_unlocked_cell_succeeds(self):
        grid = self._fd1_grid()
        grid.set_letter(1, 1, "D")
        assert grid.get_cell(1, 1) == "D"

    def test_bs1_set_black_square_on_locked_cell_raises(self):
        grid = self._fd1_grid()
        with pytest.raises(ValueError):
            grid.set_black_square(0, 0)
        assert grid.get_cell(0, 0) == "C"
        assert grid.get_cell(2, 2) == "."

    def test_bs2_set_black_square_with_locked_partner_raises(self):
        grid = self._fd1_grid()
        with pytest.raises(ValueError):
            grid.set_black_square(2, 0)  # 180-degree partner is (0, 2), locked
        assert grid.get_cell(2, 0) == "."
        assert grid.get_cell(0, 2) == "T"

    def test_bs3_set_black_square_without_symmetry_checks_only_the_cell(self):
        grid = self._fd1_grid()
        grid.set_black_square(2, 0, enforce_symmetry=False)
        assert grid.get_cell(2, 0) == "#"
        assert grid.get_cell(0, 2) == "T"
