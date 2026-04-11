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
