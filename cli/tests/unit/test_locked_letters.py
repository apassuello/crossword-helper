"""Unit tests for cli/src/fill/locked_letters.py.

novice-readiness spec 0.2.4 §2.1 (C12): which input letters `fill` locks.
"""

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.locked_letters import apply_lock_mode, cell_list, input_lock_letters


def _g33():
    """G33: 3x3, all white, with C at (0,0) and A at (1,1)."""
    grid = Grid(3, validate_size=False)
    grid.set_letter(0, 0, "C")
    grid.set_letter(1, 1, "A")
    grid.locked_cells = set()
    return grid


@pytest.mark.parametrize(
    "grid_data, lock_filled, expected",
    [
        ({"locked": [[0, 0]]}, True, {(0, 0)}),
        ({"locked": []}, True, set()),
        ({}, True, {(0, 0), (1, 1)}),
        ({}, False, set()),
        ({"locked": [[0, 0]]}, False, set()),
    ],
    ids=["key-listed", "key-empty", "key-absent", "absent-no-lock", "key-listed-no-lock"],
)
def test_apply_lock_mode_rows(grid_data, lock_filled, expected):
    grid = _g33()
    # from_dict's outcome for the key, as Task 2.1 defines it
    if "locked" in grid_data:
        grid.locked_cells = {tuple(c) for c in grid_data["locked"]}
    apply_lock_mode(grid, grid_data, lock_filled)
    assert grid.locked_cells == expected


def test_apply_lock_mode_through_from_dict():
    """The rows hold on a grid built by Grid.from_dict, not only a hand-built one."""
    data = {"size": 3, "grid": [["C", ".", "."], [".", "A", "."], [".", ".", "."]]}
    grid = Grid.from_dict(data, strict_size=False)
    assert grid.locked_cells == set()
    apply_lock_mode(grid, data, True)
    assert grid.locked_cells == {(0, 0), (1, 1)}


def test_cell_list_unique_sorted_row_major():
    assert cell_list([(2, 1), (0, 2), (2, 1), (0, 0)]) == [[0, 0], [0, 2], [2, 1]]


def test_cell_list_empty():
    assert cell_list([]) == []


def test_input_lock_letters_maps_locked_cells_to_letters():
    grid = _g33()
    grid.locked_cells = {(0, 0), (1, 1)}
    assert input_lock_letters(grid) == {(0, 0): "C", (1, 1): "A"}


def test_input_lock_letters_empty_without_locks():
    assert input_lock_letters(_g33()) == {}


# ---------------------------------------------------------------------------
# changed_locked_cells: the end-to-end postcondition's comparison
# novice-readiness spec 0.2.4 §2.1 (D3)
# ---------------------------------------------------------------------------


def _changed(setup, expected):
    from cli.src.fill.locked_letters import changed_locked_cells

    grid = Grid(3, validate_size=False)
    setup(grid)
    return changed_locked_cells(grid, expected)


def test_pc1_unchanged_letter():
    assert _changed(lambda g: g.set_letter(0, 0, "C"), {(0, 0): "C"}) == []


def test_pc2_different_letter():
    assert _changed(lambda g: g.set_letter(0, 0, "D"), {(0, 0): "C"}) == [[0, 0]]


def test_pc3_emptied_cell():
    assert _changed(lambda g: None, {(0, 0): "C"}) == [[0, 0]]


def test_pc4_blackened_cell():
    assert _changed(lambda g: g.set_black_square(0, 0, enforce_symmetry=False), {(0, 0): "C"}) == [[0, 0]]


def test_pc5_nothing_expected():
    assert _changed(lambda g: g.set_letter(0, 0, "D"), {}) == []


def test_postcondition_message_is_pinned():
    from cli.src.fill.locked_letters import POSTCONDITION_MESSAGE

    assert POSTCONDITION_MESSAGE == "Autofill changed a locked letter; nothing was written."
