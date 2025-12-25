"""
Unit tests for grid numbering.
"""
import pytest
from backend.core.numbering import NumberingValidator


class TestNumberingValidator:
    """Test suite for NumberingValidator class."""

    def test_auto_number_simple_3x3(self):
        """Test auto-numbering on simple 3×3 grid."""
        validator = NumberingValidator()
        
        grid = [
            ['R', 'A', 'T'],
            ['#', 'T', '#'],
            ['C', 'A', 'T']
        ]
        
        numbering = validator.auto_number(grid)
        
        # Expected numbering:
        # 1 2   (1: R starts across, 2: A starts down)
        # #   # (T in middle doesn't start any word)
        # 3     (3: C starts across)
        
        assert numbering[(0, 0)] == 1  # R starts across
        assert numbering[(0, 1)] == 2  # A starts down
        assert numbering[(2, 0)] == 3  # C starts across
        assert len(numbering) == 3

    def test_auto_number_all_across(self):
        """Test grid with only across words."""
        validator = NumberingValidator()
        
        grid = [
            ['C', 'A', 'T'],
            ['#', '#', '#'],
            ['D', 'O', 'G']
        ]
        
        numbering = validator.auto_number(grid)
        
        assert numbering[(0, 0)] == 1  # C
        assert numbering[(2, 0)] == 2  # D
        assert len(numbering) == 2

    def test_validate_correct_numbering(self):
        """Test validation with correct numbering."""
        validator = NumberingValidator()
        
        grid = [
            ['R', 'A', 'T'],
            ['#', 'T', '#'],
            ['C', 'A', 'T']
        ]
        
        correct_numbering = {
            (0, 0): 1,  # R
            (0, 1): 2,  # A (first row)
            (2, 0): 3   # C
        }
        
        is_valid, errors = validator.validate(grid, correct_numbering)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_wrong_numbering(self):
        """Test validation with wrong numbering."""
        validator = NumberingValidator()
        
        grid = [
            ['R', 'A', 'T'],
            ['#', 'T', '#'],
            ['C', 'A', 'T']
        ]
        
        wrong_numbering = {
            (0, 0): 1,
            (0, 1): 3,  # Wrong! Should be 2
            (2, 0): 2   # Wrong! Should be 3
        }
        
        is_valid, errors = validator.validate(grid, wrong_numbering)
        
        assert is_valid is False
        assert len(errors) == 2  # Two wrong numbers

    def test_analyze_grid(self):
        """Test grid analysis."""
        validator = NumberingValidator()
        
        grid = [
            ['R', 'A', 'T'],
            ['#', 'T', '#'],
            ['C', 'A', 'T']
        ]
        
        info = validator.analyze_grid(grid)
        
        assert info['size'] == [3, 3]
        assert info['black_squares'] == 2  # Two # symbols
        assert info['white_squares'] == 7  # Seven letter cells
        assert isinstance(info['black_square_percentage'], (int, float))
        assert isinstance(info['meets_nyt_standards'], bool)
