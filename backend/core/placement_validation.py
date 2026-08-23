"""
Grid placement conflict validation.

Single implementation of the applier's conflict check — cell/intersection
conflicts and 180-degree rotational-symmetry boundary-black conflicts — shared
by the apply-placement route (backend/api/theme_routes.py) and ThemePlacer's
candidate filtering (backend/core/theme_placer.py). Neither of those modules
duplicates this logic; both call in here instead (issue #15).

Deliberately does not import from theme_routes.py or theme_placer.py, so both
of them can import this module without creating an import cycle.

Read-only: nothing here mutates the grid it is checking. Turning boundary
cells into actual black squares is the apply step's job, not this module's —
see `_set_black` in theme_routes.py.
"""

from typing import Dict, List, Tuple

Cell = Tuple[int, int]


def _cell_state(grid: List[List], r: int, c: int) -> Tuple[str, str]:
    """Return ('black'|'letter'|'empty', letter) for a cell. Read-only."""
    cell = grid[r][c]
    if isinstance(cell, dict):
        if cell.get("isBlack", False):
            return "black", None
        letter_value = (cell.get("letter") or "").strip()
        if letter_value and letter_value != ".":
            return "letter", letter_value.upper()
        return "empty", None
    if cell == "#":
        return "black", None
    if not cell or cell in (".", ""):
        return "empty", None
    return "letter", str(cell).strip().upper()


def check_placement(grid: List[List], placement: Dict) -> Tuple[List[str], List[Cell], List[Cell]]:
    """
    Check a placement against a grid for conflicts.

    Returns (conflicts, boundary_blacks, twin_blacks):
      - conflicts: human-readable messages; [] means the placement is valid.
      - boundary_blacks: currently-empty cells immediately before/after the
        word that would need to become black squares.
      - twin_blacks: those boundary squares' 180-degree rotational twins that
        would also need to become black squares (excluding twins that are
        themselves boundary squares, or already black).

    boundary_blacks/twin_blacks are only meaningful when conflicts is empty —
    a rejected placement's blacks are not a valid grid edit.

    Read-only — does not mutate grid.
    """
    word = placement["word"].upper()
    row = placement["row"]
    col = placement["col"]
    direction = placement["direction"]
    grid_size = len(grid)

    conflicts: List[str] = []

    for i, letter in enumerate(word):
        if direction == "across":
            target_row = row
            target_col = col + i
            if target_col >= len(grid[row]):
                conflicts.append(f"Position ({target_row}, {target_col}) out of bounds")
                continue
        else:  # down
            target_row = row + i
            target_col = col
            if target_row >= len(grid):
                conflicts.append(f"Position ({target_row}, {target_col}) out of bounds")
                continue

        cell = grid[target_row][target_col]

        # Extract existing letter from cell (handle both dict and string formats)
        existing_letter = None
        is_black = False

        if isinstance(cell, dict):
            letter_value = cell.get("letter", "").strip()
            if letter_value and letter_value != ".":
                existing_letter = letter_value.upper()
            else:
                existing_letter = None  # Empty cell
            is_black = cell.get("isBlack", False)
        elif isinstance(cell, str):
            if cell == "#":
                is_black = True
            elif cell == "." or cell == "":
                existing_letter = None
            else:
                existing_letter = cell.strip().upper()

        if is_black:
            conflicts.append(f"Cannot place '{letter}' at ({target_row}, {target_col}): cell is black")
        elif existing_letter and existing_letter != letter:
            # Only report conflict if letters DON'T match
            conflicts.append(
                f"Letter conflict at ({target_row}, {target_col}): "
                f"trying to place '{letter}' but cell already contains '{existing_letter}'"
            )
        # If existing_letter matches letter, that's a valid intersection - allow it

    # Compute the word's cells and the boundary black squares this placement
    # needs (cell before the word and cell after it, when those cells are
    # currently empty).
    word_cells = set()
    for i in range(len(word)):
        if direction == "across":
            word_cells.add((row, col + i))
        else:
            word_cells.add((row + i, col))

    if direction == "across":
        boundary_candidates = [(row, col - 1), (row, col + len(word))]
    else:
        boundary_candidates = [(row - 1, col), (row + len(word), col)]

    boundary_blacks: List[Cell] = []
    for br, bc in boundary_candidates:
        if not (0 <= br < grid_size and 0 <= bc < len(grid[br])):
            continue
        state, _ = _cell_state(grid, br, bc)
        if state == "empty":
            boundary_blacks.append((br, bc))
        # 'black' needs nothing; 'letter' means the word abuts existing fill
        # and no boundary square is added (existing behavior)

    # Every added black square must get its 180-degree rotational twin, or
    # the resulting grid fails the symmetry check. Refuse placements whose
    # twin cell would land on a letter (including a letter of the word being
    # placed).
    twin_blacks: List[Cell] = []
    for br, bc in boundary_blacks:
        tr, tc = grid_size - 1 - br, grid_size - 1 - bc
        if (tr, tc) == (br, bc) or (tr, tc) in boundary_blacks:
            continue  # Twin is itself / another boundary square
        if (tr, tc) in word_cells:
            conflicts.append(
                f"Boundary black square at ({br}, {bc}) requires a symmetric "
                f"black square at ({tr}, {tc}), which is occupied by this "
                f"word — placement would break grid symmetry"
            )
            continue
        state, twin_letter = _cell_state(grid, tr, tc)
        if state == "letter":
            conflicts.append(
                f"Boundary black square at ({br}, {bc}) requires a symmetric "
                f"black square at ({tr}, {tc}), but that cell contains "
                f"'{twin_letter}'"
            )
        elif state == "empty":
            twin_blacks.append((tr, tc))
        # 'black' twin already exists — nothing to add

    return conflicts, boundary_blacks, twin_blacks


def validate_placement(grid: List[List], placement: Dict) -> List[str]:
    """
    Check a placement against a grid for conflicts.

    Returns a list of human-readable conflict messages; an empty list means
    the placement is valid. This is the single gate both the apply-placement
    route and ThemePlacer's suggestion filtering call — see module docstring.

    Read-only — does not mutate grid.
    """
    conflicts, _, _ = check_placement(grid, placement)
    return conflicts
