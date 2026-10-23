"""
Which input letters ``fill`` locks, and the cell lists that report them.

novice-readiness spec 0.2.4 §2.1 (C12): ``Grid.from_dict`` writes ``Grid.cells``
directly and applies only an explicit ``"locked"`` key, so the CLI decides the
rest here, once, on a fresh run. ``--resume`` never reaches this module.
"""

from typing import Dict, Iterable, List, Mapping, Tuple

from ..core.grid import Grid


def cell_list(cells: Iterable[Tuple[int, int]]) -> List[List[int]]:
    """Unique ``[row, col]`` pairs, zero-based, sorted row-major (spec §2.1, C11)."""
    return [[int(r), int(c)] for r, c in sorted({(int(r), int(c)) for r, c in cells})]


def apply_lock_mode(grid: Grid, grid_data: Mapping, lock_filled: bool) -> None:
    """
    Set ``grid.locked_cells`` for a fresh run (spec §2.1, C12).

    Call immediately after ``Grid.from_dict``, which has already validated any
    ``"locked"`` key (so an invalid list fails even under ``--no-lock-filled``).

    - ``lock_filled`` and ``"locked"`` in ``grid_data``: keep ``from_dict``'s set.
    - ``lock_filled`` and no key: every cell holding a letter.
    - not ``lock_filled``: no cell, with or without the key.
    """
    if not lock_filled:
        grid.locked_cells = set()
    elif "locked" not in grid_data:
        grid.locked_cells = {
            (row, col)
            for row in range(grid.size)
            for col in range(grid.size)
            if not grid.is_black(row, col) and not grid.is_empty(row, col)
        }


def input_lock_letters(grid: Grid) -> Dict[Tuple[int, int], str]:
    """``{(row, col): letter}`` for every cell in ``grid.locked_cells``."""
    return {(row, col): grid.get_cell(row, col) for row, col in grid.locked_cells}


POSTCONDITION_MESSAGE = "Autofill changed a locked letter; nothing was written."


def changed_locked_cells(grid: Grid, expected: Mapping[Tuple[int, int], str]) -> List[List[int]]:
    """
    Cell list of every ``expected`` cell that no longer holds its letter in ``grid``.

    novice-readiness spec 0.2.4 §2.1 (D3): the end-to-end postcondition. An empty,
    black or differently lettered cell all count as changed.
    """
    return cell_list(
        (row, col) for (row, col), letter in expected.items() if grid.is_black(row, col) or grid.get_cell(row, col) != letter
    )
