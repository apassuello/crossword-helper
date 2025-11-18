"""
Unit tests for Grid class.
"""

import pytest
import numpy as np
from src.core.grid import Grid, BLACK_SQUARE, EMPTY_CELL


class TestGridInitialization:
    """Test Grid initialization."""

    def test_valid_sizes(self):
        """Test grid creation with valid sizes."""
        for size in [11, 15, 21]:
            grid = Grid(size)
            assert grid.size == size
            assert grid.cells.shape == (size, size)
            assert np.all(grid.cells == EMPTY_CELL)

    def test_invalid_size(self):
        """Test grid creation with invalid size."""
        with pytest.raises(ValueError, match="Grid size must be 11, 15, or 21"):
            Grid(10)

        with pytest.raises(ValueError, match="Grid size must be 11, 15, or 21"):
            Grid(16)


class TestBlackSquares:
    """Test black square operations."""

    def test_set_black_square_without_symmetry(self):
        """Test setting black square without symmetry enforcement."""
        grid = Grid(11)
        grid.set_black_square(0, 0, enforce_symmetry=False)

        assert grid.is_black(0, 0)
        assert not grid.is_black(10, 10)  # Symmetric position should not be black

    def test_set_black_square_with_symmetry(self):
        """Test setting black square with automatic symmetry."""
        grid = Grid(11)
        grid.set_black_square(0, 0, enforce_symmetry=True)

        assert grid.is_black(0, 0)
        assert grid.is_black(10, 10)  # Symmetric position should also be black

    def test_set_black_square_default_symmetry(self):
        """Test that symmetry is enforced by default."""
        grid = Grid(11)
        grid.set_black_square(2, 3)  # Default enforce_symmetry=True

        assert grid.is_black(2, 3)
        assert grid.is_black(8, 7)  # (11-1-2, 11-1-3) = (8, 7)

    def test_multiple_black_squares(self):
        """Test setting multiple black squares."""
        grid = Grid(11)
        grid.set_black_square(0, 0)
        grid.set_black_square(1, 1)
        grid.set_black_square(2, 2)

        # Check all positions and their symmetric counterparts
        assert grid.is_black(0, 0) and grid.is_black(10, 10)
        assert grid.is_black(1, 1) and grid.is_black(9, 9)
        assert grid.is_black(2, 2) and grid.is_black(8, 8)

    def test_invalid_black_square_position(self):
        """Test setting black square at invalid position."""
        grid = Grid(11)

        with pytest.raises(ValueError, match="out of bounds"):
            grid.set_black_square(-1, 0)

        with pytest.raises(ValueError, match="out of bounds"):
            grid.set_black_square(0, 11)


class TestLetters:
    """Test letter operations."""

    def test_set_letter(self):
        """Test setting a letter."""
        grid = Grid(11)
        grid.set_letter(0, 0, 'A')

        assert grid.get_cell(0, 0) == 'A'
        assert not grid.is_black(0, 0)

    def test_set_multiple_letters(self):
        """Test setting multiple letters."""
        grid = Grid(11)
        grid.set_letter(0, 0, 'C')
        grid.set_letter(0, 1, 'A')
        grid.set_letter(0, 2, 'T')

        assert grid.get_cell(0, 0) == 'C'
        assert grid.get_cell(0, 1) == 'A'
        assert grid.get_cell(0, 2) == 'T'

    def test_set_letter_lowercase(self):
        """Test setting lowercase letter (should be converted to uppercase)."""
        grid = Grid(11)
        grid.set_letter(0, 0, 'a')

        assert grid.get_cell(0, 0) == 'A'  # 'a' -> 'A'

    def test_invalid_letter(self):
        """Test setting invalid letter."""
        grid = Grid(11)

        with pytest.raises(ValueError, match="Letter must be single character A-Z"):
            grid.set_letter(0, 0, '1')

        with pytest.raises(ValueError, match="Letter must be single character A-Z"):
            grid.set_letter(0, 0, '@')

    def test_overwrite_black_square_with_letter(self):
        """Test that setting a letter overwrites a black square."""
        grid = Grid(11)
        grid.set_black_square(0, 0, enforce_symmetry=False)
        assert grid.is_black(0, 0)

        grid.set_letter(0, 0, 'A')
        assert not grid.is_black(0, 0)
        assert grid.get_cell(0, 0) == 'A'


class TestSymmetry:
    """Test symmetry checking."""

    def test_empty_grid_is_symmetric(self):
        """Test that empty grid is symmetric."""
        grid = Grid(11)
        assert grid.check_symmetry()

    def test_symmetric_pattern(self):
        """Test symmetric black square pattern."""
        grid = Grid(11)
        grid.set_black_square(0, 0)  # Automatically sets (10, 10)
        grid.set_black_square(1, 5)  # Automatically sets (9, 5)

        assert grid.check_symmetry()

    def test_asymmetric_pattern(self):
        """Test asymmetric pattern detection."""
        grid = Grid(11)
        grid.set_black_square(0, 0, enforce_symmetry=False)
        # (10, 10) is not black, so grid is asymmetric

        assert not grid.check_symmetry()

    def test_center_square_symmetry(self):
        """Test that center square is its own symmetric partner."""
        grid = Grid(11)
        grid.set_black_square(5, 5)  # Center of 11x11 grid

        assert grid.check_symmetry()
        assert grid.is_black(5, 5)


class TestWordSlots:
    """Test word slot detection."""

    def test_simple_across_word(self):
        """Test detecting simple across word."""
        grid = Grid(11)
        # Grid: C A T . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        grid.set_letter(0, 0, 'C')
        grid.set_letter(0, 1, 'A')
        grid.set_letter(0, 2, 'T')

        slots = grid.get_word_slots()
        across_slots = [s for s in slots if s['direction'] == 'across']

        # Should find one across slot starting at (0, 0) with length 11 (entire row)
        assert len(across_slots) > 0
        assert any(s['row'] == 0 and s['col'] == 0 and s['length'] == 11 for s in across_slots)

    def test_simple_down_word(self):
        """Test detecting simple down word."""
        grid = Grid(11)
        # Grid: C . . . .
        #       A . . . .
        #       T . . . .
        #       . . . . .
        #       . . . . .
        grid.set_letter(0, 0, 'C')
        grid.set_letter(1, 0, 'A')
        grid.set_letter(2, 0, 'T')

        slots = grid.get_word_slots()
        down_slots = [s for s in slots if s['direction'] == 'down']

        # Should find one down slot starting at (0, 0) with length 11 (entire column)
        assert len(down_slots) > 0
        assert any(s['row'] == 0 and s['col'] == 0 and s['length'] == 11 for s in down_slots)

    def test_word_slots_with_black_squares(self):
        """Test word slot detection with black squares."""
        grid = Grid(11)
        # Grid: C A T # .
        #       # . . # .
        #       . . . # .
        #       # . . # .
        #       . . . # .
        grid.set_letter(0, 0, 'C')
        grid.set_letter(0, 1, 'A')
        grid.set_letter(0, 2, 'T')
        grid.set_black_square(0, 3, enforce_symmetry=False)
        grid.set_black_square(1, 0, enforce_symmetry=False)

        slots = grid.get_word_slots()
        across_slots = [s for s in slots if s['direction'] == 'across' and s['row'] == 0]

        # Should find across slot (0,0) with length 3 (CAT), not 5
        assert any(s['row'] == 0 and s['col'] == 0 and s['length'] == 3 for s in across_slots)

    def test_minimum_word_length(self):
        """Test that only slots of length ≥3 are returned."""
        grid = Grid(11)
        # Grid: C A # T #
        #       . . . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        grid.set_letter(0, 0, 'C')
        grid.set_letter(0, 1, 'A')
        grid.set_black_square(0, 2, enforce_symmetry=False)
        grid.set_letter(0, 3, 'T')
        grid.set_black_square(0, 4, enforce_symmetry=False)

        slots = grid.get_word_slots()
        across_slots = [s for s in slots if s['direction'] == 'across' and s['row'] == 0]

        # Should NOT find 2-letter slot "CA" or 1-letter slot "T"
        assert not any(s['row'] == 0 and s['col'] == 0 and s['length'] == 2 for s in across_slots)
        assert not any(s['row'] == 0 and s['col'] == 3 and s['length'] == 1 for s in across_slots)


class TestImportExport:
    """Test grid serialization."""

    def test_to_dict_empty_grid(self):
        """Test exporting empty grid to dict."""
        grid = Grid(11)
        data = grid.to_dict()

        assert data['size'] == 11
        assert len(data['grid']) == 11
        assert all(len(row) == 11 for row in data['grid'])
        assert all(cell == '.' for row in data['grid'] for cell in row)

    def test_to_dict_with_content(self):
        """Test exporting grid with content."""
        grid = Grid(11)
        grid.set_black_square(0, 0)
        grid.set_letter(1, 1, 'A')

        data = grid.to_dict()

        assert data['grid'][0][0] == '#'
        assert data['grid'][10][10] == '#'  # Symmetric
        assert data['grid'][1][1] == 'A'

    def test_from_dict(self):
        """Test importing grid from dict."""
        # Create 11x11 grid with some content
        grid_data = [['.' for _ in range(11)] for _ in range(11)]
        grid_data[0][0] = '#'
        grid_data[10][10] = '#'  # Symmetric
        grid_data[1][1] = 'A'

        data = {
            'size': 11,
            'grid': grid_data
        }

        grid = Grid.from_dict(data)

        assert grid.size == 11
        assert grid.is_black(0, 0)
        assert grid.is_black(10, 10)
        assert grid.get_cell(1, 1) == 'A'

    def test_roundtrip_serialization(self):
        """Test that grid survives export->import cycle."""
        original = Grid(11)
        original.set_black_square(0, 0)
        original.set_black_square(2, 5)
        original.set_letter(1, 1, 'T')
        original.set_letter(1, 2, 'E')
        original.set_letter(1, 3, 'S')
        original.set_letter(1, 4, 'T')

        # Export and reimport
        data = original.to_dict()
        restored = Grid.from_dict(data)

        # Compare
        assert restored.size == original.size
        assert np.array_equal(restored.cells, original.cells)
        assert restored.check_symmetry() == original.check_symmetry()
