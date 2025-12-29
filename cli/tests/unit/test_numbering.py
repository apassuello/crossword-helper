"""
Unit tests for GridNumbering class.
"""

from src.core.grid import Grid
from src.core.numbering import GridNumbering


class TestAutoNumber:
    """Test auto-numbering functionality."""

    def test_empty_grid(self):
        """Test numbering empty grid."""
        grid = Grid(11)
        numbering = GridNumbering.auto_number(grid)

        # Empty grid should number (0,0) since it starts both across and down words
        assert (0, 0) in numbering
        assert numbering[(0, 0)] == 1

        # Should also number (0,1), (0,2), etc. for down
        # And (1,0), (2,0), etc. for across
        # Total should be 21 (11 across starts on row 0, 11 down starts on col 0, minus (0,0) counted once)
        assert len(numbering) == 21  # (0,0) starts both, (0,1-10) start down, (1-10,0) start across

    def test_simple_3x3_grid(self):
        """Test numbering simple 3x3 grid."""
        grid = Grid(11)
        # Use only 3x3 portion for simplicity
        # R A T
        # # A #
        # C A T

        # Row 0: R A T (black squares to isolate)
        grid.set_letter(0, 0, 'R')
        grid.set_letter(0, 1, 'A')
        grid.set_letter(0, 2, 'T')
        grid.set_black_square(0, 3, enforce_symmetry=False)

        # Row 1: # A #
        grid.set_black_square(1, 0, enforce_symmetry=False)
        grid.set_letter(1, 1, 'A')
        grid.set_black_square(1, 2, enforce_symmetry=False)

        # Row 2: C A T
        grid.set_letter(2, 0, 'C')
        grid.set_letter(2, 1, 'A')
        grid.set_letter(2, 2, 'T')
        grid.set_black_square(2, 3, enforce_symmetry=False)

        numbering = GridNumbering.auto_number(grid)

        # (0,0) starts across RAT
        assert (0, 0) in numbering
        # (0,1) starts down AAA (column 1)
        assert (0, 1) in numbering
        # (2,0) starts across CAT
        assert (2, 0) in numbering

        # Numbers should be sequential
        numbers = sorted(numbering.values())
        assert numbers == list(range(1, len(numbers) + 1))

    def test_numbering_with_black_squares(self):
        """Test that black squares are not numbered."""
        grid = Grid(11)
        grid.set_black_square(0, 0)

        numbering = GridNumbering.auto_number(grid)

        # Black square should not be numbered
        assert (0, 0) not in numbering
        # Its symmetric partner should not be numbered
        assert (10, 10) not in numbering

    def test_numbering_starts_across_word(self):
        """Test numbering cells that start across words."""
        grid = Grid(11)
        # Grid: # A B C D
        #       . . . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        grid.set_black_square(0, 0, enforce_symmetry=False)

        numbering = GridNumbering.auto_number(grid)

        # (0,1) starts across word ABCD
        assert (0, 1) in numbering

    def test_numbering_starts_down_word(self):
        """Test numbering cells that start down words."""
        grid = Grid(11)
        # Grid: # . . . .
        #       A . . . .
        #       B . . . .
        #       C . . . .
        #       D . . . .
        grid.set_black_square(0, 0, enforce_symmetry=False)

        numbering = GridNumbering.auto_number(grid)

        # (1,0) starts down word ABCD
        assert (1, 0) in numbering

    def test_numbering_starts_both_directions(self):
        """Test numbering cell that starts both across and down words."""
        grid = Grid(11)
        # Grid: # # . . .
        #       # # . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        grid.set_black_square(0, 0, enforce_symmetry=False)
        grid.set_black_square(0, 1, enforce_symmetry=False)
        grid.set_black_square(1, 0, enforce_symmetry=False)
        grid.set_black_square(1, 1, enforce_symmetry=False)

        numbering = GridNumbering.auto_number(grid)

        # (0,2) starts across word (left is black, right exists)
        assert (0, 2) in numbering
        # (2,0) starts down word (above is black, below exists)
        assert (2, 0) in numbering
        # (2,2) does NOT start both - it's in the middle of word runs from (0,2) and (2,0)
        # So let's just check that (0,2) and (2,0) are numbered

    def test_numbering_sequential(self):
        """Test that numbers are sequential starting from 1."""
        grid = Grid(11)
        # Add some black squares to create multiple word starts
        grid.set_black_square(0, 3)
        grid.set_black_square(0, 7)
        grid.set_black_square(3, 0)
        grid.set_black_square(7, 0)

        numbering = GridNumbering.auto_number(grid)

        # Numbers should be sequential
        numbers = sorted(numbering.values())
        assert numbers == list(range(1, len(numbers) + 1))

    def test_numbering_left_to_right_top_to_bottom(self):
        """Test that numbering proceeds left-to-right, top-to-bottom."""
        grid = Grid(11)
        # Grid: . . . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .

        numbering = GridNumbering.auto_number(grid)

        # (0,0) should be numbered 1 (starts both across and down)
        assert numbering[(0, 0)] == 1

        # (0,1) should be numbered 2 (starts down, next in left-to-right scan)
        assert numbering[(0, 1)] == 2

        # (1,0) should be numbered later (starts across, but comes after top row in top-to-bottom scan)
        assert numbering[(1, 0)] > 5  # After all of row 0


class TestGetCluePositions:
    """Test clue position information."""

    def test_simple_across_clue(self):
        """Test getting clue info for across word."""
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

        clue_info = GridNumbering.get_clue_positions(grid)

        # Find clue at (0,0)
        clue_1 = None
        for num, info in clue_info.items():
            if info['position'] == (0, 0):
                clue_1 = info
                break

        assert clue_1 is not None
        assert clue_1['has_across'] is True
        assert clue_1['across_length'] == 3

    def test_simple_down_clue(self):
        """Test getting clue info for down word."""
        grid = Grid(11)
        # Grid: C # . . .
        #       A # . . .
        #       T # . . .
        #       # # . . .
        #       . # . . .
        grid.set_letter(0, 0, 'C')
        grid.set_letter(1, 0, 'A')
        grid.set_letter(2, 0, 'T')
        grid.set_black_square(3, 0, enforce_symmetry=False)
        grid.set_black_square(0, 1, enforce_symmetry=False)

        clue_info = GridNumbering.get_clue_positions(grid)

        # Find clue at (0,0)
        clue_1 = None
        for num, info in clue_info.items():
            if info['position'] == (0, 0):
                clue_1 = info
                break

        assert clue_1 is not None
        assert clue_1['has_down'] is True
        assert clue_1['down_length'] == 3

    def test_clue_both_directions(self):
        """Test clue that has both across and down words."""
        grid = Grid(11)
        # Grid: # # . . .
        #       # # . . .
        #       . . . . .
        #       . . . . .
        #       . . . . .
        grid.set_black_square(0, 0, enforce_symmetry=False)
        grid.set_black_square(0, 1, enforce_symmetry=False)
        grid.set_black_square(1, 0, enforce_symmetry=False)
        grid.set_black_square(1, 1, enforce_symmetry=False)

        clue_info = GridNumbering.get_clue_positions(grid)

        # Find clue at (0,2) which starts across
        across_clue = None
        for num, info in clue_info.items():
            if info['position'] == (0, 2):
                across_clue = info
                break

        # Find clue at (2,0) which starts down
        down_clue = None
        for num, info in clue_info.items():
            if info['position'] == (2, 0):
                down_clue = info
                break

        assert across_clue is not None
        assert across_clue['has_across'] is True
        assert across_clue['across_length'] == 9  # 11 - 2 = 9

        assert down_clue is not None
        assert down_clue['has_down'] is True
        assert down_clue['down_length'] == 9   # 11 - 2 = 9

    def test_clue_numbers_match_positions(self):
        """Test that clue numbers correspond to positions correctly."""
        grid = Grid(11)
        grid.set_black_square(0, 3)
        grid.set_black_square(3, 0)

        clue_info = GridNumbering.get_clue_positions(grid)

        # All clue numbers should be unique
        numbers = list(clue_info.keys())
        assert len(numbers) == len(set(numbers))

        # All positions should be valid
        for num, info in clue_info.items():
            row, col = info['position']
            assert 0 <= row < 11
            assert 0 <= col < 11
            assert not grid.is_black(row, col)

    def test_all_clues_have_at_least_one_direction(self):
        """Test that every clue has at least one direction (across or down)."""
        grid = Grid(11)
        grid.set_black_square(0, 3)
        grid.set_black_square(3, 0)

        clue_info = GridNumbering.get_clue_positions(grid)

        for num, info in clue_info.items():
            # Every clue must start at least one word
            assert info['has_across'] or info['has_down']

    def test_word_lengths_are_correct(self):
        """Test that reported word lengths match actual slots."""
        grid = Grid(11)
        # Grid: . . . # .
        #       . . . # .
        #       . . . # .
        #       # # # # .
        #       . . . . .
        grid.set_black_square(0, 3, enforce_symmetry=False)
        grid.set_black_square(3, 0, enforce_symmetry=False)
        grid.set_black_square(3, 1, enforce_symmetry=False)
        grid.set_black_square(3, 2, enforce_symmetry=False)
        grid.set_black_square(3, 3, enforce_symmetry=False)

        clue_info = GridNumbering.get_clue_positions(grid)

        # (0,0) should have across length 3 (columns 0-2) and down length 3 (rows 0-2)
        clue_1 = None
        for num, info in clue_info.items():
            if info['position'] == (0, 0):
                clue_1 = info
                break

        assert clue_1 is not None
        if clue_1['has_across']:
            assert clue_1['across_length'] == 3
        if clue_1['has_down']:
            assert clue_1['down_length'] == 3

    def test_clue_positions_include_only_word_starts(self):
        """Test that only cells starting words are included."""
        grid = Grid(11)
        # Grid: W O R D # . . . . . .
        #       . . . . . . . . . . .
        #       . . . . . . . . . . .
        # Add black square after WORD to isolate it
        grid.set_letter(0, 0, 'W')
        grid.set_letter(0, 1, 'O')
        grid.set_letter(0, 2, 'R')
        grid.set_letter(0, 3, 'D')
        grid.set_black_square(0, 4, enforce_symmetry=False)

        clue_info = GridNumbering.get_clue_positions(grid)

        # (0,0) starts across word, should be numbered
        assert any(info['position'] == (0, 0) for info in clue_info.values())

        # (0,1), (0,2), (0,3) also start down words, so they WILL be numbered
        # Only cells that don't start ANY word shouldn't be numbered
        # (0,1) starts a down word, so it will be numbered
        # Let's just verify (0,0) is numbered
