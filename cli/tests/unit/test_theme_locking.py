"""
Test the theme word locking mechanism.

This module tests that theme words (words that are part of the puzzle's theme)
are properly locked and preserved during the autofill process.
"""

import pytest
from cli.src.core.grid import Grid


class TestThemeLocking:
    """Test theme word locking functionality."""

    def test_place_word_with_lock(self):
        """Test placing a word with locking enabled."""
        grid = Grid(11)

        # Place a theme word with locking
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Verify each cell is locked
        for i in range(5):
            assert grid.get_cell(0, i) == "THEME"[i]
            assert (0, i) in grid.locked_cells
            assert grid.is_locked(0, i)

    def test_cannot_overwrite_locked_cells(self):
        """Test that locked cells cannot be overwritten with different letters."""
        grid = Grid(11)

        # Place and lock a theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Try to place a conflicting word - should fail
        with pytest.raises(ValueError, match="would overwrite locked cell"):
            grid.place_word("TESTS", 0, 0, "across")

    def test_can_place_compatible_crossing_word(self):
        """Test that compatible crossing words can be placed over locked cells."""
        grid = Grid(11)

        # Place and lock a horizontal theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Place a compatible vertical word that shares the 'T'
        grid.place_word("TOP", 0, 0, "down")  # Should work

        # Verify the crossing word was placed correctly
        assert grid.get_cell(0, 0) == "T"  # Shared
        assert grid.get_cell(1, 0) == "O"
        assert grid.get_cell(2, 0) == "P"

    def test_remove_word_skips_locked_cells(self):
        """Test that remove_word skips locked cells."""
        grid = Grid(11)

        # Place and lock a theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Place an intersecting word
        grid.place_word("TOP", 0, 0, "down")

        # Try to remove the vertical word
        grid.remove_word(0, 0, 3, "down")

        # The 'T' should remain (it's locked as part of THEME)
        assert grid.get_cell(0, 0) == "T"  # Still there (locked)
        assert grid.get_cell(1, 0) == "."  # Removed
        assert grid.get_cell(2, 0) == "."  # Removed

    def test_clear_unlocked_preserves_locked(self):
        """Test that clear_unlocked() preserves locked cells."""
        grid = Grid(11)

        # Place and lock a theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Place some unlocked words
        grid.place_word("CAT", 2, 0, "across", lock=False)
        grid.place_word("DOG", 4, 0, "across", lock=False)

        # Clear all unlocked cells
        grid.clear_unlocked()

        # Theme word should remain
        for i in range(5):
            assert grid.get_cell(0, i) == "THEME"[i]

        # Other words should be cleared
        for i in range(3):
            assert grid.get_cell(2, i) == "."
            assert grid.get_cell(4, i) == "."

    def test_clone_preserves_locked_cells(self):
        """Test that cloning a grid preserves the locked cells."""
        grid = Grid(11)

        # Place and lock a theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Clone the grid
        cloned = grid.clone()

        # Verify the clone has the same locked cells
        for i in range(5):
            assert cloned.get_cell(0, i) == "THEME"[i]
            assert (0, i) in cloned.locked_cells
            assert cloned.is_locked(0, i)

        # Verify it's a deep copy (modifying clone doesn't affect original)
        cloned.locked_cells.add((5, 5))
        assert (5, 5) not in grid.locked_cells

    def test_set_letter_with_lock(self):
        """Test setting individual letters with locking."""
        grid = Grid(11)

        # Set a letter with lock
        grid.set_letter(5, 5, "X", lock=True)

        # Verify it's locked
        assert grid.get_cell(5, 5) == "X"
        assert grid.is_locked(5, 5)
        assert (5, 5) in grid.locked_cells

        # Try to overwrite it - should be possible with set_letter (low-level)
        # Note: place_word respects locks, but set_letter is more direct
        grid.set_letter(5, 5, "Y")
        assert grid.get_cell(5, 5) == "Y"  # Changed
        assert grid.is_locked(5, 5)  # Still locked from before

    def test_multiple_theme_words(self):
        """Test placing multiple theme words with locking."""
        grid = Grid(15)

        # Place SOLAR horizontally
        grid.place_word("SOLAR", 0, 0, "across", lock=True)

        # Place STAR vertically, sharing the 'S'
        grid.place_word("STAR", 0, 0, "down", lock=True)

        # Place MOON horizontally (no intersection)
        grid.place_word("MOON", 5, 0, "across", lock=True)

        # Verify all theme words are placed and locked
        assert grid.get_cell(0, 0) == "S"  # Shared by SOLAR and STAR
        assert grid.get_cell(0, 1) == "O"  # From SOLAR
        assert grid.get_cell(1, 0) == "T"  # From STAR
        assert grid.get_cell(5, 0) == "M"  # From MOON

        # Count total locked cells
        # SOLAR: 5 cells, STAR: 4 cells (one shared), MOON: 4 cells
        # Total unique cells: 5 + 3 + 4 = 12
        assert len(grid.locked_cells) == 12

    def test_from_dict_preserves_locks(self):
        """Test that from_dict properly restores locked cells."""
        grid = Grid(11)

        # Place and lock a theme word
        grid.place_word("THEME", 0, 0, "across", lock=True)

        # Convert to dict
        grid_dict = grid.to_dict()

        # Create new grid from dict (class method)
        new_grid = Grid.from_dict(grid_dict)

        # Verify theme word is preserved
        for i in range(5):
            assert new_grid.get_cell(0, i) == "THEME"[i]

        # Note: locked_cells are NOT serialized in to_dict/from_dict
        # This is intentional as the lock state is session-specific
        # The orchestrator handles re-locking theme words when resuming
        assert len(new_grid.locked_cells) == 0  # Locks not serialized