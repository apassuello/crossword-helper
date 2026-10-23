"""Unit tests for cli/src/fill/locked_letters.py.

novice-readiness spec 0.2.4 §2.1 (C12): which input letters `fill` locks.
"""

import pytest

from cli.src.core.grid import Grid
from cli.src.domain.fillability import assess
from cli.src.domain.letter_bitset import LetterBitsetIndex
from cli.src.domain.slot_model import SlotModel, fixed_from_grid, pattern
from cli.src.fill.locked_letters import (
    OFF_LIST_WARNING_PREFIX,
    apply_lock_mode,
    blocked_text_lines,
    cell_list,
    input_lock_letters,
    off_list_warning,
    preflight,
    stuck_cells,
)
from cli.src.fill.word_list import WordList


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


# ---------------------------------------------------------------------------
# preflight / off_list_warning / blocked_text_lines
# novice-readiness spec 0.2.4 §2.1 (C1, C4, M2, B2)
# ---------------------------------------------------------------------------

L1 = ["CAT", "COT", "CUT", "QUA", "XIS"]
L2 = ["CRANE", "SLATE"]
L5 = ["COD", "ALE", "BEE", "OLE", "DEE"]


def _wl(words):
    return WordList([(w, 50) for w in words])


def _grid(rows, locked=None):
    """Build a Grid from rows of '.', '#' and letters; lock every letter unless `locked` is given."""
    grid = Grid(len(rows), validate_size=False)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                grid.set_black_square(r, c, enforce_symmetry=False)
            elif ch != ".":
                grid.set_letter(r, c, ch)
    grid.locked_cells = (
        {(r, c) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch not in ".#"} if locked is None else set(locked)
    )
    return grid


G33_QX = [["Q", "X", "."], [".", ".", "."], [".", ".", "."]]
G33_EMPTY = [[".", ".", "."], [".", ".", "."], [".", ".", "."]]
G44 = [["#", ".", ".", "."], [".", ".", ".", "."], [".", ".", ".", "."], [".", ".", ".", "#"]]


def test_preflight_case_1_dead_slot_through_locked_cells():
    result = preflight(_grid(G33_QX), _wl(L1))
    assert result.reason == "no_word_fits"
    assert result.blocked_cells == [[0, 0], [0, 1]]
    assert result.blocked_slots == [{"row": 0, "col": 0, "direction": "across", "length": 3, "pattern": "QX?"}]
    assert result.off_list_cells == []
    assert result.off_list_words == []


def test_preflight_unlocked_letters_take_no_part():
    result = preflight(_grid(G33_QX, locked=[]), _wl(L1))
    assert result.reason is None


def test_preflight_partial_lock_matches():
    assert preflight(_grid(G33_QX, locked=[(0, 0)]), _wl(L1)).reason is None


def test_preflight_b2_empty_grid():
    result = preflight(_grid(G33_EMPTY), _wl(L2))
    assert result.reason == "no_word_of_length"
    assert result.blocked_cells == []
    assert [(s["row"], s["col"], s["direction"], s["length"], s["pattern"]) for s in result.blocked_slots] == [
        (0, 0, "across", 3, "???"),
        (1, 0, "across", 3, "???"),
        (2, 0, "across", 3, "???"),
        (0, 0, "down", 3, "???"),
        (0, 1, "down", 3, "???"),
        (0, 2, "down", 3, "???"),
    ]


def test_preflight_b2_length_block_holding_locked_letter_goes_to_b2():
    rows = [["Q", ".", "."], [".", ".", "."], [".", ".", "."]]
    result = preflight(_grid(rows), _wl(L2))
    assert result.reason == "no_word_of_length"
    assert result.blocked_cells == []
    assert len(result.blocked_slots) == 6
    patterns = {(s["row"], s["col"], s["direction"]): s["pattern"] for s in result.blocked_slots}
    assert patterns[(0, 0, "across")] == "Q??"
    assert patterns[(0, 0, "down")] == "Q??"
    assert patterns[(1, 0, "across")] == "???"


def test_preflight_b2_with_typed_letter_on_g44():
    rows = [list(r) for r in G44]
    rows[1][1] = "A"
    result = preflight(_grid(rows), _wl(["CARE"]))
    assert result.reason == "no_word_of_length"
    assert result.blocked_cells == []
    assert [(s["row"], s["col"], s["direction"], s["length"], s["pattern"]) for s in result.blocked_slots] == [
        (0, 1, "across", 3, "???"),
        (3, 0, "across", 3, "???"),
        (1, 0, "down", 3, "???"),
        (0, 3, "down", 3, "???"),
    ]


def test_preflight_refuted_without_dead_slot_is_not_blocked():
    """P10: only the arc-consistency cascade refutes the empty grid; no slot is dead by itself."""
    grid = _grid(G33_EMPTY)
    index = preflight(grid, _wl(["ABA"])).index
    model = SlotModel.from_grid(grid)
    fixed = fixed_from_grid(grid)
    assert assess(model, index, fixed, min_score=0).refuted is True
    assert all(index.count_matches(pattern(model, s.id, fixed), min_score=0) == 1 for s in model.slots)
    assert preflight(grid, _wl(["ABA"])).reason is None


def test_preflight_case_2_off_list_typed_word():
    rows = [["C", "A", "B"], [".", ".", "."], [".", ".", "."]]
    result = preflight(_grid(rows), _wl(L5))
    assert result.reason is None
    assert result.off_list_cells == [[0, 0], [0, 1], [0, 2]]
    assert result.off_list_words == ["CAB"]


def test_preflight_case_2_two_words_in_slot_model_order():
    rows = [["C", "A", "B"], [".", ".", "."], ["T", "A", "T"]]
    result = preflight(_grid(rows), _wl(["COT", "CAT", "ART", "AHA", "BOA", "BIT"]))
    assert result.off_list_words == ["CAB", "TAT"]


def test_preflight_empty_lock_set_has_no_off_list():
    rows = [["C", "A", "B"], [".", ".", "."], [".", ".", "."]]
    result = preflight(_grid(rows, locked=[]), _wl(L5))
    assert result.off_list_cells == [] and result.off_list_words == []


def test_preflight_never_mutates_the_grid():
    grid = _grid(G33_QX, locked=[(0, 0)])
    before = (grid.cells.copy(), set(grid.locked_cells))
    preflight(grid, _wl(L1))
    assert (grid.cells == before[0]).all() and grid.locked_cells == before[1]


def test_off_list_warning_text():
    assert OFF_LIST_WARNING_PREFIX == "Typed words not in the selected word lists: "
    assert off_list_warning(["CAB", "TAT"]) == "Typed words not in the selected word lists: CAB, TAT"


def test_blocked_text_lines_no_word_fits():
    result = preflight(_grid(G33_QX), _wl(L1))
    assert blocked_text_lines(result) == ["Blocked: no word fits QX? at 0,0 across"]


def test_blocked_text_lines_one_line_per_length_ascending():
    rows = [list(r) for r in G44]
    result = preflight(_grid(rows), _wl(L2))
    assert blocked_text_lines(result) == [
        "Blocked: the selected word lists have no words of length 3",
        "Blocked: the selected word lists have no words of length 4",
    ]


def test_blocked_text_lines_b2_g33():
    result = preflight(_grid(G33_EMPTY), _wl(L2))
    assert blocked_text_lines(result) == ["Blocked: the selected word lists have no words of length 3"]


def test_blocked_text_lines_empty_when_not_blocked():
    assert blocked_text_lines(preflight(_grid(G33_EMPTY, locked=[]), _wl(L1))) == []


# ---------------------------------------------------------------------------
# stuck_cells
# novice-readiness spec 0.2.4 §2.1 (C2, C11)
# ---------------------------------------------------------------------------

SC_LOCKED = {(0, 0), (0, 1)}
SC_ROWS_OPEN = ["CA.", "...", "..."]
SC_ROWS_FULL = ["CAX", "OLE", "TED"]
SC_WORDS = [("CAT", 10), ("COT", 50), ("ART", 50)]
SC_INVALID = {"slot": (0, 0, "across"), "pattern": "CAX", "reason": "invalid_word"}


def _sc(rows, words, min_score, problematic, locked=SC_LOCKED, index="build"):
    grid = _grid(rows, locked=locked)
    if index == "build":
        index = LetterBitsetIndex.from_word_list(WordList(words))
    return stuck_cells(grid, locked, problematic, index, min_score)


def test_sc1_unmatched_pattern_under_min_score():
    assert _sc(SC_ROWS_OPEN, SC_WORDS, 30, []) == [[0, 0], [0, 1]]


def test_sc2_min_score_zero_matches():
    assert _sc(SC_ROWS_OPEN, SC_WORDS, 0, []) == []


def test_sc3_invalid_word_entry():
    assert _sc(SC_ROWS_FULL, [("COT", 50)], 30, [SC_INVALID]) == [[0, 0], [0, 1]]


def test_sc4_other_reason_contributes_nothing():
    entry = dict(SC_INVALID, reason="unfilled")
    assert _sc(SC_ROWS_FULL, [("COT", 50)], 30, [entry]) == []


def test_sc5_beam_shaped_entry_contributes_nothing():
    entry = {"row": 0, "col": 0, "direction": "across", "length": 3}
    assert _sc(SC_ROWS_FULL, [("COT", 50)], 30, [entry]) == []


def test_sc6_invalid_word_slot_without_locked_cell():
    entry = {"slot": (1, 0, "across"), "pattern": "OLE", "reason": "invalid_word"}
    assert _sc(SC_ROWS_FULL, [("COT", 50)], 30, [entry]) == []


def test_sc7_cells_in_both_sources_are_unique():
    assert _sc(SC_ROWS_OPEN, SC_WORDS, 30, [SC_INVALID]) == [[0, 0], [0, 1]]


def test_sc8_resume_empty_lock_set_never_touches_the_index():
    class _Untouchable:
        def __getattr__(self, name):
            raise AssertionError(f"index touched: {name}")

    grid = _grid(SC_ROWS_OPEN, locked=set())
    assert stuck_cells(grid, set(), [SC_INVALID], None, 30) == []
    assert stuck_cells(grid, set(), [SC_INVALID], _Untouchable(), 30) == []
