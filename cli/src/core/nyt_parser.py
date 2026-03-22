"""
Parser for NYT crossword JSON files (doshea/nyt_crosswords format).

Converts NYT JSON format into the internal grid format, extracts word lists
with positions and clues, and self-verifies by reconstructing the grid.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .grid import Grid
from .numbering import GridNumbering


class NytParseError(Exception):
    """Base exception for NYT parsing errors."""
    pass


class NytFormatError(NytParseError):
    """JSON structure is malformed (missing keys, wrong types)."""
    pass


class NytDataError(NytParseError):
    """Data is internally inconsistent."""
    pass


@dataclass
class NytWord:
    """A single extracted word with positional and clue data."""
    number: int
    direction: str  # 'across' or 'down'
    answer: str
    clue: str
    row: int
    col: int
    length: int


@dataclass
class VerificationResult:
    """Result of the self-verification pass."""
    success: bool
    conflicts: List[str]
    grid_match: bool
    words_placed: int
    total_words: int
    mismatched_cells: List[Tuple[int, int, str, str]]  # (row, col, expected, got)


@dataclass
class NytParseResult:
    """Complete result of parsing an NYT crossword JSON file."""
    size: int
    empty_grid: Grid
    filled_grid: Grid
    words: List[NytWord]
    numbering: Dict[Tuple[int, int], int]
    verification: Optional[VerificationResult] = None
    metadata: Dict = field(default_factory=dict)


def load_nyt_file(file_path: str) -> dict:
    """Load and validate an NYT crossword JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Validated dictionary of NYT data.

    Raises:
        NytFormatError: If JSON is malformed or missing required keys.
        NytDataError: If data is internally inconsistent.
    """
    path = Path(file_path)
    if not path.exists():
        raise NytParseError(f"File not found: {file_path}")

    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise NytFormatError(f"Invalid JSON: {e}")

    # Validate required keys
    required_keys = ['size', 'grid', 'gridnums', 'clues', 'answers']
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise NytFormatError(f"Missing required keys: {missing}")

    # Validate size
    size_data = data['size']
    if not isinstance(size_data, dict) or 'rows' not in size_data or 'cols' not in size_data:
        raise NytFormatError("'size' must be dict with 'rows' and 'cols'")

    rows, cols = size_data['rows'], size_data['cols']
    if rows != cols:
        raise NytFormatError(f"Non-square grids not supported: {rows}x{cols}")

    # Validate grid length
    expected_len = rows * cols
    if not isinstance(data['grid'], list) or len(data['grid']) != expected_len:
        actual = len(data['grid']) if isinstance(data['grid'], list) else 0
        raise NytDataError(f"Grid length {actual} != expected {expected_len} ({rows}x{cols})")

    if not isinstance(data['gridnums'], list) or len(data['gridnums']) != expected_len:
        raise NytDataError("gridnums length doesn't match grid")

    # Validate clues/answers structure
    for section in ['clues', 'answers']:
        if not isinstance(data[section], dict):
            raise NytFormatError(f"'{section}' must be a dict")
        for direction in ['across', 'down']:
            if direction not in data[section]:
                raise NytFormatError(f"'{section}' missing '{direction}'")
            if not isinstance(data[section][direction], list):
                raise NytFormatError(f"'{section}.{direction}' must be a list")

    # Validate clue/answer count match
    for direction in ['across', 'down']:
        n_clues = len(data['clues'][direction])
        n_answers = len(data['answers'][direction])
        if n_clues != n_answers:
            raise NytDataError(
                f"{direction}: {n_clues} clues but {n_answers} answers"
            )

    return data


def nyt_grid_to_internal(nyt_data: dict) -> Tuple[Grid, Grid]:
    """Convert NYT flat grid to internal Grid objects.

    Args:
        nyt_data: Validated NYT data dict.

    Returns:
        Tuple of (empty_grid, filled_grid).
        empty_grid has black squares only; filled_grid has all letters.
    """
    size = nyt_data['size']['rows']
    flat_grid = nyt_data['grid']

    # Build 2D arrays for both grids
    empty_2d = []
    filled_2d = []
    has_rebus = False

    for row in range(size):
        empty_row = []
        filled_row = []
        for col in range(size):
            cell = flat_grid[row * size + col]

            if cell == '.':
                # NYT "." = black square -> internal "#"
                empty_row.append('#')
                filled_row.append('#')
            elif isinstance(cell, str) and len(cell) == 1 and cell.isalpha():
                empty_row.append('.')  # Empty in the empty grid
                filled_row.append(cell.upper())
            elif isinstance(cell, str) and len(cell) > 1:
                # Rebus cell - take first letter with warning
                has_rebus = True
                empty_row.append('.')
                filled_row.append(cell[0].upper() if cell[0].isalpha() else '.')
            else:
                # Unknown cell type
                empty_row.append('.')
                filled_row.append('.')

        empty_2d.append(empty_row)
        filled_2d.append(filled_row)

    empty_grid = Grid.from_dict({'size': size, 'grid': empty_2d}, strict_size=False)
    filled_grid = Grid.from_dict({'size': size, 'grid': filled_2d}, strict_size=False)

    return empty_grid, filled_grid, has_rebus


def parse_clue_string(clue_str: str) -> Tuple[int, str]:
    """Parse a clue string like '1. Defrost' into (number, text).

    Handles formats: '1. text', '1) text', '1 text'
    """
    match = re.match(r'^(\d+)[.)\s]\s*(.*)', clue_str)
    if match:
        return int(match.group(1)), match.group(2).strip()

    # Fallback: try to find leading number
    match = re.match(r'^(\d+)(.*)', clue_str)
    if match:
        return int(match.group(1)), match.group(2).strip()

    raise NytDataError(f"Cannot parse clue string: '{clue_str}'")


def _compute_word_length(grid: Grid, row: int, col: int, direction: str) -> int:
    """Walk the grid from (row, col) in direction until black square or edge."""
    length = 0
    r, c = row, col
    while r < grid.size and c < grid.size and not grid.is_black(r, c):
        length += 1
        if direction == 'across':
            c += 1
        else:
            r += 1
    return length


def extract_words(
    nyt_data: dict,
    numbering: Dict[Tuple[int, int], int],
    grid: Grid,
) -> List[NytWord]:
    """Extract all words with positions from NYT data.

    Args:
        nyt_data: Validated NYT data dict.
        numbering: Dict mapping (row, col) -> clue number.
        grid: The empty grid (for walking word lengths).

    Returns:
        List of NytWord objects.
    """
    # Build reverse lookup: number -> (row, col)
    num_to_pos = {v: k for k, v in numbering.items()}

    # Determine which numbers start across/down words
    clue_positions = GridNumbering.get_clue_positions(grid)

    words = []

    for direction in ['across', 'down']:
        clues = nyt_data['clues'][direction]
        answers = nyt_data['answers'][direction]

        for i, (clue_str, answer) in enumerate(zip(clues, answers)):
            try:
                number, clue_text = parse_clue_string(clue_str)
            except NytDataError:
                # Skip unparseable clues
                continue

            if number not in num_to_pos:
                continue

            row, col = num_to_pos[number]
            length = _compute_word_length(grid, row, col, direction)

            words.append(NytWord(
                number=number,
                direction=direction,
                answer=answer.upper(),
                clue=clue_text,
                row=row,
                col=col,
                length=length,
            ))

    return words


def verify_extraction(
    nyt_data: dict,
    empty_grid: Grid,
    words: List[NytWord],
    size: int,
) -> VerificationResult:
    """Verify extraction by placing words one-by-one and checking for conflicts.

    Phase A: Place each word letter by letter, checking crossing consistency.
    Phase B: Compare reconstructed grid against original NYT grid.
    """
    # Clone the empty grid to reconstruct
    # Use from_dict for non-standard sizes since clone() validates size
    recon = Grid.from_dict(empty_grid.to_dict(), strict_size=False)

    conflicts = []
    words_placed = 0
    total_words = len(words)

    # Sort: by number, across before down
    sorted_words = sorted(words, key=lambda w: (w.number, 0 if w.direction == 'across' else 1))

    # Phase A: Place words, check crossing consistency
    for word in sorted_words:
        word_ok = True
        for i, letter in enumerate(word.answer):
            if word.direction == 'across':
                r, c = word.row, word.col + i
            else:
                r, c = word.row + i, word.col

            # Bounds check
            if r >= size or c >= size:
                conflicts.append(
                    f"{word.number}-{word.direction} '{word.answer}' extends beyond grid at ({r},{c})"
                )
                word_ok = False
                break

            existing = recon.get_cell(r, c)
            if existing == '#':
                conflicts.append(
                    f"{word.number}-{word.direction} '{word.answer}' hits black square at ({r},{c})"
                )
                word_ok = False
                break
            elif existing != '.' and existing != letter:
                conflicts.append(
                    f"Conflict at ({r},{c}): {word.number}-{word.direction} "
                    f"wants '{letter}' but '{existing}' already placed"
                )
                word_ok = False
            else:
                recon.set_letter(r, c, letter)

        if word_ok:
            words_placed += 1

    # Phase B: Compare against original NYT grid
    flat_grid = nyt_data['grid']
    mismatched = []

    for idx, nyt_cell in enumerate(flat_grid):
        if nyt_cell == '.':
            continue  # Black square, skip
        row, col = divmod(idx, size)
        recon_cell = recon.get_cell(row, col)

        expected = nyt_cell.upper() if isinstance(nyt_cell, str) else str(nyt_cell)
        # Handle rebus: only compare first letter
        if len(expected) > 1:
            expected = expected[0]

        if recon_cell == '.':
            mismatched.append((row, col, expected, '(empty)'))
        elif recon_cell != expected:
            mismatched.append((row, col, expected, recon_cell))

    grid_match = len(mismatched) == 0
    success = len(conflicts) == 0 and grid_match

    return VerificationResult(
        success=success,
        conflicts=conflicts,
        grid_match=grid_match,
        words_placed=words_placed,
        total_words=total_words,
        mismatched_cells=mismatched,
    )


def _crosscheck_numbering(
    nyt_data: dict,
    computed_numbering: Dict[Tuple[int, int], int],
    size: int,
) -> List[str]:
    """Cross-check computed numbering against NYT gridnums. Returns warnings."""
    warnings = []
    gridnums = nyt_data['gridnums']

    for idx, nyt_num in enumerate(gridnums):
        if nyt_num == 0:
            continue
        row, col = divmod(idx, size)
        computed = computed_numbering.get((row, col))
        if computed is None:
            warnings.append(f"NYT has number {nyt_num} at ({row},{col}) but auto_number doesn't")
        elif computed != nyt_num:
            warnings.append(
                f"Number mismatch at ({row},{col}): NYT={nyt_num}, computed={computed}"
            )

    return warnings


def parse_nyt_json(file_path: str, verify: bool = True) -> NytParseResult:
    """Parse an NYT crossword JSON file into internal format.

    Args:
        file_path: Path to the NYT JSON file.
        verify: Whether to run self-verification.

    Returns:
        NytParseResult with grid, words, and optional verification.

    Raises:
        NytParseError: If file is corrupted or malformed.
    """
    # Load and validate
    nyt_data = load_nyt_file(file_path)
    size = nyt_data['size']['rows']

    # Convert grids
    empty_grid, filled_grid, has_rebus = nyt_grid_to_internal(nyt_data)

    # Compute numbering
    numbering = GridNumbering.auto_number(empty_grid)

    # Cross-check numbering
    numbering_warnings = _crosscheck_numbering(nyt_data, numbering, size)

    # Extract words
    words = extract_words(nyt_data, numbering, empty_grid)

    # Build metadata
    metadata = {
        'title': nyt_data.get('title', ''),
        'author': nyt_data.get('author', ''),
        'editor': nyt_data.get('editor', ''),
        'date': nyt_data.get('date', ''),
        'dow': nyt_data.get('dow', ''),
        'has_rebus': has_rebus,
        'numbering_warnings': numbering_warnings,
    }

    # Verify
    verification = None
    if verify:
        verification = verify_extraction(nyt_data, empty_grid, words, size)

    return NytParseResult(
        size=size,
        empty_grid=empty_grid,
        filled_grid=filled_grid,
        words=words,
        numbering=numbering,
        verification=verification,
        metadata=metadata,
    )
