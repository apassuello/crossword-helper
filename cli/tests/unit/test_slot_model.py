"""
Tests for src.domain.slot_model (Task 1 geometry; Task 2 crossings; Task 3
the Grid bridge -- fixed_from_grid and pattern).

Fixture is the 5x5 grid pinned by the task-1 brief (blacks at (0,3), (1,3),
(3,0), (4,1) -- cell indices 3, 8, 15, 21), built with validate_size=False
and enforce_symmetry=False since Grid otherwise rejects a non-11/15/21 size
and mirrors an asymmetric black onto its 180-degree partner. Slot geometry,
cell-ownership and crossing values below are transcribed from running the
oracles named in the task briefs against that fixture -- not hand-derived
from the grid diagram.
"""

from __future__ import annotations

import pytest
from src.core.grid import Grid
from src.domain.slot_model import Crossing, SlotModel, fixed_from_grid, pattern
from src.fill.autofill import Autofill
from src.fill.beam_search.utils.slot_utils import SlotIntersectionHelper
from src.fill.word_list import WordList

FIXTURE_SIZE = 5
FIXTURE_BLACK_POSITIONS = [(0, 3), (1, 3), (3, 0), (4, 1)]
FIXTURE_BLACKS = (3, 8, 15, 21)

# (slot id, direction, row, col, length, cells) -- literal, from the task-1
# brief's normative table (SlotModel.from_grid(g, min_length=3)).
SLOT_TABLE = [
    (0, "across", 0, 0, 3, (0, 1, 2)),
    (1, "across", 1, 0, 3, (5, 6, 7)),
    (2, "across", 2, 0, 5, (10, 11, 12, 13, 14)),
    (3, "across", 3, 1, 4, (16, 17, 18, 19)),
    (4, "across", 4, 2, 3, (22, 23, 24)),
    (5, "down", 0, 0, 3, (0, 5, 10)),
    (6, "down", 0, 1, 4, (1, 6, 11, 16)),
    (7, "down", 0, 2, 5, (2, 7, 12, 17, 22)),
    (8, "down", 2, 3, 3, (13, 18, 23)),
    (9, "down", 0, 4, 5, (4, 9, 14, 19, 24)),
]

CELL_ACROSS = (0, 0, 0, -1, -1, 1, 1, 1, -1, -1, 2, 2, 2, 2, 2, -1, 3, 3, 3, 3, -1, -1, 4, 4, 4)
CELL_DOWN = (5, 6, 7, -1, 9, 5, 6, 7, -1, 9, 5, 6, 7, 8, 9, -1, 6, 7, 8, 9, -1, -1, 7, 8, 9)
UNSLOTTED = (20,)

# (cell, across_id, across_pos, down_id, down_pos) -- literal, from the task-2
# brief's normative table (SlotModel.from_grid(g, min_length=3)), already in
# the ascending-by-cell order the contract requires crossings to hold.
CROSSING_TABLE = [
    (0, 0, 0, 5, 0),
    (1, 0, 1, 6, 0),
    (2, 0, 2, 7, 0),
    (5, 1, 0, 5, 1),
    (6, 1, 1, 6, 1),
    (7, 1, 2, 7, 1),
    (10, 2, 0, 5, 2),
    (11, 2, 1, 6, 2),
    (12, 2, 2, 7, 2),
    (13, 2, 3, 8, 0),
    (14, 2, 4, 9, 2),
    (16, 3, 0, 6, 3),
    (17, 3, 1, 7, 3),
    (18, 3, 2, 8, 1),
    (19, 3, 3, 9, 3),
    (22, 4, 0, 7, 4),
    (23, 4, 1, 8, 2),
    (24, 4, 2, 9, 4),
]


@pytest.fixture(scope="module")
def fixture_grid() -> Grid:
    g = Grid(FIXTURE_SIZE, validate_size=False)
    for row, col in FIXTURE_BLACK_POSITIONS:
        g.set_black_square(row, col, enforce_symmetry=False)
    return g


@pytest.fixture(scope="module")
def model(fixture_grid) -> SlotModel:
    return SlotModel.from_grid(fixture_grid, min_length=3)


class TestNormativeCases:
    """Exact values from the task-1 brief's table, on the fixture grid."""

    def test_slot_count_matches_normative_total(self, model):
        assert len(model.slots) == 10

    def test_size_matches_grid_size(self, model):
        assert model.size == 5

    def test_blacks_matches_normative_fixture_sorted(self, model):
        assert model.blacks == FIXTURE_BLACKS

    @pytest.mark.parametrize("slot_id,direction,row,col,length,cells", SLOT_TABLE)
    def test_slot_fields_match_normative_table(self, model, slot_id, direction, row, col, length, cells):
        """Slot.id must equal its position in model.slots -- the id = index guarantee."""
        slot = model.slots[slot_id]
        assert (slot.id, slot.direction, slot.row, slot.col, slot.length, slot.cells) == (
            slot_id,
            direction,
            row,
            col,
            length,
            cells,
        )

    def test_cell_across_matches_normative_tuple(self, model):
        assert model.cell_across == CELL_ACROSS

    def test_cell_down_matches_normative_tuple(self, model):
        assert model.cell_down == CELL_DOWN

    def test_cell_across_has_length_size_squared(self, model):
        assert len(model.cell_across) == FIXTURE_SIZE * FIXTURE_SIZE

    def test_cell_down_has_length_size_squared(self, model):
        assert len(model.cell_down) == FIXTURE_SIZE * FIXTURE_SIZE

    def test_unslotted_matches_normative_tuple(self, model):
        """Cell 20 is (4,0): its across and down runs are both length 1, below min_length=3."""
        assert model.unslotted == UNSLOTTED

    def test_unslotted_excludes_a_cell_owned_only_by_the_crossing_direction(self, model):
        """Cells 4 and 9 sit in a 1-cell across run but a 5-cell down run: owned, not unslotted."""
        assert 4 not in model.unslotted
        assert 9 not in model.unslotted

    @pytest.mark.parametrize("index,row", list(enumerate(CROSSING_TABLE)))
    def test_crossings_match_normative_table_in_order(self, model, index, row):
        """model.crossings[index] must equal the brief's row at that position -- not just be present somewhere."""
        cell, across_id, across_pos, down_id, down_pos = row
        assert model.crossings[index] == Crossing(
            cell=cell, across_id=across_id, across_pos=across_pos, down_id=down_id, down_pos=down_pos
        )


class TestCrossingsStructuralProperties:
    """Properties model.crossings must hold beyond matching the literal rows."""

    def test_crossings_total_matches_normative_row_count(self, model):
        assert len(model.crossings) == len(CROSSING_TABLE)

    def test_crossings_sorted_strictly_ascending_by_cell(self, model):
        cells = [c.cell for c in model.crossings]
        assert all(a < b for a, b in zip(cells, cells[1:]))

    def test_crossing_cell_values_are_unique(self, model):
        cells = [c.cell for c in model.crossings]
        assert len(set(cells)) == len(cells)

    def test_grid_with_no_crossings_yields_empty_tuple(self):
        """3x3 grid, middle row entirely black: across runs exist, no down run reaches min_length."""
        built = SlotModel.from_blacks(3, [3, 4, 5], min_length=3)

        assert built.slots  # slots exist; it's the crossings, not the geometry, that's empty
        assert built.crossings == ()


class TestCrossingsOracleA:
    """Cross-check against SlotIntersectionHelper (cli/src/fill/beam_search/utils/slot_utils.py).

    Valid only at min_length=3: get_slot_crossings calls grid.get_word_slots()
    with no argument, so it always sees the default filter regardless of the
    model's min_length (slot_utils.py:156) -- this fixture's model already
    uses min_length=3, so no mismatch arises.
    """

    @staticmethod
    def _slot_dict(slot):
        return {"row": slot.row, "col": slot.col, "direction": slot.direction, "length": slot.length}

    @pytest.mark.parametrize("index", range(len(CROSSING_TABLE)))
    def test_get_crossing_position_matches_the_materialised_crossing(self, model, index):
        """Compares model.crossings[index] (the field under test) against a fresh oracle computation.

        Deliberately reads positions from the crossing object, not from CROSSING_TABLE,
        so a wrong materialised position -- not just a wrong literal -- fails this test.
        Called across-dict-first, per-argument-order (slot_utils.py:96): (across_pos, down_pos) directly.
        """
        crossing = model.crossings[index]
        across_dict = self._slot_dict(model.slots[crossing.across_id])
        down_dict = self._slot_dict(model.slots[crossing.down_id])

        assert SlotIntersectionHelper.get_crossing_position(across_dict, down_dict) == (
            crossing.across_pos,
            crossing.down_pos,
        )

    @pytest.mark.parametrize("across_id", [0, 1, 2, 3, 4])
    def test_get_slot_crossings_matches_the_down_slots_this_across_slot_crosses(self, model, fixture_grid, across_id):
        across_dict = self._slot_dict(model.slots[across_id])

        oracle_down_starts = {
            (d["row"], d["col"]) for d in SlotIntersectionHelper.get_slot_crossings(across_dict, fixture_grid)
        }
        model_down_starts = {
            (model.slots[c.down_id].row, model.slots[c.down_id].col) for c in model.crossings if c.across_id == across_id
        }

        assert oracle_down_starts == model_down_starts


class TestCrossingsOracleB:
    """Cross-check against Autofill's own CSP constraint graph (cli/src/fill/autofill.py).

    Independent of SlotIntersectionHelper: Autofill builds its graph through
    its own _get_intersection (autofill.py:851).
    """

    @pytest.fixture(scope="module")
    def solver(self, fixture_grid) -> Autofill:
        word_list = WordList([("CAT", 50), ("DOG", 50), ("BIRDS", 50), ("HORSE", 50), ("FISH", 50)])
        autofill = Autofill(fixture_grid, word_list)
        autofill._initialize_csp(fixture_grid.get_word_slots(3))
        return autofill

    @pytest.mark.parametrize("index", range(len(CROSSING_TABLE)))
    def test_solver_constraints_match_the_materialised_crossing(self, model, solver, index):
        """Reads positions from model.crossings[index], not CROSSING_TABLE -- see OracleA's sibling test.

        solver's slot ids index the list it was given; map through slot_id_map[model.slot_key(...)].
        """
        crossing = model.crossings[index]
        i = solver.slot_id_map[model.slot_key(crossing.across_id)]
        j = solver.slot_id_map[model.slot_key(crossing.down_id)]

        matches = [entry for entry in solver.constraints[i] if entry[0] == j]

        assert len(matches) == 1
        assert matches[0][1:] == (crossing.across_pos, crossing.down_pos)


class TestOrderedListOracle:
    """model.slots must match Grid.get_word_slots' order exactly, at every min_length it supports.

    Asserted as an ordered list, not a set: a set comparison would still pass
    on a permutation of the same runs, which would silently renumber every
    Slot.id since id is position in model.slots.
    """

    @pytest.mark.parametrize("min_length", [1, 2, 3, 4, 5])
    def test_slot_order_matches_grid_oracle(self, fixture_grid, min_length):
        built = SlotModel.from_grid(fixture_grid, min_length=min_length)

        actual = [(s.row, s.col, s.direction, s.length) for s in built.slots]
        expected = [(d["row"], d["col"], d["direction"], d["length"]) for d in fixture_grid.get_word_slots(min_length)]

        assert actual == expected


class TestFromGridDelegation:
    def test_from_grid_default_min_length_is_three(self, fixture_grid, model):
        assert SlotModel.from_grid(fixture_grid) == model

    def test_from_grid_ignores_letters_in_the_grid(self, fixture_grid, model):
        """from_grid contributes only size and black cells; filled letters must not change any field."""
        lettered = fixture_grid.clone()
        lettered.set_letter(0, 0, "A")
        lettered.set_letter(2, 2, "Z")

        assert SlotModel.from_grid(lettered, min_length=3) == model


class TestFromBlacksConstruction:
    def test_default_min_length_is_three(self, model):
        assert SlotModel.from_blacks(5, FIXTURE_BLACKS) == model

    def test_input_order_does_not_matter(self, model):
        assert SlotModel.from_blacks(5, [21, 3, 15, 8], min_length=3) == model

    def test_duplicates_in_input_collapse(self, model):
        assert SlotModel.from_blacks(5, [3, 3, 8, 15, 21], min_length=3) == model

    def test_blacks_field_is_sorted_ascending_regardless_of_input_order(self):
        built = SlotModel.from_blacks(5, [21, 3, 15, 8], min_length=3)

        assert built.blacks == FIXTURE_BLACKS

    def test_accepts_an_arbitrary_iterable_not_only_a_sequence(self, model):
        """A generator can only be consumed once -- catches an implementation that iterates blacks twice."""
        built = SlotModel.from_blacks(5, iter([21, 3, 15, 8]), min_length=3)

        assert built == model

    def test_black_index_equal_to_size_squared_raises_value_error(self):
        with pytest.raises(ValueError):
            SlotModel.from_blacks(5, [25])

    def test_negative_black_index_raises_value_error(self):
        with pytest.raises(ValueError):
            SlotModel.from_blacks(5, [-1])


class TestSlotKey:
    def test_slot_key_of_first_slot(self, model):
        assert model.slot_key(0) == (0, 0, "across")

    def test_slot_key_of_last_slot(self, model):
        assert model.slot_key(9) == (0, 4, "down")

    def test_negative_slot_id_addresses_from_the_end_without_raising(self, model):
        """Contract (spec decision 12): a negative slot_id indexes from the end; model.slots[-1] is slot 9."""
        assert model.slot_key(-1) == (0, 4, "down")

    def test_out_of_range_slot_id_raises_index_error_unguarded(self, model):
        with pytest.raises(IndexError):
            model.slot_key(10)


# ---------------------------------------------------------------------------
# Task 3: the Grid bridge -- fixed_from_grid and pattern.
#
# fixture_grid/model above are module-scoped and never mutated by any test
# above this point; the fixtures below build their own Grid instances (or
# clone one) before placing words, so no test here can leak state into the
# TestNormativeCases/TestCrossings*/TestFromGrid*/TestFromBlacks*/TestSlotKey
# classes above, and no ordering between test files or classes matters.
# ---------------------------------------------------------------------------


def _slot_dict(slot) -> dict:
    return {"row": slot.row, "col": slot.col, "length": slot.length, "direction": slot.direction}


@pytest.fixture(scope="module")
def cat_grid() -> Grid:
    """The fixture grid plus one unlocked placement: CAT across at (0, 0)."""
    g = Grid(FIXTURE_SIZE, validate_size=False)
    for row, col in FIXTURE_BLACK_POSITIONS:
        g.set_black_square(row, col, enforce_symmetry=False)
    g.place_word("CAT", 0, 0, "across")
    return g


@pytest.fixture(scope="module")
def horse_grid(cat_grid) -> Grid:
    """cat_grid plus a second, locked placement: HORSE down at (0, 4)."""
    g = cat_grid.clone()
    g.place_word("HORSE", 0, 4, "down", lock=True)
    return g


# (slot id 0-9) -- literal, from the task-3 brief's normative tables.
EMPTY_PATTERNS = ("???", "???", "?????", "????", "???", "???", "????", "?????", "???", "?????")
CAT_PATTERNS = ("CAT", "???", "?????", "????", "???", "C??", "A???", "T????", "???", "?????")
HORSE_PATTERNS = ("CAT", "???", "????R", "???S", "??E", "C??", "A???", "T????", "???", "HORSE")


class TestFixedFromGrid:
    """fixed_from_grid(grid): a flat, index-based read of grid content only -- no locked-ness."""

    def test_length_is_size_squared(self, fixture_grid):
        assert len(fixed_from_grid(fixture_grid)) == FIXTURE_SIZE * FIXTURE_SIZE

    def test_empty_grid_is_all_empty_strings(self, fixture_grid):
        assert fixed_from_grid(fixture_grid) == ("",) * (FIXTURE_SIZE * FIXTURE_SIZE)

    def test_black_cells_are_empty_string(self, fixture_grid):
        fixed = fixed_from_grid(fixture_grid)
        for black in FIXTURE_BLACKS:
            assert fixed[black] == ""

    def test_unlocked_filled_cells_give_their_letters(self, cat_grid):
        assert fixed_from_grid(cat_grid)[0:3] == ("C", "A", "T")

    def test_black_cell_stays_empty_string_next_to_a_filled_word(self, cat_grid):
        """Cell 3 is (0, 3), a black square adjacent to CAT's last letter at cell 2."""
        assert fixed_from_grid(cat_grid)[3] == ""

    def test_empty_white_cell_stays_empty_string_after_an_unrelated_placement(self, cat_grid):
        """Cell 5 is (1, 0): white, untouched by the CAT placement at row 0."""
        assert fixed_from_grid(cat_grid)[5] == ""

    def test_locked_placement_differs_from_unlocked_only_in_lock_state(self, horse_grid):
        """Sanity check on the fixture itself, not on fixed_from_grid: the two placements
        this task discriminates between must actually differ only in lock, not in anything else."""
        assert horse_grid.is_locked(0, 4) is True
        assert horse_grid.is_locked(0, 0) is False

    def test_locked_filled_cells_give_their_letters_same_as_unlocked(self, horse_grid):
        """The rule under test: a filled white cell gives its letter locked or not."""
        fixed = fixed_from_grid(horse_grid)
        assert (fixed[4], fixed[9], fixed[14], fixed[19], fixed[24]) == ("H", "O", "R", "S", "E")

    def test_earlier_unlocked_placement_is_unaffected_by_a_later_locked_one(self, horse_grid):
        assert fixed_from_grid(horse_grid)[0:3] == ("C", "A", "T")


class TestPattern:
    """pattern(model, slot_id, fixed): reads only model and fixed, never a Grid."""

    def test_empty_grid_patterns_match_normative_table(self, model, fixture_grid):
        fixed = fixed_from_grid(fixture_grid)
        actual = tuple(pattern(model, s.id, fixed) for s in model.slots)
        assert actual == EMPTY_PATTERNS

    def test_cat_placement_patterns_match_normative_table(self, model, cat_grid):
        fixed = fixed_from_grid(cat_grid)
        actual = tuple(pattern(model, s.id, fixed) for s in model.slots)
        assert actual == CAT_PATTERNS

    def test_locked_horse_placement_patterns_match_normative_table(self, model, horse_grid):
        fixed = fixed_from_grid(horse_grid)
        actual = tuple(pattern(model, s.id, fixed) for s in model.slots)
        assert actual == HORSE_PATTERNS

    def test_result_length_equals_slot_length_for_every_slot(self, model, horse_grid):
        fixed = fixed_from_grid(horse_grid)
        for s in model.slots:
            assert len(pattern(model, s.id, fixed)) == s.length

    def test_out_of_range_slot_id_raises_index_error(self, model, fixture_grid):
        fixed = fixed_from_grid(fixture_grid)
        with pytest.raises(IndexError):
            pattern(model, 10, fixed)

    def test_negative_slot_id_addresses_from_the_end_without_raising(self, model, horse_grid):
        """Same unguarded-negative-index contract as SlotModel.slot_key: model.slots[-1] is slot 9."""
        fixed = fixed_from_grid(horse_grid)
        assert pattern(model, -1, fixed) == HORSE_PATTERNS[9]

    def test_wrong_length_fixed_raises_value_error(self, model):
        with pytest.raises(ValueError):
            pattern(model, 0, ("",) * (model.size * model.size - 1))


class TestPatternMatchesGridByteForByte:
    """The task's real acceptance test (spec 6): pattern(...) must equal
    grid.get_pattern_for_slot(...) exactly, for every slot, in every one of
    the three fixture states -- not just the rows the brief's tables name."""

    @pytest.mark.parametrize("slot_id", range(10))
    def test_matches_grid_oracle_on_empty_grid(self, model, fixture_grid, slot_id):
        fixed = fixed_from_grid(fixture_grid)
        slot = model.slots[slot_id]
        assert pattern(model, slot_id, fixed) == fixture_grid.get_pattern_for_slot(_slot_dict(slot))

    @pytest.mark.parametrize("slot_id", range(10))
    def test_matches_grid_oracle_after_cat(self, model, cat_grid, slot_id):
        fixed = fixed_from_grid(cat_grid)
        slot = model.slots[slot_id]
        assert pattern(model, slot_id, fixed) == cat_grid.get_pattern_for_slot(_slot_dict(slot))

    @pytest.mark.parametrize("slot_id", range(10))
    def test_matches_grid_oracle_after_locked_horse(self, model, horse_grid, slot_id):
        fixed = fixed_from_grid(horse_grid)
        slot = model.slots[slot_id]
        assert pattern(model, slot_id, fixed) == horse_grid.get_pattern_for_slot(_slot_dict(slot))
