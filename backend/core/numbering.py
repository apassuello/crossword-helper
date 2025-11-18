"""
Crossword grid numbering validation and generation.

This module validates and generates numbering schemes for crossword grids,
ensuring that clue numbers are assigned correctly according to standard
crossword conventions.
"""

from typing import Dict, Tuple, List


class NumberingValidator:
    """Validates and generates crossword grid numbering."""

    def auto_number(self, grid: List[List[str]]) -> Dict[Tuple[int, int], int]:
        """
        Automatically number grid using standard crossword rules.

        Rules:
        1. Scan grid left-to-right, top-to-bottom
        2. For each white cell:
           a. Check if starts ACROSS word:
              - Cell to left is black OR at left edge
              - AND cell to right exists and is not black
           b. Check if starts DOWN word:
              - Cell above is black OR at top edge
              - AND cell below exists and is not black
           c. If starts across OR down: assign next number
        3. Numbers increment sequentially (1, 2, 3, ...)
        4. Each cell gets at most one number

        Args:
            grid: 2D array of grid cells (A-Z, #, .)

        Returns:
            Dict mapping (row, col) to number
        """
        numbering = {}
        current_number = 1
        rows, cols = len(grid), len(grid[0]) if grid else 0

        for row in range(rows):
            for col in range(cols):
                if grid[row][col] == '#':
                    continue

                starts_across = (
                    (col == 0 or grid[row][col-1] == '#') and
                    (col < cols-1 and grid[row][col+1] != '#')
                )

                starts_down = (
                    (row == 0 or grid[row-1][col] == '#') and
                    (row < rows-1 and grid[row+1][col] != '#')
                )

                if starts_across or starts_down:
                    numbering[(row, col)] = current_number
                    current_number += 1

        return numbering

    def validate(
        self,
        grid: List[List[str]],
        user_numbering: Dict[Tuple[int, int], int]
    ) -> Tuple[bool, List[dict]]:
        """
        Validate user's numbering against standard rules.

        Args:
            grid: 2D array of grid cells
            user_numbering: User's numbering to validate

        Returns:
            (is_valid, list_of_errors)

        Error dict format:
            {
                'type': 'MISSING_NUMBER' | 'WRONG_NUMBER' | 'EXTRA_NUMBER',
                'position': (row, col),
                'expected': number or None,
                'actual': number or None,
                'message': human-readable explanation
            }
        """
        errors = []
        correct_numbering = self.auto_number(grid)

        # Convert tuple keys to strings for comparison
        user_positions = set(user_numbering.keys())
        correct_positions = set(correct_numbering.keys())

        # Check for missing numbers
        for pos in correct_positions - user_positions:
            errors.append({
                'type': 'MISSING_NUMBER',
                'position': pos,
                'expected': correct_numbering[pos],
                'actual': None,
                'message': f'Missing number {correct_numbering[pos]} at {pos}'
            })

        # Check for extra numbers
        for pos in user_positions - correct_positions:
            errors.append({
                'type': 'EXTRA_NUMBER',
                'position': pos,
                'expected': None,
                'actual': user_numbering[pos],
                'message': f'Unexpected number {user_numbering[pos]} at {pos}'
            })

        # Check for wrong numbers
        for pos in user_positions & correct_positions:
            if user_numbering[pos] != correct_numbering[pos]:
                errors.append({
                    'type': 'WRONG_NUMBER',
                    'position': pos,
                    'expected': correct_numbering[pos],
                    'actual': user_numbering[pos],
                    'message': f'Wrong number at {pos}: expected {correct_numbering[pos]}, got {user_numbering[pos]}'
                })

        is_valid = len(errors) == 0
        return is_valid, errors

    def analyze_grid(self, grid: List[List[str]]) -> dict:
        """
        Analyze grid characteristics.

        NYT Standards (for 15×15):
        - Black squares: <16% (~36 squares)
        - Word count: <78 (themed), <72 (themeless)

        Returns:
            {
                'size': [rows, cols],
                'black_squares': count,
                'white_squares': count,
                'word_count': count,
                'black_square_percentage': percentage,
                'meets_nyt_standards': bool
            }
        """
        rows, cols = len(grid), len(grid[0]) if grid else 0
        total_squares = rows * cols

        black_count = sum(
            1 for row in grid for cell in row if cell == '#'
        )
        white_count = total_squares - black_count

        # Count words (simplified: number cells * 2 for rough estimate)
        numbering = self.auto_number(grid)
        word_count = len(numbering) * 2  # Rough estimate (each number usually has across + down)

        black_percentage = (black_count / total_squares) * 100 if total_squares > 0 else 0

        # NYT standards check
        max_black_percentage = 16
        max_words = 78 if rows == 15 else 140  # 15×15 or 21×21

        meets_standards = (
            black_percentage <= max_black_percentage and
            word_count <= max_words
        )

        return {
            'size': [rows, cols],
            'black_squares': black_count,
            'white_squares': white_count,
            'word_count': word_count,
            'black_square_percentage': round(black_percentage, 1),
            'meets_nyt_standards': meets_standards
        }

    def _validate_grid(self, grid: List[List[str]]) -> None:
        """
        Validate grid format.

        Rules:
        - Must be square (n×n)
        - Size must be 11×11, 15×15, or 21×21
        - Cells must be A-Z, #, or .

        Raises:
            ValueError: With specific message
        """
        if not grid:
            raise ValueError("Grid cannot be empty")

        rows = len(grid)
        cols = len(grid[0]) if grid else 0

        if rows != cols:
            raise ValueError(f"Grid must be square, got {rows}×{cols}")

        if rows not in [11, 15, 21]:
            raise ValueError(f"Grid size must be 11×11, 15×15, or 21×21, got {rows}×{rows}")

        for row_idx, row in enumerate(grid):
            for col_idx, cell in enumerate(row):
                if not (cell == '#' or cell == '.' or (len(cell) == 1 and cell.isalpha())):
                    raise ValueError(
                        f"Invalid cell value '{cell}' at ({row_idx}, {col_idx}). "
                        f"Must be A-Z, #, or ."
                    )
