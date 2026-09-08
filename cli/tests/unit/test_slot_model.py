"""
Tests for src.domain.slot_model (Task 1: geometry, construction, cell ownership).

Fixture is the 5x5 grid pinned by the task-1 brief (blacks at (0,3), (1,3),
(3,0), (4,1) -- cell indices 3, 8, 15, 21), built with validate_size=False
and enforce_symmetry=False since Grid otherwise rejects a non-11/15/21 size
and mirrors an asymmetric black onto its 180-degree partner. Slot geometry
and cell-ownership values below are transcribed from running Grid's own
enumerate_white_runs/get_word_slots oracle on that fixture, per the brief's
normative table -- not hand-derived from the grid diagram.

crossings == () is asserted here as a Task 1 fact: Task 2 populates it and
its first step rewrites this assertion against the fixture's crossings.
That is expected, not a regression in this file.
"""

from __future__ import annotations

import pytest
from src.core.grid import Grid
from src.domain.slot_model import SlotModel

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

    def test_crossings_is_empty_in_task_one(self, model):
        """Scoped to Task 1 -- Task 2's first step supersedes this with the 18-row assertion."""
        assert model.crossings == ()


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
