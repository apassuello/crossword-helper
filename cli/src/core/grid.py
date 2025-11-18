"""
Grid data structure for crossword puzzles.

Uses NumPy for efficient grid operations and enforces standard crossword rules:
- 180° rotational symmetry
- Minimum 3-letter words
- All white squares must be connected
- Standard sizes: 11×11, 15×15, 21×21
"""

import numpy as np
from typing import Dict, Set, Tuple, List, Optional


# Cell encoding constants
BLACK_SQUARE = -1
EMPTY_CELL = 0


class Grid:
    """Crossword grid with NumPy backing and constraint enforcement."""

    def __init__(self, size: int):
        """
        Initialize empty grid.

        Args:
            size: Grid dimension (11, 15, or 21)

        Raises:
            ValueError: If size is not valid
        """
        if size not in [11, 15, 21]:
            raise ValueError(f"Grid size must be 11, 15, or 21, got {size}")

        self.size = size
        # Initialize with all empty cells
        self.cells = np.zeros((size, size), dtype=np.int8)
        self._numbering: Optional[Dict[Tuple[int, int], int]] = None

    def set_black_square(self, row: int, col: int, enforce_symmetry: bool = True):
        """
        Set a black square at position.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)
            enforce_symmetry: If True, also set symmetric position

        Raises:
            ValueError: If position is out of bounds
        """
        self._validate_position(row, col)

        self.cells[row, col] = BLACK_SQUARE

        if enforce_symmetry:
            # 180° rotation: (row, col) → (size-1-row, size-1-col)
            sym_row = self.size - 1 - row
            sym_col = self.size - 1 - col
            self.cells[sym_row, sym_col] = BLACK_SQUARE

        # Invalidate cached numbering
        self._numbering = None

    def set_letter(self, row: int, col: int, letter: str):
        """
        Set a letter at position.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)
            letter: Single letter A-Z

        Raises:
            ValueError: If position is out of bounds or letter invalid
        """
        self._validate_position(row, col)

        if len(letter) != 1 or not letter.isalpha():
            raise ValueError(f"Letter must be single character A-Z, got '{letter}'")

        # Encode: A=1, B=2, ..., Z=26
        self.cells[row, col] = ord(letter.upper()) - ord('A') + 1

        # Invalidate cached numbering
        self._numbering = None

    def get_cell(self, row: int, col: int) -> str:
        """
        Get cell contents as string.

        Args:
            row: Row index
            col: Column index

        Returns:
            '#' for black square
            '.' for empty cell
            'A'-'Z' for letters
        """
        self._validate_position(row, col)

        value = self.cells[row, col]

        if value == BLACK_SQUARE:
            return '#'
        elif value == EMPTY_CELL:
            return '.'
        else:
            # Decode: 1=A, 2=B, ..., 26=Z
            return chr(value - 1 + ord('A'))

    def is_black(self, row: int, col: int) -> bool:
        """Check if position is a black square."""
        return self.cells[row, col] == BLACK_SQUARE

    def is_empty(self, row: int, col: int) -> bool:
        """Check if position is empty."""
        return self.cells[row, col] == EMPTY_CELL

    def has_letter(self, row: int, col: int) -> bool:
        """Check if position has a letter."""
        return self.cells[row, col] > 0

    def get_black_squares(self) -> Set[Tuple[int, int]]:
        """Get all black square positions."""
        black_positions = set()
        for row in range(self.size):
            for col in range(self.size):
                if self.is_black(row, col):
                    black_positions.add((row, col))
        return black_positions

    def check_symmetry(self) -> bool:
        """
        Check if grid has 180° rotational symmetry.

        Returns:
            True if symmetric, False otherwise
        """
        for row in range(self.size):
            for col in range(self.size):
                sym_row = self.size - 1 - row
                sym_col = self.size - 1 - col

                # Check if black squares match
                if self.is_black(row, col) != self.is_black(sym_row, sym_col):
                    return False

        return True

    def get_word_slots(self) -> List[Dict]:
        """
        Get all across and down word slots.

        Returns:
            List of word slot dictionaries with keys:
            - direction: 'across' or 'down'
            - row: Starting row
            - col: Starting column
            - length: Word length
            - pattern: Current pattern (e.g., 'C?T')
        """
        slots = []

        # Find across words
        for row in range(self.size):
            col = 0
            while col < self.size:
                if not self.is_black(row, col):
                    # Found start of potential word
                    start_col = col
                    length = 0
                    pattern = []

                    while col < self.size and not self.is_black(row, col):
                        pattern.append(self.get_cell(row, col))
                        length += 1
                        col += 1

                    # Only add if length >= 3
                    if length >= 3:
                        slots.append({
                            'direction': 'across',
                            'row': row,
                            'col': start_col,
                            'length': length,
                            'pattern': ''.join(pattern)
                        })
                else:
                    col += 1

        # Find down words
        for col in range(self.size):
            row = 0
            while row < self.size:
                if not self.is_black(row, col):
                    # Found start of potential word
                    start_row = row
                    length = 0
                    pattern = []

                    while row < self.size and not self.is_black(row, col):
                        pattern.append(self.get_cell(row, col))
                        length += 1
                        row += 1

                    # Only add if length >= 3
                    if length >= 3:
                        slots.append({
                            'direction': 'down',
                            'row': start_row,
                            'col': col,
                            'length': length,
                            'pattern': ''.join(pattern)
                        })
                else:
                    row += 1

        return slots

    def to_dict(self) -> Dict:
        """
        Export grid to dictionary format.

        Returns:
            Dictionary with grid data
        """
        grid_2d = []
        for row in range(self.size):
            row_data = []
            for col in range(self.size):
                row_data.append(self.get_cell(row, col))
            grid_2d.append(row_data)

        return {
            'size': self.size,
            'grid': grid_2d,
            'black_squares': len(self.get_black_squares()),
            'is_symmetric': self.check_symmetry()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Grid':
        """
        Create grid from dictionary format.

        Args:
            data: Dictionary with 'size' and 'grid' keys

        Returns:
            Grid instance
        """
        size = data['size']
        grid = cls(size)

        grid_data = data['grid']
        for row in range(size):
            for col in range(size):
                cell = grid_data[row][col]
                if cell == '#':
                    grid.cells[row, col] = BLACK_SQUARE
                elif cell == '.':
                    grid.cells[row, col] = EMPTY_CELL
                elif cell.isalpha():
                    grid.cells[row, col] = ord(cell.upper()) - ord('A') + 1

        return grid

    def _validate_position(self, row: int, col: int):
        """Validate that position is within grid bounds."""
        if not (0 <= row < self.size and 0 <= col < self.size):
            raise ValueError(
                f"Position ({row}, {col}) out of bounds for {self.size}×{self.size} grid"
            )

    def __str__(self) -> str:
        """String representation of grid."""
        lines = []
        for row in range(self.size):
            line = []
            for col in range(self.size):
                line.append(self.get_cell(row, col))
            lines.append(' '.join(line))
        return '\n'.join(lines)
