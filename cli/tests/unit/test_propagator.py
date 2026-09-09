"""
Tests for src.domain.propagator (Task 1: dataclasses and initial_state).

Fixture is FIX-A, the 5x5 grid pinned by global-constraints.md (blacks at
cell indices 3, 8, 15, 21; one unslotted cell, 20) together with
FIXTURE_WORDS, the same file's 14-word list. Both are transcribed verbatim
from that file, and every literal table below is transcribed from the
task-1 brief's normative tables -- which the brief states were taken by
running the real oracles against this fixture, not hand-derived. Cross-
checked independently against the real LetterBitsetIndex/SlotModel/pattern
before writing: running the brief's own precedence rule against FIX-A
reproduces every value below exactly.
"""

from __future__ import annotations

import dataclasses
import inspect
import typing
from typing import Callable

import numpy as np
import pytest
from src.domain.letter_bitset import LetterBitsetIndex
from src.domain.propagator import DomainState, MinScore, Result, Revision, initial_state
from src.domain.slot_model import SlotModel, pattern
from src.fill.word_list import WordList

FIXTURE_SIZE = 5
FIXTURE_BLACKS = (3, 8, 15, 21)

# (text, score) -- literal, from global-constraints.md's FIXTURE_WORDS.
FIXTURE_WORDS = [
    ("ARISE", 90),
    ("EVERY", 80),
    ("TRIES", 70),
    ("EARN", 60),
    ("NEAR", 50),
    ("EAR", 40),
    ("PEA", 40),
    ("SEA", 35),
    ("SPA", 30),
    ("PAR", 30),
    ("PET", 25),
    ("SET", 25),
    ("SAP", 20),
    ("SPY", 20),
]

# Canonical length-3 order ((-score, text)), from global-constraints.md's table --
# the exact (text, score) list an all-wildcard length-3 mask decodes to via
# index.words(3, mask).
CANONICAL_LENGTH_3 = [
    ("EAR", 40),
    ("PEA", 40),
    ("SEA", 35),
    ("PAR", 30),
    ("SPA", 30),
    ("PET", 25),
    ("SET", 25),
    ("SAP", 20),
    ("SPY", 20),
]

EMPTY_FIXED = tuple("" for _ in range(FIXTURE_SIZE * FIXTURE_SIZE))


def _fixed_with(overrides: dict) -> tuple:
    """EMPTY_FIXED with a handful of cells overridden -- the rest stay unfixed."""
    fixed = list(EMPTY_FIXED)
    for cell, letter in overrides.items():
        fixed[cell] = letter
    return tuple(fixed)


def _letters_string(bits, index: LetterBitsetIndex) -> str:
    """Decode an alphabet bitmask into its letters, in the index's own (sorted) order."""
    bits = int(bits)
    return "".join(letter for letter in index.alphabet if bits & (1 << index.letter_index[letter]))


def _length_dependent_min_score(length: int) -> int:
    """The brief's callable case: 40 for length-3 slots, 0 for every other length."""
    return 40 if length == 3 else 0


# Per-slot letter counts (index.count(m) for m in word_masks), FIX-A, all-empty fixed,
# slot ids 0..9 -- literal, from the task-1 brief's normative table.
MASK_COUNTS_MIN_SCORE_0 = (9, 9, 3, 2, 9, 9, 2, 3, 9, 3)
MASK_COUNTS_MIN_SCORE_30 = (5, 5, 3, 2, 5, 5, 2, 3, 5, 3)
MASK_COUNTS_CALLABLE = (2, 2, 3, 2, 2, 2, 2, 3, 2, 3)

# cell_letters on FIX-A, all-empty fixed, min_score=0, as letter strings ("" for 0) --
# literal, from the task-1 brief's normative table. Flat, cell = row * 5 + col.
CELL_LETTERS_TABLE = (
    "EPS", "E", "AT", "", "AET",
    "EP", "AE", "R", "", "RV",
    "AT", "R", "EI", "ES", "E",
    "", "N", "E", "A", "R",
    "", "", "ES", "AP", "Y",
)  # fmt: skip


@pytest.fixture(scope="module")
def fixture_word_list() -> WordList:
    return WordList(list(FIXTURE_WORDS))


@pytest.fixture(scope="module")
def bitset_index(fixture_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(fixture_word_list)


@pytest.fixture(scope="module")
def model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIXTURE_BLACKS, min_length=3)


class TestContractShapes:
    """Structural guards on the names Tasks 2/3/4 import -- signatures and dataclass
    shape are the contract itself (per the task brief), so pin them directly rather
    than only through initial_state's behavior."""

    def test_min_score_alias_is_the_typing_union_form(self):
        """global-constraints.md requires Union[int, Callable[[int], int]] specifically:
        int | Callable[...] as a module-level (runtime) alias raises TypeError on
        Python 3.9, which this 3.12 interpreter cannot catch by running the code --
        so the alias's actual runtime shape is pinned here instead."""
        assert typing.get_origin(MinScore) is typing.Union
        assert typing.get_args(MinScore) == (int, Callable[[int], int])

    def test_domain_state_fields_and_not_frozen(self):
        assert [f.name for f in dataclasses.fields(DomainState)] == [
            "model",
            "word_masks",
            "cell_letters",
            "fixed",
        ]
        assert DomainState.__dataclass_params__.frozen is False

    def test_revision_fields_and_frozen(self):
        assert [f.name for f in dataclasses.fields(Revision)] == [
            "source_crossing",
            "source_slot",
            "slot",
            "removed",
        ]
        assert Revision.__dataclass_params__.frozen is True

    def test_result_fields_and_frozen(self):
        assert [f.name for f in dataclasses.fields(Result)] == ["state", "wiped", "revisions"]
        assert Result.__dataclass_params__.frozen is True

    def test_initial_state_signature_has_no_not_equals_parameter(self):
        """Step 2's not-equals half belongs to propagate (Task 3); initial_state's
        signature must not carry a not_equals parameter that would let someone
        thread it through here instead."""
        params = inspect.signature(initial_state).parameters
        assert list(params) == ["model", "index", "fixed", "min_score"]
        assert params["min_score"].default == 0


class TestMaskCountsByMinScore:
    """tuple(index.count(m) for m in word_masks) by min_score policy -- the task-1
    brief's first normative table, all three rows."""

    def test_constant_zero(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        counts = tuple(bitset_index.count(m) for m in state.word_masks)
        assert counts == MASK_COUNTS_MIN_SCORE_0

    def test_constant_thirty(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=30)
        counts = tuple(bitset_index.count(m) for m in state.word_masks)
        assert counts == MASK_COUNTS_MIN_SCORE_30

    def test_callable_varying_by_length(self, model, bitset_index):
        """The edge case the brief names explicitly: a callable min_score that
        varies across the three lengths present (3, 4, 5) in FIX-A."""
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=_length_dependent_min_score)
        counts = tuple(bitset_index.count(m) for m in state.word_masks)
        assert counts == MASK_COUNTS_CALLABLE


class TestOpenFixedClassification:
    """Open/fixed classification and mask contents -- FIX-A, min_score=0. Every row
    of the task-1 brief's second normative table, one test per row."""

    def test_all_empty_fixed_slot_0_is_open_with_all_nine_length_3_words(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert pattern(model, 0, EMPTY_FIXED) == "???"
        assert state.word_masks[0] is not None
        assert bitset_index.words(3, state.word_masks[0]) == CANONICAL_LENGTH_3

    def test_ear_fixed_slot_0_is_fixed(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "EAR"
        assert state.word_masks[0] is None

    def test_ear_fixed_slot_5_is_open_with_exactly_ear(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 5, fixed) == "E??"
        assert state.word_masks[5] is not None
        assert bitset_index.words(3, state.word_masks[5]) == [("EAR", 40)]

    def test_ear_fixed_slot_6_is_open_with_an_empty_mask(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 6, fixed) == "A???"
        assert state.word_masks[6] is not None
        assert bitset_index.count(state.word_masks[6]) == 0

    def test_off_list_xyz_fixed_slot_0_is_still_fixed(self, model, bitset_index):
        """A fixed slot is fixed by pattern shape alone -- being off the word list
        entirely does not reclassify it as open."""
        fixed = _fixed_with({0: "X", 1: "Y", 2: "Z"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "XYZ"
        assert state.word_masks[0] is None

    def test_partial_x_fixed_slot_0_is_open_with_an_empty_mask_no_exception(self, model, bitset_index):
        """C1 contract: a pattern with a letter outside the alphabet degrades to an
        all-zero mask, never an exception -- even though the slot is open (because
        '?' is still present) and 'X' is not in this fixture's alphabet."""
        fixed = _fixed_with({0: "X"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "X??"
        assert state.word_masks[0] is not None
        assert bitset_index.count(state.word_masks[0]) == 0


class TestWordMasksParallelToSlots:
    """word_masks is parallel to model.slots: len matches, and index s is slot id s."""

    def test_length_equals_number_of_slots(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert len(state.word_masks) == len(model.slots) == 10

    def test_length_equals_number_of_slots_with_some_fixed(self, model, bitset_index):
        """Same invariant with a fixed tuple that turns some slots fixed (None) --
        the list must stay the full length, not shrink to only the open slots."""
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert len(state.word_masks) == len(model.slots) == 10

    def test_none_positions_match_pattern_based_classification(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        for slot in model.slots:
            is_open = "?" in pattern(model, slot.id, fixed)
            assert (state.word_masks[slot.id] is not None) == is_open


class TestCellLetters:
    """cell_letters on FIX-A, all-empty fixed, min_score=0 -- the task-1 brief's
    third normative table."""

    def test_matches_normative_table(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        actual = tuple(_letters_string(bits, bitset_index) for bits in state.cell_letters)
        assert actual == CELL_LETTERS_TABLE

    def test_dtype_and_shape(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert state.cell_letters.dtype == np.uint64
        assert state.cell_letters.shape == (FIXTURE_SIZE * FIXTURE_SIZE,)

    def test_black_cells_are_zero(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        for cell in FIXTURE_BLACKS:
            assert int(state.cell_letters[cell]) == 0

    def test_unslotted_cell_is_zero(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert int(state.cell_letters[20]) == 0


class TestCellLettersDecision15Precedence:
    """Decision 15's precedence, exercised only by this case: FIX-A with
    fixed[20] = 'A' and nothing else. Cell 20 is white, in no slot in either
    direction, and in model.unslotted -- the ratified reading is that unslotted
    beats a fixed letter there."""

    def test_unslotted_wins_over_the_fixed_letter(self, model, bitset_index):
        fixed = _fixed_with({20: "A"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        assert int(state.cell_letters[20]) == 0

    def test_word_masks_are_identical_to_the_all_empty_fixed_case(self, model, bitset_index):
        baseline = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        fixed = _fixed_with({20: "A"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        for baseline_mask, mask in zip(baseline.word_masks, state.word_masks):
            if baseline_mask is None:
                assert mask is None
            else:
                assert np.array_equal(baseline_mask, mask)


class TestDomainStateFields:
    """model and fixed are carried straight through, not copied or rebuilt."""

    def test_model_and_fixed_are_carried_through(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert state.model is model
        assert state.fixed == EMPTY_FIXED
