"""
Grid placement conflict validation.

Single implementation of the applier's conflict check — cell/intersection
conflicts, a letter abutting either end of the word (the entry would run on),
180-degree rotational-symmetry boundary-black conflicts, and new blacks that
strand an existing letter in a 1-2 cell entry — shared
by the apply-placement route (backend/api/theme_routes.py) and ThemePlacer's
candidate filtering (backend/core/theme_placer.py). Neither of those modules
duplicates this logic; both call in here instead (issue #15).

Deliberately does not import from theme_routes.py or theme_placer.py, so both
of them can import this module without creating an import cycle.

`check_placement` and `validate_placement` are read-only. The one write step —
letters with `isThemeLocked`, then the boundary and twin black squares — is
`apply_checked_placement`, the single mutation shared by the apply-placement
route and ThemePlacer's joint-plan search (TH4).
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

    # Messages are user-facing and the grid labels rows/columns from 1, so every
    # position printed below is the zero-based index + 1 (#94). Indices stay zero-based.
    conflicts: List[str] = []

    for i, letter in enumerate(word):
        if direction == "across":
            target_row = row
            target_col = col + i
            if target_col >= len(grid[row]):
                conflicts.append(f"Position ({target_row + 1}, {target_col + 1}) out of bounds")
                continue
        else:  # down
            target_row = row + i
            target_col = col
            if target_row >= len(grid):
                conflicts.append(f"Position ({target_row + 1}, {target_col + 1}) out of bounds")
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
            conflicts.append(f"Cannot place '{letter}' at ({target_row + 1}, {target_col + 1}): cell is black")
        elif existing_letter and existing_letter != letter:
            # Only report conflict if letters DON'T match
            conflicts.append(
                f"Letter conflict at ({target_row + 1}, {target_col + 1}): "
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
        state, boundary_letter = _cell_state(grid, br, bc)
        if state == "empty":
            boundary_blacks.append((br, bc))
        elif state == "letter":
            # A letter does not terminate an entry: the run would continue
            # through it, so the grid's actual entry is longer than the word
            # (e.g. CAT before an existing S reads CATS...). Only a black
            # square or the grid edge ends a word.
            conflicts.append(
                f"Cell ({br + 1}, {bc + 1}) next to the word contains "
                f"'{boundary_letter}': the entry would run on past the word"
            )
        # 'black' needs nothing

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
                f"Boundary black square at ({br + 1}, {bc + 1}) requires a symmetric "
                f"black square at ({tr + 1}, {tc + 1}), which is occupied by this "
                f"word — placement would break grid symmetry"
            )
            continue
        state, twin_letter = _cell_state(grid, tr, tc)
        if state == "letter":
            conflicts.append(
                f"Boundary black square at ({br + 1}, {bc + 1}) requires a symmetric "
                f"black square at ({tr + 1}, {tc + 1}), but that cell contains "
                f"'{twin_letter}'"
            )
        elif state == "empty":
            twin_blacks.append((tr, tc))
        # 'black' twin already exists — nothing to add

    # A new black square splits every white run it lands in. A piece left
    # beside it shorter than 3 cells (the minimum cli/src/core/validator.py
    # enforces) is refused only when it holds an existing letter: that cuts a
    # partly filled entry down to a stub the user cannot fix without losing
    # letters. An empty stub is allowed — the user can still black it out
    # (owner ruling, 2026-10-29).
    new_blacks = set(boundary_blacks) | set(twin_blacks)

    def _is_black_after(r: int, c: int) -> bool:
        return (r, c) in new_blacks or _cell_state(grid, r, c)[0] == "black"

    for br, bc in sorted(new_blacks):
        for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            run = []
            r, c = br + dr, bc + dc
            while 0 <= r < grid_size and 0 <= c < len(grid[r]) and not _is_black_after(r, c):
                run.append((r, c))
                r, c = r + dr, c + dc
            if 0 < len(run) < 3 and any(_cell_state(grid, r, c)[0] == "letter" for r, c in run):
                first, last = min(run), max(run)
                conflicts.append(
                    f"Black square at ({br + 1}, {bc + 1}) would leave a {len(run)}-letter "
                    f"entry at ({first[0] + 1}, {first[1] + 1})-({last[0] + 1}, {last[1] + 1})"
                )

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


def _set_black(grid: List[List], r: int, c: int) -> None:
    """Turn a cell into a black square, preserving cell format."""
    if isinstance(grid[r][c], dict):
        grid[r][c] = {"letter": "", "isBlack": True}
    else:
        grid[r][c] = "#"


def apply_checked_placement(grid: List[List], placement: Dict) -> Tuple[List[str], List[List[int]]]:
    """
    Check a placement and, if it has no conflicts, write it into `grid`.

    Returns (conflicts, added_blacks). On conflicts the grid is untouched and
    added_blacks is []. Otherwise the word's letters are written as
    theme-locked dict cells and the boundary and twin black squares are set
    (conflicts were already checked, so neither can clobber a letter).

    Mutates only the row lists of `grid`: every cell is replaced, never edited
    in place, so a caller can search on `[row[:] for row in grid]` without a
    deep copy. Works on both cell formats check_placement reads.
    """
    conflicts, boundary_blacks, twin_blacks = check_placement(grid, placement)
    if conflicts:
        return conflicts, []

    word = placement["word"].upper()
    row = placement["row"]
    col = placement["col"]
    direction = placement["direction"]

    for i, letter in enumerate(word):
        if direction == "across":
            target_row, target_col = row, col + i
        else:
            target_row, target_col = row + i, col
        cell = grid[target_row][target_col]
        if isinstance(cell, dict):
            new_cell = dict(cell)
            new_cell["letter"] = letter
            new_cell["isThemeLocked"] = True
        else:
            new_cell = {"letter": letter, "isBlack": False, "isThemeLocked": True}
        grid[target_row][target_col] = new_cell

    added_blacks: List[List[int]] = []
    for br, bc in boundary_blacks + twin_blacks:
        _set_black(grid, br, bc)
        added_blacks.append([br, bc])
    return conflicts, added_blacks
