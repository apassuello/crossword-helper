"""
Auto-numbering for crossword grids.

Implements standard crossword numbering algorithm:
- Scan left-to-right, top-to-bottom
- Number cells that start across or down words
- Numbers increment sequentially
"""

from typing import Dict, Tuple
from .grid import Grid


class GridNumbering:
    """Handles automatic grid numbering."""

    @staticmethod
    def auto_number(grid: Grid) -> Dict[Tuple[int, int], int]:
        """
        Auto-number grid using standard crossword rules.

        Rules:
        1. Scan grid left-to-right, top-to-bottom
        2. For each white cell:
           - Check if starts ACROSS word (left is black/edge AND right exists and is white)
           - Check if starts DOWN word (above is black/edge AND below exists and is white)
           - If starts across OR down: assign next number
        3. Numbers increment sequentially (1, 2, 3, ...)

        Args:
            grid: Grid to number

        Returns:
            Dictionary mapping (row, col) to number
        """
        numbering = {}
        current_number = 1

        for row in range(grid.size):
            for col in range(grid.size):
                # Skip black squares
                if grid.is_black(row, col):
                    continue

                # Check if starts across word
                starts_across = (
                    (col == 0 or grid.is_black(row, col - 1)) and
                    (col < grid.size - 1 and not grid.is_black(row, col + 1))
                )

                # Check if starts down word
                starts_down = (
                    (row == 0 or grid.is_black(row - 1, col)) and
                    (row < grid.size - 1 and not grid.is_black(row + 1, col))
                )

                # Assign number if starts any word
                if starts_across or starts_down:
                    numbering[(row, col)] = current_number
                    current_number += 1

        return numbering

    @staticmethod
    def get_clue_positions(grid: Grid) -> Dict[int, Dict]:
        """
        Get clue positions with across/down information.

        Returns:
            Dictionary mapping clue number to:
            {
                'position': (row, col),
                'has_across': bool,
                'has_down': bool,
                'across_length': int or None,
                'down_length': int or None
            }
        """
        numbering = GridNumbering.auto_number(grid)
        word_slots = grid.get_word_slots()

        # Build position to slot mapping
        clue_info = {}

        for pos, num in numbering.items():
            row, col = pos
            info = {
                'position': pos,
                'has_across': False,
                'has_down': False,
                'across_length': None,
                'down_length': None
            }

            # Find matching slots
            for slot in word_slots:
                if slot['row'] == row and slot['col'] == col:
                    if slot['direction'] == 'across':
                        info['has_across'] = True
                        info['across_length'] = slot['length']
                    elif slot['direction'] == 'down':
                        info['has_down'] = True
                        info['down_length'] = slot['length']

            clue_info[num] = info

        return clue_info
