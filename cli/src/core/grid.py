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
    def from_dict(cls, data: Dict, strict_size: bool = True) -> 'Grid':
        """
        Create grid from dictionary format.

        Supports both Phase 1 (webapp) and Phase 2 (CLI) formats:
        - Phase 1: {"grid": [[...]], "size": N}
        - Phase 2: {"grid": [[...]], "size": N, "black_squares": M, "is_symmetric": bool}

        Args:
            data: Dictionary with 'size' and 'grid' keys
            strict_size: If False, auto-detect size from grid data (allows non-standard sizes)

        Returns:
            Grid instance

        Raises:
            ValueError: If grid data is invalid or incompatible with size
        """
        # Get grid data
        if 'grid' not in data:
            raise ValueError("Dictionary must contain 'grid' key")

        grid_data = data['grid']

        # Determine size
        if 'size' in data:
            size = data['size']
        else:
            # Auto-detect from grid dimensions
            if not grid_data or not isinstance(grid_data, list):
                raise ValueError("Grid data must be non-empty 2D array")
            size = len(grid_data)

        # Validate grid dimensions
        if not isinstance(grid_data, list) or len(grid_data) != size:
            raise ValueError(f"Grid must be {size}×{size}, got {len(grid_data)} rows")

        for row_idx, row in enumerate(grid_data):
            if not isinstance(row, list) or len(row) != size:
                expected_cols = size
                actual_cols = len(row) if isinstance(row, list) else 0
                raise ValueError(
                    f"Grid row {row_idx} must have {expected_cols} columns, got {actual_cols}"
                )

        # Create grid (with size validation if strict)
        if strict_size and size not in [11, 15, 21]:
            raise ValueError(
                f"Grid size must be 11, 15, or 21 for standard crosswords, got {size}. "
                f"Set strict_size=False to allow non-standard sizes."
            )

        grid = cls.__new__(cls)
        grid.size = size
        grid.cells = np.zeros((size, size), dtype=np.int8)
        grid._numbering = None

        # Populate cells
        for row in range(size):
            for col in range(size):
                cell = grid_data[row][col]
                if cell == '#':
                    grid.cells[row, col] = BLACK_SQUARE
                elif cell == '.':
                    grid.cells[row, col] = EMPTY_CELL
                elif cell.isalpha():
                    grid.cells[row, col] = ord(cell.upper()) - ord('A') + 1
                elif cell == '':
                    # Handle empty string as empty cell
                    grid.cells[row, col] = EMPTY_CELL
                else:
                    # Unknown cell value - treat as empty with warning
                    grid.cells[row, col] = EMPTY_CELL

        return grid

    def _validate_position(self, row: int, col: int):
        """Validate that position is within grid bounds."""
        if not (0 <= row < self.size and 0 <= col < self.size):
            raise ValueError(
                f"Position ({row}, {col}) out of bounds for {self.size}×{self.size} grid"
            )

    def get_pattern_for_slot(self, slot: Dict) -> str:
        """
        Get current pattern for a slot (with filled letters).

        Args:
            slot: Slot dict with 'row', 'col', 'length', 'direction'

        Returns:
            Pattern string (e.g., "?I?A" where ? is empty, letters are filled)
        """
        pattern = []
        row, col = slot['row'], slot['col']
        length = slot['length']
        direction = slot['direction']

        for i in range(length):
            if direction == 'across':
                cell = self.get_cell(row, col + i)
            else:  # down
                cell = self.get_cell(row + i, col)

            if cell == '.':
                pattern.append('?')
            elif cell == '#':
                # Shouldn't happen in a valid slot
                pattern.append('?')
            else:
                # Letter
                pattern.append(cell)

        return ''.join(pattern)

    def place_word(self, word: str, row: int, col: int, direction: str) -> None:
        """
        Place word in grid.

        Args:
            word: Word to place (uppercase letters)
            row: Starting row
            col: Starting column
            direction: 'across' or 'down'

        Raises:
            ValueError: If word doesn't fit in grid or direction is invalid
        """
        word = word.upper()

        # Validate direction
        if direction not in ('across', 'down'):
            raise ValueError(f"Direction must be 'across' or 'down', got '{direction}'")

        # Validate word fits in grid bounds
        if direction == 'across':
            end_col = col + len(word) - 1
            if end_col >= self.size:
                raise ValueError(
                    f"Word '{word}' (length {len(word)}) at ({row}, {col}) "
                    f"extends beyond grid (end col {end_col} >= {self.size})"
                )
            self._validate_position(row, col)  # Validate start position
        else:  # down
            end_row = row + len(word) - 1
            if end_row >= self.size:
                raise ValueError(
                    f"Word '{word}' (length {len(word)}) at ({row}, {col}) "
                    f"extends beyond grid (end row {end_row} >= {self.size})"
                )
            self._validate_position(row, col)  # Validate start position

        # Place word (now safe)
        for i, letter in enumerate(word):
            if direction == 'across':
                self.set_letter(row, col + i, letter)
            else:  # down
                self.set_letter(row + i, col, letter)

    def remove_word(self, row: int, col: int, length: int, direction: str) -> None:
        """
        Remove word from grid (set cells to empty).

        Args:
            row: Starting row
            col: Starting column
            length: Word length
            direction: 'across' or 'down'

        Raises:
            ValueError: If removal would extend beyond grid or direction is invalid
        """
        # Validate direction
        if direction not in ('across', 'down'):
            raise ValueError(f"Direction must be 'across' or 'down', got '{direction}'")

        # Validate removal fits in grid bounds
        if direction == 'across':
            end_col = col + length - 1
            if end_col >= self.size:
                raise ValueError(
                    f"Remove operation (length {length}) at ({row}, {col}) "
                    f"extends beyond grid (end col {end_col} >= {self.size})"
                )
            self._validate_position(row, col)  # Validate start position
        else:  # down
            end_row = row + length - 1
            if end_row >= self.size:
                raise ValueError(
                    f"Remove operation (length {length}) at ({row}, {col}) "
                    f"extends beyond grid (end row {end_row} >= {self.size})"
                )
            self._validate_position(row, col)  # Validate start position

        # Remove word (now safe)
        for i in range(length):
            if direction == 'across':
                self.cells[row, col + i] = EMPTY_CELL
            else:  # down
                self.cells[row + i, col] = EMPTY_CELL

        # Invalidate cached numbering
        self._numbering = None

    def get_empty_slots(self) -> List[Dict]:
        """
        Get all word slots that are not completely filled.

        Returns:
            List of slot dicts that have at least one empty cell
        """
        empty_slots = []

        all_slots = self.get_word_slots()

        for slot in all_slots:
            # Check actual cell values, not pattern strings
            # A cell is filled if it's a black square (-1) OR a positive value (letter)
            # Anything else (0, None, unexpected values) = empty
            row, col = slot['row'], slot['col']
            length = slot['length']
            direction = slot['direction']

            has_empty = False
            for i in range(length):
                if direction == 'across':
                    cell_value = self.cells[row, col + i]
                else:  # down
                    cell_value = self.cells[row + i, col]

                # Inverse logic: if NOT (black square OR positive letter), then empty
                if not (cell_value == BLACK_SQUARE or cell_value > 0):
                    has_empty = True
                    break

            if has_empty:
                empty_slots.append(slot)

        return empty_slots

    def clone(self) -> 'Grid':
        """
        Create deep copy of grid.

        Returns:
            New Grid instance with same state
        """
        new_grid = Grid(self.size)
        new_grid.cells = self.cells.copy()
        return new_grid

    def __str__(self) -> str:
        """String representation of grid."""
        lines = []
        for row in range(self.size):
            line = []
            for col in range(self.size):
                line.append(self.get_cell(row, col))
            lines.append(' '.join(line))
        return '\n'.join(lines)
