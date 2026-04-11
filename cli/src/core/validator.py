"""
Grid validation functions.

Validates crossword grids against NYT-style construction rules:
- Connectivity (all white squares connected)
- Minimum word length (3 letters)
- Black square percentage (<17%)
- Symmetry (180° rotational)
"""

from typing import List, Tuple

from .grid import Grid


class GridValidator:
    """Validates crossword grid construction rules."""

    @staticmethod
    def validate_all(grid: Grid) -> Tuple[bool, List[str]]:
        """
        Validate grid against all rules.

        Args:
            grid: Grid to validate

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check symmetry
        if not grid.check_symmetry():
            errors.append("Grid lacks 180° rotational symmetry")

        # Check connectivity
        if not GridValidator._check_connectivity(grid):
            errors.append("Grid has isolated white square regions")

        # Check minimum word length
        min_word_errors = GridValidator._check_minimum_word_length(grid)
        errors.extend(min_word_errors)

        # Check black square percentage
        black_pct = GridValidator._get_black_square_percentage(grid)
        if black_pct > 17.0:
            errors.append(f"Black square percentage ({black_pct:.1f}%) exceeds 17% limit")

        return (len(errors) == 0, errors)

    @staticmethod
    def _check_connectivity(grid: Grid) -> bool:
        """
        Check if all white squares are connected.

        Uses flood fill to ensure no isolated regions.

        Returns:
            True if all white squares connected
        """
        # Find first white square
        start = None
        white_count = 0

        for row in range(grid.size):
            for col in range(grid.size):
                if not grid.is_black(row, col):
                    white_count += 1
                    if start is None:
                        start = (row, col)

        if white_count == 0:
            return True  # All black is technically "connected"

        # Flood fill from start position
        visited = set()
        stack = [start]

        while stack:
            row, col = stack.pop()

            if (row, col) in visited:
                continue

            if not (0 <= row < grid.size and 0 <= col < grid.size):
                continue

            if grid.is_black(row, col):
                continue

            visited.add((row, col))

            # Add neighbors
            stack.extend(
                [
                    (row - 1, col),  # up
                    (row + 1, col),  # down
                    (row, col - 1),  # left
                    (row, col + 1),  # right
                ]
            )

        # Check if visited all white squares
        return len(visited) == white_count

    @staticmethod
    def _check_minimum_word_length(grid: Grid) -> List[str]:
        """
        Check that all words are at least 3 letters.

        Returns:
            List of error messages for short words
        """
        errors = []
        slots = grid.get_word_slots()

        for slot in slots:
            if slot["length"] < 3:
                errors.append(
                    f"{slot['direction'].capitalize()} word at "
                    f"({slot['row']}, {slot['col']}) is only {slot['length']} letters"
                )

        return errors

    @staticmethod
    def _get_black_square_percentage(grid: Grid) -> float:
        """
        Calculate percentage of black squares.

        Returns:
            Percentage (0-100)
        """
        black_count = len(grid.get_black_squares())
        total = grid.size * grid.size
        return (black_count / total) * 100.0

    @staticmethod
    def get_grid_stats(grid: Grid) -> dict:
        """
        Get comprehensive grid statistics.

        Returns:
            Dictionary with grid statistics
        """
        word_slots = grid.get_word_slots()
        across_words = [s for s in word_slots if s["direction"] == "across"]
        down_words = [s for s in word_slots if s["direction"] == "down"]

        black_squares = len(grid.get_black_squares())
        total_squares = grid.size * grid.size
        white_squares = total_squares - black_squares

        return {
            "size": grid.size,
            "total_squares": total_squares,
            "black_squares": black_squares,
            "white_squares": white_squares,
            "black_square_percentage": GridValidator._get_black_square_percentage(grid),
            "word_count": len(word_slots),
            "across_word_count": len(across_words),
            "down_word_count": len(down_words),
            "is_symmetric": grid.check_symmetry(),
            "is_connected": GridValidator._check_connectivity(grid),
            "meets_nyt_standards": GridValidator.validate_all(grid)[0],
        }
