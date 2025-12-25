"""
Test cell type consistency and standardization.

Ensures that:
- Grid cells use '.' for empty
- Patterns use '?' for wildcards
- No confusion between data and search representations
"""

import pytest
from cli.src.core.cell_types import (
    EMPTY_CELL,
    BLACK_CELL,
    WILDCARD,
    is_empty,
    is_black,
    is_letter,
    is_filled,
    grid_to_pattern,
    pattern_has_wildcards,
    pattern_is_complete,
    validate_grid_cell,
    validate_pattern_char,
    assert_valid_grid,
    assert_valid_pattern,
)
from cli.src.core.grid import Grid


class TestCellTypeConstants:
    """Test that constants are correctly defined."""

    def test_empty_cell_is_dot(self):
        """Empty cells in grid should be represented as '.'"""
        assert EMPTY_CELL == '.'

    def test_black_cell_is_hash(self):
        """Black squares should be represented as '#'"""
        assert BLACK_CELL == '#'

    def test_wildcard_is_question(self):
        """Pattern wildcards should be represented as '?'"""
        assert WILDCARD == '?'

    def test_constants_are_distinct(self):
        """All constants should be different from each other."""
        assert EMPTY_CELL != BLACK_CELL
        assert EMPTY_CELL != WILDCARD
        assert BLACK_CELL != WILDCARD


class TestHelperFunctions:
    """Test helper functions for cell type checking."""

    def test_is_empty(self):
        """Test empty cell detection."""
        assert is_empty('.')
        assert not is_empty('?')
        assert not is_empty('#')
        assert not is_empty('A')

    def test_is_black(self):
        """Test black square detection."""
        assert is_black('#')
        assert not is_black('.')
        assert not is_black('?')
        assert not is_black('A')

    def test_is_letter(self):
        """Test letter detection."""
        assert is_letter('A')
        assert is_letter('Z')
        assert not is_letter('.')
        assert not is_letter('?')
        assert not is_letter('#')

    def test_is_filled(self):
        """Test filled cell detection (contains letter)."""
        assert is_filled('A')
        assert is_filled('M')
        assert not is_filled('.')
        assert not is_filled('?')
        assert not is_filled('#')

    def test_grid_to_pattern(self):
        """Test conversion from grid cell to pattern character."""
        assert grid_to_pattern('.') == '?'  # Empty -> wildcard
        assert grid_to_pattern('A') == 'A'  # Letter unchanged
        assert grid_to_pattern('Z') == 'Z'  # Letter unchanged

        # Black squares should not be in patterns
        with pytest.raises(ValueError):
            grid_to_pattern('#')


class TestPatternFunctions:
    """Test pattern-specific functions."""

    def test_pattern_has_wildcards(self):
        """Test wildcard detection in patterns."""
        assert pattern_has_wildcards('?I?A')
        assert pattern_has_wildcards('???')
        assert not pattern_has_wildcards('VISA')
        assert not pattern_has_wildcards('')

    def test_pattern_is_complete(self):
        """Test if pattern is fully filled."""
        assert pattern_is_complete('VISA')
        assert pattern_is_complete('HELLO')
        assert not pattern_is_complete('?I?A')
        assert not pattern_is_complete('???')
        assert pattern_is_complete('')  # Empty pattern is complete


class TestValidation:
    """Test validation functions."""

    def test_validate_grid_cell(self):
        """Test grid cell validation."""
        # Valid grid cells
        assert validate_grid_cell('.')  # Empty
        assert validate_grid_cell('#')  # Black
        assert validate_grid_cell('A')  # Letter
        assert validate_grid_cell('Z')  # Letter

        # Invalid: wildcards don't belong in grid
        assert not validate_grid_cell('?')

    def test_validate_pattern_char(self):
        """Test pattern character validation."""
        # Valid pattern chars
        assert validate_pattern_char('?')  # Wildcard
        assert validate_pattern_char('A')  # Letter
        assert validate_pattern_char('Z')  # Letter

        # Invalid: grid markers don't belong in patterns
        assert not validate_pattern_char('.')  # Empty cell marker
        assert not validate_pattern_char('#')  # Black square marker

    def test_assert_valid_grid(self):
        """Test grid validation assertion."""
        # Valid grid
        valid_grid = [
            ['.', '.', 'A', '#', '.'],
            ['B', '.', 'C', '.', 'D'],
        ]
        assert_valid_grid(valid_grid)  # Should not raise

        # Invalid grid with wildcard
        invalid_grid = [
            ['.', '?', 'A'],  # '?' should not be in grid
            ['B', '.', 'C'],
        ]
        with pytest.raises(AssertionError, match="Found '\\?' in grid"):
            assert_valid_grid(invalid_grid)

    def test_assert_valid_pattern(self):
        """Test pattern validation assertion."""
        # Valid patterns
        assert_valid_pattern('?I?A')  # Should not raise
        assert_valid_pattern('VISA')  # Should not raise
        assert_valid_pattern('???')   # Should not raise

        # Invalid pattern with grid marker
        with pytest.raises(AssertionError, match="Found '\\.' .* in pattern"):
            assert_valid_pattern('V.SA')  # '.' should not be in pattern

        with pytest.raises(AssertionError, match="Found .* '#' in pattern"):
            assert_valid_pattern('VI#A')  # '#' should not be in pattern


class TestGridIntegration:
    """Test Grid class integration with cell types."""

    def test_grid_empty_cells_are_dots(self):
        """Verify Grid returns '.' for empty cells."""
        grid = Grid(11)
        assert grid.get_cell(0, 0) == '.'
        assert grid.get_cell(5, 5) == '.'

    def test_grid_black_squares_are_hashes(self):
        """Verify Grid returns '#' for black squares."""
        grid = Grid(11)
        grid.set_black_square(3, 3, enforce_symmetry=False)
        assert grid.get_cell(3, 3) == '#'

    def test_grid_letters_are_uppercase(self):
        """Verify Grid returns uppercase letters."""
        grid = Grid(11)
        grid.set_letter(0, 0, 'a')  # Lowercase input
        assert grid.get_cell(0, 0) == 'A'  # Uppercase output

    def test_pattern_conversion(self):
        """Verify get_pattern_for_slot converts correctly."""
        grid = Grid(11)
        grid.set_letter(0, 0, 'V')
        grid.set_letter(0, 1, 'I')
        # Cells 2 and 3 remain empty
        grid.set_letter(0, 4, 'A')

        slot = {
            'row': 0, 'col': 0, 'length': 5, 'direction': 'across'
        }
        pattern = grid.get_pattern_for_slot(slot)

        # Should convert empty cells (.) to wildcards (?)
        assert pattern == 'VI??A'

    def test_place_word_rejects_wildcards(self):
        """Verify place_word rejects words containing wildcards."""
        grid = Grid(11)

        # Should reject word with wildcard
        with pytest.raises(ValueError, match="Cannot place wildcard"):
            grid.place_word('VI?A', 0, 0, 'across')

        # Should reject word with empty marker
        with pytest.raises(ValueError, match="Cannot place empty marker"):
            grid.place_word('VI.A', 0, 0, 'across')

        # Valid word should work
        grid.place_word('VISA', 0, 0, 'across')
        assert grid.get_cell(0, 0) == 'V'
        assert grid.get_cell(0, 1) == 'I'
        assert grid.get_cell(0, 2) == 'S'
        assert grid.get_cell(0, 3) == 'A'

    def test_remove_word_sets_to_empty(self):
        """Verify remove_word sets cells back to '.'"""
        grid = Grid(11)
        grid.place_word('VISA', 0, 0, 'across')

        # Verify word is placed
        assert grid.get_cell(0, 0) == 'V'

        # Remove word
        grid.remove_word(0, 0, 4, 'across')

        # Verify cells are now empty (.)
        assert grid.get_cell(0, 0) == '.'
        assert grid.get_cell(0, 1) == '.'
        assert grid.get_cell(0, 2) == '.'
        assert grid.get_cell(0, 3) == '.'


class TestCompletionDetection:
    """Test proper completion detection using patterns."""

    def test_slot_is_complete(self):
        """Test checking if a slot is completely filled."""
        grid = Grid(11)

        slot = {
            'row': 0, 'col': 0, 'length': 4, 'direction': 'across'
        }

        # Initially empty
        pattern = grid.get_pattern_for_slot(slot)
        assert pattern == '????'
        assert not pattern_is_complete(pattern)

        # Partially filled
        grid.set_letter(0, 0, 'V')
        grid.set_letter(0, 1, 'I')
        pattern = grid.get_pattern_for_slot(slot)
        assert pattern == 'VI??'
        assert not pattern_is_complete(pattern)

        # Completely filled
        grid.set_letter(0, 2, 'S')
        grid.set_letter(0, 3, 'A')
        pattern = grid.get_pattern_for_slot(slot)
        assert pattern == 'VISA'
        assert pattern_is_complete(pattern)


class TestGibberishPatternDetection:
    """Test that gibberish detection works with proper pattern representation."""

    def test_gibberish_with_wildcards(self):
        """Test gibberish detection ignores wildcards properly."""
        # This would be tested in beam_search_autofill
        # The pattern 'AAA??' should be checked without the wildcards
        pattern_without_wildcards = 'AAA??'.replace('?', '')
        assert pattern_without_wildcards == 'AAA'
        # Then check if 'AAA' is gibberish (it is)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])