"""
Cell type definitions and constants for crossword grids.

This module establishes a clear semantic distinction between:
- Grid state representation (data)
- Pattern matching wildcards (search)

The confusion between '.' and '?' has been a source of bugs.
This module provides the single source of truth.
"""

from typing import Literal, Union

# ============================================================================
# GRID STATE CONSTANTS (Data Representation)
# ============================================================================

# Empty cell in the grid (no letter placed yet)
EMPTY_CELL = '.'

# Black square (word boundary)
BLACK_CELL = '#'

# Valid letter range
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Type definition for grid cells
GridCell = Literal['.', '#', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                   'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                   'W', 'X', 'Y', 'Z']

# ============================================================================
# PATTERN MATCHING CONSTANTS (Search Patterns)
# ============================================================================

# Wildcard in pattern matching (matches any letter)
WILDCARD = '?'

# Pattern character type
PatternChar = Union[Literal['?'], str]  # '?' or any letter A-Z

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def is_empty(cell: str) -> bool:
    """Check if a cell is empty (no letter placed)."""
    return cell == EMPTY_CELL


def is_black(cell: str) -> bool:
    """Check if a cell is a black square."""
    return cell == BLACK_CELL


def is_letter(cell: str) -> bool:
    """Check if a cell contains a letter."""
    return cell in LETTERS


def is_filled(cell: str) -> bool:
    """Check if a cell is filled with a letter (not empty or black)."""
    return is_letter(cell)


def grid_to_pattern(cell: str) -> str:
    """
    Convert a grid cell to a pattern character for matching.

    Rules:
    - Empty cell (.) → Wildcard (?)
    - Letter (A-Z) → Same letter
    - Black square (#) → Should not be in patterns

    Args:
        cell: Grid cell value

    Returns:
        Pattern character for matching
    """
    if is_empty(cell):
        return WILDCARD
    elif is_letter(cell):
        return cell
    elif is_black(cell):
        # Black squares should not be part of patterns
        raise ValueError(f"Black squares should not be in patterns: {cell}")
    else:
        raise ValueError(f"Invalid cell value: {cell}")


def pattern_has_wildcards(pattern: str) -> bool:
    """Check if a pattern contains any wildcards."""
    return WILDCARD in pattern


def pattern_is_complete(pattern: str) -> bool:
    """Check if a pattern is completely filled (no wildcards)."""
    return WILDCARD not in pattern


def validate_grid_cell(cell: str) -> bool:
    """
    Validate that a cell value is valid for a grid.

    Valid values: '.', '#', 'A'-'Z'
    Invalid: '?' (only for patterns, not grid state)
    """
    if cell == WILDCARD:
        return False  # '?' is for patterns, not grid state!
    return is_empty(cell) or is_black(cell) or is_letter(cell)


def validate_pattern_char(char: str) -> bool:
    """
    Validate that a character is valid for a pattern.

    Valid values: '?', 'A'-'Z'
    Invalid: '.', '#' (grid state characters)
    """
    if char == EMPTY_CELL or char == BLACK_CELL:
        return False  # These are grid state, not pattern chars!
    return char == WILDCARD or is_letter(char)


def count_empty_cells(row: list) -> int:
    """Count the number of empty cells in a grid row."""
    return sum(1 for cell in row if is_empty(cell))


def count_filled_cells(row: list) -> int:
    """Count the number of filled cells (letters) in a grid row."""
    return sum(1 for cell in row if is_filled(cell))

# ============================================================================
# ASSERTIONS FOR DEBUGGING
# ============================================================================


def assert_valid_grid(grid: list) -> None:
    """Assert that all cells in a grid are valid."""
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if not validate_grid_cell(cell):
                raise AssertionError(
                    f"Invalid grid cell at ({row_idx}, {col_idx}): '{cell}'. "
                    f"Found '?' in grid - use '{EMPTY_CELL}' for empty cells!"
                )


def assert_valid_pattern(pattern: str) -> None:
    """Assert that all characters in a pattern are valid."""
    for idx, char in enumerate(pattern):
        if not validate_pattern_char(char):
            raise AssertionError(
                f"Invalid pattern character at position {idx}: '{char}'. "
                f"Found '{EMPTY_CELL}' or '{BLACK_CELL}' in pattern - "
                f"use '{WILDCARD}' for wildcards!"
            )
