"""
Tests for src.domain.propagator (Task 1: dataclasses/initial_state; Task 2:
arc-consistency refine/propagate with not_equals=False; Task 3: the
not-equals rule live under not_equals=True; Task 4: crossing_counts, the
last public name in the module).

Fixture is FIX-A, the 5x5 grid pinned by global-constraints.md (blacks at
cell indices 3, 8, 15, 21; one unslotted cell, 20) together with
FIXTURE_WORDS, the same file's 14-word list. Both are transcribed verbatim
from that file, and every literal table below is transcribed from the
task briefs' normative tables -- which the briefs state were taken by
running the real oracles against this fixture, not hand-derived. Cross-
checked independently against the real LetterBitsetIndex/SlotModel/pattern
(and, for Task 2, a hand-run AC-3 loop and a brute-force enumerator) before
writing: running the brief's own rules against FIX-A reproduces every value
below exactly.

Task 2 additionally cross-checks against two independent oracles that never
call anything in src.domain.propagator: a brute-force complete-fill
enumerator (test-local, using only pattern/index.words/index.mask) and the
existing CSP AC-3 in src.fill.autofill.Autofill, run directly against a real
Grid rather than through fill().

Task 3 adds three further geometries -- FIX-B, FIX-G, FIX-H (plus an
off-list variant of FIX-H's own geometry) -- each built with
SlotModel.from_blacks per the task-3 brief, and reuses Task 2's
_brute_force_fills/_states_equal/_natural_queue harnesses rather than
duplicating them. Every Revision comparison in this file's Task-3 tests is
a field-by-field predicate over the integer fields, never `in`, `==`, or
`set()` against a Revision or a Result: both are frozen dataclasses over a
NumPy array, so those operators raise once a mask spans more than one
uint64 chunk -- FIXTURE_WORDS never produces that, but the predicate form
is written to hold regardless.

TestConfluenceWithNotEqualsCascade below adds one more geometry and its
own small word list (CASCADE_WORDS): FIXTURE_WORDS' 14 words over a
10-letter alphabet turned out too dense for a fixture where the not-equals
phase both fires on a real crossing and re-enqueues it -- every attempt
either collapsed straight to an empty domain or cascaded to a full wipe
before a second, uncrossed slot could show a distinct fixed point. That
class documents why CASCADE_WORDS exists rather than reusing FIXTURE_WORDS.

Task 4's crossing_counts tests build initial_state directly and never call
refine or propagate -- the brief's contract is unpropagated by design.
TestCrossingCountsAgainstPlacementImpactOracle differentially checks one
normative row against analyze_placement_impact, and stops there: the
brief explicitly forbids extending that oracle to the fixed-crossing or
off-list-fixed-word rows, since the analyzer counts fixed crossings and
reports a phantom elimination for an off-list fixed word. Those two rows
use the brief's hand-built values instead, like every other Task-4 row.
"""

from __future__ import annotations

import dataclasses
import inspect
import random
import typing
from pathlib import Path
from typing import Callable

import numpy as np
import pytest
from src.core.constraint_analyzer import analyze_placement_impact
from src.core.grid import Grid
from src.domain.letter_bitset import LetterBitsetIndex
from src.domain.propagator import (
    DomainState,
    MinScore,
    Result,
    Revision,
    _refine,
    crossing_counts,
    initial_state,
    propagate,
    refine,
)
from src.domain.slot_model import SlotModel, pattern
from src.fill.autofill import Autofill
from src.fill.trie_pattern_matcher import TriePatternMatcher
from src.fill.word_list import WordList

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPREHENSIVE_WORDLIST = REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"

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

# Text-only view of the same set (task-3 tests build a fixed-length-3 target
# set and then subtract/compare, where the score half is irrelevant).
CANONICAL_LENGTH_3_WORDS = {text for text, _ in CANONICAL_LENGTH_3}

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

# (row, col) black positions equivalent to FIXTURE_BLACKS, for building a real
# Grid the Autofill._ac3 oracle needs -- from global-constraints.md's FIX-A.
FIXTURE_BLACK_POSITIONS = ((0, 3), (1, 3), (3, 0), (4, 1))

# Task-2 brief's normative fixed point on FIX-A, all-empty fixed, min_score=0,
# not_equals=False -- words per slot, in canonical ((-score, text)) order.
FIXED_POINT_WORDS = {
    0: ("PET", "SET"),
    1: ("EAR", "PAR"),
    2: ("ARISE",),
    3: ("NEAR",),
    4: ("SPY",),
    5: ("PEA", "SEA", "SPA"),
    6: ("EARN",),
    7: ("TRIES",),
    8: ("SAP",),
    9: ("EVERY",),
}

# cell_letters at that same fixed point, as letter strings ("" for 0) --
# literal, from the task-2 brief's normative table. Flat, cell = row * 5 + col.
CELL_LETTERS_FIXED_POINT = (
    "PS", "E", "T", "", "E",
    "EP", "A", "R", "", "V",
    "A", "R", "I", "S", "E",
    "", "N", "E", "A", "R",
    "", "", "S", "P", "Y",
)  # fmt: skip

# FIX-C: SlotModel.from_blacks(5, [4,5,6,7,8,9,14,15,16,17,18,19,24], min_length=3)
# -- three isolated length-4 across slots, no crossings (task-2 brief).
FIX_C_BLACKS = (4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 19, 24)

# FIX-B, the twins (task-3 brief): two isolated length-3 across slots (cells
# 0-2 and 10-12), no crossings.
FIX_B_BLACKS = (3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24)

# FIX-G/FIX-H share this geometry (task-3 brief): three isolated length-3
# across slots (cells 0-2, 10-12, 20-22), no crossings. FIX-G leaves slot 0
# open (a singleton via step 5); FIX-H fixes it outright (step 2 instead).
FIX_G_BLACKS = (3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18, 19, 23, 24)


@pytest.fixture(scope="module")
def fixture_word_list() -> WordList:
    return WordList(list(FIXTURE_WORDS))


@pytest.fixture(scope="module")
def bitset_index(fixture_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(fixture_word_list)


@pytest.fixture(scope="module")
def model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIXTURE_BLACKS, min_length=3)


@pytest.fixture(scope="module")
def fix_b_model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIX_B_BLACKS, min_length=3)


@pytest.fixture(scope="module")
def fix_g_model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIX_G_BLACKS, min_length=3)


def _new_fix_a_grid() -> Grid:
    """A fresh, unfilled FIX-A Grid -- fresh per call since the Autofill
    oracle tests fill letters into it, and a module-scoped fixture would
    leak one test's letters into the next."""
    grid = Grid(FIXTURE_SIZE, validate_size=False)
    for row, col in FIXTURE_BLACK_POSITIONS:
        grid.set_black_square(row, col, enforce_symmetry=False)
    return grid


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


class TestDomainStateEquality:
    """Decision 16 (spec 0.1.8, section 7): DomainState.__eq__ replaces the
    dataclass-generated one, which raises ValueError the moment it reaches a
    field whose array holds more than one element. Every test below is one
    row of the task-1 brief's normative table. States that must differ in
    exactly one field are built directly through the DomainState
    constructor -- initial_state's four fields always move together, so it
    cannot isolate a single field the way these tests need to."""

    def test_declares_eq_false(self):
        assert DomainState.__dataclass_params__.eq is False

    def test_two_states_from_the_same_inputs_are_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert a == b

    def test_differing_only_in_model_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        other_model = dataclasses.replace(model, size=model.size + 1)
        b = DomainState(model=other_model, word_masks=a.word_masks, cell_letters=a.cell_letters, fixed=a.fixed)
        assert a != b

    def test_differing_only_in_fixed_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        other_fixed = _fixed_with({0: "Z"})
        b = DomainState(model=a.model, word_masks=a.word_masks, cell_letters=a.cell_letters, fixed=other_fixed)
        assert a != b

    def test_differing_only_in_cell_letters_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        other_cell_letters = a.cell_letters.copy()
        other_cell_letters[0] ^= np.uint64(1)
        b = DomainState(model=a.model, word_masks=a.word_masks, cell_letters=other_cell_letters, fixed=a.fixed)
        assert a != b

    def test_differing_only_in_word_masks_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        other_masks = list(a.word_masks)
        assert other_masks[0] is not None  # slot 0 is open under EMPTY_FIXED
        other_masks[0] = other_masks[0] ^ np.uint64(1)
        b = DomainState(model=a.model, word_masks=other_masks, cell_letters=a.cell_letters, fixed=a.fixed)
        assert a != b

    def test_one_word_masks_entry_none_other_an_array_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        other_masks = list(a.word_masks)
        assert other_masks[0] is not None  # slot 0 is open under EMPTY_FIXED
        other_masks[0] = None
        b = DomainState(model=a.model, word_masks=other_masks, cell_letters=a.cell_letters, fixed=a.fixed)
        assert a != b

    def test_both_word_masks_none_at_the_same_slot_all_else_equal_is_equal(self, model, bitset_index):
        """Built via two separate initial_state calls, not by sharing one
        closed slot's None by reference, so this genuinely exercises the
        pairwise both-None branch rather than short-circuiting on identity."""
        fixed = _fixed_with({0: "P", 1: "E", 2: "T"})  # closes slot 0: no wildcard left
        a = initial_state(model, bitset_index, fixed, min_score=0)
        b = initial_state(model, bitset_index, fixed, min_score=0)
        assert a.word_masks[0] is None and b.word_masks[0] is None
        assert a == b

    def test_word_masks_of_different_length_is_not_equal(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = DomainState(model=a.model, word_masks=a.word_masks[:-1], cell_letters=a.cell_letters, fixed=a.fixed)
        assert a != b

    def test_not_equal_to_a_non_domain_state(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert a.__eq__(object()) is NotImplemented
        assert (a == object()) is False
        assert (a != object()) is True

    def test_hash_is_none(self):
        assert DomainState.__hash__ is None

    def test_hash_raises_type_error_naming_domain_state(self, model, bitset_index):
        a = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        with pytest.raises(TypeError, match="DomainState"):
            hash(a)


def _states_equal(a: DomainState, b: DomainState) -> bool:
    """Confluence/idempotence predicate, written independently of
    DomainState.__eq__ (decision 16) so these tests do not check the
    propagator's fixed point with the propagator's own equality:
    model and fixed by ==, word_masks pairwise both-None or
    np.array_equal, cell_letters by np.array_equal."""
    if a.model != b.model or a.fixed != b.fixed:
        return False
    if len(a.word_masks) != len(b.word_masks):
        return False
    for mask_a, mask_b in zip(a.word_masks, b.word_masks):
        if mask_a is None or mask_b is None:
            if mask_a is not mask_b:
                return False
        elif not np.array_equal(mask_a, mask_b):
            return False
    return np.array_equal(a.cell_letters, b.cell_letters)


def _natural_queue(model: SlotModel, word_masks: list) -> list:
    """The task-2 brief's own definition of the natural queue, written
    independently here (not imported from propagator) so the test that
    checks refine builds this queue is not simply comparing the
    implementation to itself: indices into model.crossings, in order, of
    every crossing whose two slots are both open."""
    return [
        idx
        for idx, crossing in enumerate(model.crossings)
        if word_masks[crossing.across_id] is not None and word_masks[crossing.down_id] is not None
    ]


def _open_slot_ids(model: SlotModel, fixed: tuple) -> list:
    return [slot.id for slot in model.slots if "?" in pattern(model, slot.id, fixed)]


def _fixed_slot_texts_on_list(model: SlotModel, fixed: tuple, index: LetterBitsetIndex) -> set:
    """
    The on-list text of every fixed slot -- task-3's distinctness seed.

    A fixed slot's word is not available to any open slot either (FIX-H:
    slot 0 is fixed at SPY, which is on-list, so no brute-force fill may
    also place SPY at slot 1 or 2). Off-list fixed text (index.count == 0)
    contributes nothing, matching step 2's own "off the index removes
    nothing" rule.
    """
    texts = set()
    for slot in model.slots:
        slot_pattern = pattern(model, slot.id, fixed)
        if "?" in slot_pattern:
            continue
        if index.count(index.mask(slot_pattern, 0)) > 0:
            texts.add(slot_pattern)
    return texts


def _brute_force_fills(model: SlotModel, fixed: tuple, index: LetterBitsetIndex) -> list:
    """
    Exhaustive, propagator-independent oracle: every complete, consistent
    fill of model's open slots.

    Never calls refine/_refine/propagate/letters_at/restrict -- candidates
    for a slot of length L come from index.words(L, index.mask("?" * L, 0)),
    the brief's own scoping (the *raw* length-L pool, not that slot's own
    narrower pattern), and a hand-written filter re-applies both the slot's
    own fixed letters (via pattern) and cross-slot cell agreement by
    simulating a shared cell grid. A word already used by another slot in
    the same fill is rejected (distinctness) -- required so that "wiped
    non-empty implies zero solutions" is not falsified by a repeats-allowed
    reading (task-2 brief). Distinctness is seeded with every fixed slot's
    own on-list text before recursion starts (task-3): a fixed slot never
    appears in open_slots or candidates, so without this seed its word
    would be free for an open slot to reuse, which is exactly what the
    not-equals rule forbids (FIX-H).

    Returns a list of {slot_id: word} dicts, one per complete fill.
    """
    open_slots = [slot for slot in model.slots if slot.id in _open_slot_ids(model, fixed)]
    candidates = {
        slot.id: [text for text, _ in index.words(slot.length, index.mask("?" * slot.length, 0))] for slot in open_slots
    }
    patterns = {slot.id: pattern(model, slot.id, fixed) for slot in open_slots}
    seeded_used = _fixed_slot_texts_on_list(model, fixed, index)

    fills: list = []

    def backtrack(pos: int, assignment: dict, used: set, cell_values: dict) -> None:
        if pos == len(open_slots):
            fills.append(dict(assignment))
            return
        slot = open_slots[pos]
        slot_pattern = patterns[slot.id]
        for word in candidates[slot.id]:
            if word in used:
                continue
            if any(ch != "?" and word[i] != ch for i, ch in enumerate(slot_pattern)):
                continue
            new_cells = {}
            conflict = False
            for i, cell in enumerate(slot.cells):
                letter = word[i]
                if cell in cell_values:
                    if cell_values[cell] != letter:
                        conflict = True
                        break
                else:
                    new_cells[cell] = letter
            if conflict:
                continue
            assignment[slot.id] = word
            used.add(word)
            cell_values.update(new_cells)
            backtrack(pos + 1, assignment, used, cell_values)
            del assignment[slot.id]
            used.discard(word)
            for cell in new_cells:
                del cell_values[cell]

    backtrack(0, {}, set(seeded_used), {})
    return fills


class TestPropagateRefineContractShapes:
    """Structural guards on propagate/refine/_refine's signatures -- the
    contract itself, per the task brief."""

    def test_propagate_signature(self):
        params = inspect.signature(propagate).parameters
        assert list(params) == ["model", "index", "fixed", "min_score", "not_equals"]
        assert params["min_score"].default == 0
        assert params["not_equals"].default is True

    def test_refine_signature(self):
        params = inspect.signature(refine).parameters
        assert list(params) == ["state", "index", "min_score", "not_equals"]
        assert params["min_score"].default == 0
        assert params["not_equals"].default is True

    def test_private_refine_signature_has_no_defaults(self):
        """_refine is the seam decision 13 pins for the confluence test to
        vary queue order through -- every argument, including queue, is
        required rather than defaulted."""
        params = inspect.signature(_refine).parameters
        assert list(params) == ["state", "index", "min_score", "not_equals", "queue"]
        for name in params:
            assert params[name].default is inspect.Parameter.empty


class TestRefineBuildsTheNaturalQueue:
    """refine(state, ...) must call _refine with exactly the natural queue
    (decision 13).

    Comparing refine's *result* to a direct _refine(..., natural_queue) call
    cannot actually test this: confluence (proved separately, see
    TestConfluence) means any permutation of the same arc set returns an
    equal state, so refine could pass a reversed or shuffled queue and a
    result-only comparison would still pass. The only way to check what
    queue refine actually hands to _refine is to intercept the call itself,
    so the first test below monkeypatches the module's _refine with a spy
    that records its queue argument (and still delegates to the real one,
    so the run completes normally) rather than comparing outcomes."""

    def test_refine_calls_private_refine_with_the_natural_queue(self, model, bitset_index, monkeypatch):
        import src.domain.propagator as propagator_module

        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        real_refine = propagator_module._refine
        captured_queues = []

        def spy(state_arg, index_arg, min_score_arg, not_equals_arg, queue_arg):
            captured_queues.append(list(queue_arg))
            return real_refine(state_arg, index_arg, min_score_arg, not_equals_arg, queue_arg)

        monkeypatch.setattr(propagator_module, "_refine", spy)

        propagator_module.refine(state, bitset_index, min_score=0, not_equals=False)

        assert captured_queues == [_natural_queue(model, state.word_masks)]

    def test_natural_queue_on_fixa_all_open_is_every_crossing_in_order(self, model, bitset_index):
        """Sanity check on the fixture, not on refine: FIX-A with an
        all-empty fixed has every slot open, so this file's own
        _natural_queue helper -- the one the spy test above compares
        against -- is simply every crossing index in model.crossings
        order here."""
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        queue = _natural_queue(model, state.word_masks)
        assert queue == list(range(len(model.crossings)))


class TestNonMutation:
    """refine/_refine/propagate must not mutate their argument state or any
    array it holds (decision 13) -- non-vacuous only because we snapshot
    the caller's own arrays before the call and diff against that snapshot
    afterwards, not against the (possibly aliased) post-call state."""

    def test_original_state_and_arrays_are_unchanged_after_refine(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        mask_snapshots = [None if m is None else m.copy() for m in state.word_masks]
        cell_letters_snapshot = state.cell_letters.copy()

        result = refine(state, bitset_index, min_score=0, not_equals=False)

        assert result.state is not state
        assert result.state.word_masks is not state.word_masks
        assert result.state.cell_letters is not state.cell_letters
        for original, snapshot in zip(state.word_masks, mask_snapshots):
            if snapshot is None:
                assert original is None
            else:
                assert np.array_equal(original, snapshot)
        assert np.array_equal(state.cell_letters, cell_letters_snapshot)

    def test_first_results_state_is_unchanged_after_a_second_refine_call(self, model, bitset_index):
        """The same non-mutation guarantee must hold when a caller takes one
        refine's result state and feeds it into a second refine call
        directly (what propagate's own initial_state -> refine handoff, and
        Task 3's re-propagation-after-an-edit use case, both rely on)."""
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        first = refine(state, bitset_index, min_score=0, not_equals=False)
        snapshot = [None if m is None else m.copy() for m in first.state.word_masks]

        second = refine(first.state, bitset_index, min_score=0, not_equals=False)

        assert second.state is not first.state
        for original, snap in zip(first.state.word_masks, snapshot):
            if snap is None:
                assert original is None
            else:
                assert np.array_equal(original, snap)


class TestFixANormativeFixedPoint:
    """Task-2 brief's primary normative table: FIX-A, all-empty fixed,
    min_score=0, not_equals=False."""

    def test_wiped_is_empty(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        assert result.wiped == ()

    @pytest.mark.parametrize("slot_id", list(range(10)))
    def test_fixed_point_mask_matches_normative_table(self, model, bitset_index, slot_id):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        slot = model.slots[slot_id]
        words = tuple(text for text, _ in bitset_index.words(slot.length, result.state.word_masks[slot_id]))
        assert words == FIXED_POINT_WORDS[slot_id]

    def test_cell_letters_matches_normative_table(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        actual = tuple(_letters_string(bits, bitset_index) for bits in result.state.cell_letters)
        assert actual == CELL_LETTERS_FIXED_POINT

    def test_fixed_and_model_carried_through_on_the_result_state(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        assert result.state.model is model
        assert result.state.fixed == EMPTY_FIXED


class TestFixCWipeoutWithOpenRegionRemaining:
    """Task-2 brief's FIX-C: a wipeout in one region must not silently
    empty an unrelated, uncrossed open slot, and a fixed slot must never
    appear in wiped even when its (off-list) text would otherwise count."""

    @pytest.fixture
    def fix_c_model(self) -> SlotModel:
        return SlotModel.from_blacks(FIXTURE_SIZE, FIX_C_BLACKS, min_length=3)

    @pytest.fixture
    def fix_c_fixed(self) -> tuple:
        overrides = {10: "A", 11: "R", 12: "I", 13: "S", 20: "V"}
        return _fixed_with(overrides)

    def test_no_crossings_in_this_geometry(self, fix_c_model):
        """The property this fixture is built to exercise only holds because
        the three slots cannot influence one another through the arc queue."""
        assert fix_c_model.crossings == ()

    def test_slot_0_open_with_the_two_length_4_words(self, fix_c_model, fix_c_fixed, bitset_index):
        result = propagate(fix_c_model, bitset_index, fix_c_fixed, min_score=0, not_equals=False)
        assert pattern(fix_c_model, 0, fix_c_fixed) == "????"
        words = {text for text, _ in bitset_index.words(4, result.state.word_masks[0])}
        assert words == {"EARN", "NEAR"}

    def test_slot_1_is_fixed_off_list_and_never_wiped(self, fix_c_model, fix_c_fixed, bitset_index):
        result = propagate(fix_c_model, bitset_index, fix_c_fixed, min_score=0, not_equals=False)
        assert pattern(fix_c_model, 1, fix_c_fixed) == "ARIS"
        assert result.state.word_masks[1] is None
        assert 1 not in result.wiped

    def test_slot_2_open_and_empty(self, fix_c_model, fix_c_fixed, bitset_index):
        result = propagate(fix_c_model, bitset_index, fix_c_fixed, min_score=0, not_equals=False)
        assert pattern(fix_c_model, 2, fix_c_fixed) == "V???"
        assert result.state.word_masks[2] is not None
        assert bitset_index.count(result.state.word_masks[2]) == 0

    def test_wiped_is_exactly_slot_2(self, fix_c_model, fix_c_fixed, bitset_index):
        result = propagate(fix_c_model, bitset_index, fix_c_fixed, min_score=0, not_equals=False)
        assert result.wiped == (2,)


class TestConfluence:
    """The fixed point must not depend on arc-processing order (spec section
    7's uniqueness claim) -- natural order, its reverse, and a batch of
    seeded random shuffles of the same arc set must all agree, compared by
    the state-equality predicate. Only masks are compared; revision order is
    never asserted."""

    def test_natural_and_reverse_order_agree(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, False, queue)
        reversed_result = _refine(state, bitset_index, 0, False, list(reversed(queue)))

        assert _states_equal(natural.state, reversed_result.state)
        assert natural.wiped == reversed_result.wiped

    @pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
    def test_random_shuffles_agree_with_natural_order(self, model, bitset_index, seed):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, False, queue)
        shuffled = list(queue)
        random.Random(seed).shuffle(shuffled)
        shuffled_result = _refine(state, bitset_index, 0, False, shuffled)

        assert _states_equal(natural.state, shuffled_result.state)
        assert natural.wiped == shuffled_result.wiped

    def test_confluence_also_holds_on_a_partially_fixed_grid(self, model, bitset_index):
        """The same property, but on a state where propagation actually
        cascades to a wipeout (EAR fixed at cells 0-2) -- confluence must
        hold on a state that empties, not only on FIX-A's tight-but-nonempty
        fixed point."""
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, False, queue)
        shuffled = list(queue)
        random.Random(7).shuffle(shuffled)
        shuffled_result = _refine(state, bitset_index, 0, False, shuffled)

        assert _states_equal(natural.state, shuffled_result.state)
        assert natural.wiped == shuffled_result.wiped


class TestIdempotence:
    """refine on an already-arc-consistent state must return an equal state
    and no revisions -- non-vacuous only because refine/_refine do not
    mutate (TestNonMutation), so this is not comparing a state to itself by
    aliasing."""

    def test_refining_the_fixed_point_again_changes_nothing(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        again = refine(result.state, bitset_index, min_score=0, not_equals=False)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()
        assert again.wiped == result.wiped

    def test_idempotence_also_holds_at_a_wiped_out_fixed_point(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        result = propagate(model, bitset_index, fixed, min_score=0, not_equals=False)
        again = refine(result.state, bitset_index, min_score=0, not_equals=False)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()


class TestSupportAtFixedPoint:
    """At the fixed point, every crossing whose two slots are open must
    agree at the shared cell -- letters_at from one side equals letters_at
    from the other (spec section 7's support property)."""

    def test_every_open_open_crossing_agrees(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        state = result.state
        for crossing in model.crossings:
            mask_a = state.word_masks[crossing.across_id]
            mask_b = state.word_masks[crossing.down_id]
            if mask_a is None or mask_b is None:
                continue
            length_a = model.slots[crossing.across_id].length
            length_b = model.slots[crossing.down_id].length
            letters_a = bitset_index.letters_at(length_a, crossing.across_pos, mask_a)
            letters_b = bitset_index.letters_at(length_b, crossing.down_pos, mask_b)
            assert letters_a == letters_b


class TestSoundnessAgainstBruteForce:
    """Every word of every brute-force complete fill must survive in its
    slot's fixed-point mask, and a non-empty wiped must imply zero
    solutions -- checked both on FIX-A (tight, non-empty) and on a fixture
    that genuinely wipes, so the implication is exercised on both sides."""

    def test_fixa_yields_exactly_three_fills(self, model, bitset_index):
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        assert len(fills) == 3

    def test_fixa_every_fill_word_survives_in_its_slots_fixed_point_mask(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        assert fills, "expected at least one brute-force fill on FIX-A"
        for fill in fills:
            for slot_id, word in fill.items():
                slot = model.slots[slot_id]
                mask = result.state.word_masks[slot_id]
                words_in_mask = {text for text, _ in bitset_index.words(slot.length, mask)}
                assert word in words_in_mask

    def test_fixa_per_slot_solution_word_sets_match_the_normative_table(self, model, bitset_index):
        """FIX-A's arc consistency is exactly tight (task-2 brief): the union
        of solution words at each slot equals the whole fixed-point mask,
        not merely a subset of it."""
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        per_slot: dict = {}
        for fill in fills:
            for slot_id, word in fill.items():
                per_slot.setdefault(slot_id, set()).add(word)
        for slot_id, words in FIXED_POINT_WORDS.items():
            assert per_slot[slot_id] == set(words)

    def test_enumerator_rejects_a_fill_that_reuses_a_word(self, model, bitset_index):
        """The distinctness requirement itself: every fill the enumerator
        returns on FIX-A uses each word at most once."""
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        assert fills
        for fill in fills:
            words = list(fill.values())
            assert len(words) == len(set(words))

    def test_wipeout_fixture_has_zero_brute_force_solutions_and_a_nonempty_wiped(self, model, bitset_index):
        """Non-vacuous check of the other direction: EAR fixed at cells 0-2
        cascades to a real wipeout (independently confirmed), and the
        brute-force enumerator over the remaining open slots must agree
        there is no complete fill."""
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        result = propagate(model, bitset_index, fixed, min_score=0, not_equals=False)
        fills = _brute_force_fills(model, fixed, bitset_index)
        assert result.wiped != ()
        assert fills == []


class TestAc3Oracle:
    """Fixed point vs the existing AC-3 (Autofill._ac3/_revise), built per
    the task-2 brief: Autofill(grid, word_list, min_score=<int>), then
    _initialize_csp(grid.get_empty_slots()), then _ac3() -- no fill(), which
    would run the whole solver."""

    def test_sampling_threshold_is_not_crossed_on_fixa(self, fixture_word_list):
        """_initialize_csp would fall back to a non-deterministic stratified
        sample above 10000 raw candidates -- assert the inequality rather
        than assuming it."""
        grid = _new_fix_a_grid()
        matcher = TriePatternMatcher(fixture_word_list)
        largest = max(
            len(matcher.find(grid.get_pattern_for_slot(slot), 0, max_results=None)) for slot in grid.get_word_slots()
        )
        assert largest <= 10000

    def test_per_slot_domain_equality_on_blank_fixa(self, model, fixture_word_list, bitset_index):
        """Holds only when _ac3() returns True (task-2 brief's scoping) --
        confirmed True on a blank FIX-A below, before the comparison runs."""
        grid = _new_fix_a_grid()
        af = Autofill(grid, fixture_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        assert af._ac3() is True

        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        for slot in model.slots:
            expected = af.domains[af.slot_id_map[model.slot_key(slot.id)]]
            actual = {text for text, _ in bitset_index.words(slot.length, result.state.word_masks[slot.id])}
            assert actual == expected

    def test_wiped_or_not_agrees_on_a_blank_grid(self, model, fixture_word_list, bitset_index):
        grid = _new_fix_a_grid()
        af = Autofill(grid, fixture_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        ac3_result = af._ac3()

        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        assert bool(result.wiped) == (not ac3_result or af.has_empty_domain())
        assert bool(result.wiped) is False

    def test_wiped_or_not_agrees_with_ear_fixed_at_cells_0_to_2(self, model, fixture_word_list, bitset_index):
        grid = _new_fix_a_grid()
        grid.set_letter(0, 0, "E")
        grid.set_letter(0, 1, "A")
        grid.set_letter(0, 2, "R")
        af = Autofill(grid, fixture_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        ac3_result = af._ac3()

        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        result = propagate(model, bitset_index, fixed, min_score=0, not_equals=False)
        assert bool(result.wiped) == (not ac3_result or af.has_empty_domain())
        assert bool(result.wiped) is True

    def test_wiped_or_not_agrees_with_x_fixed_at_cell_0(self, model, fixture_word_list, bitset_index):
        grid = _new_fix_a_grid()
        grid.set_letter(0, 0, "X")
        af = Autofill(grid, fixture_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        ac3_result = af._ac3()

        fixed = _fixed_with({0: "X"})
        result = propagate(model, bitset_index, fixed, min_score=0, not_equals=False)
        assert bool(result.wiped) == (not ac3_result or af.has_empty_domain())
        assert bool(result.wiped) is True


@pytest.mark.slow
class TestRealWordListAgainstAc3:
    """One real-list run (spec section 11 marks C3 slow "when real-list
    runs"): data/wordlists/comprehensive.txt, FIX-A, not_equals=False, a
    constant int min_score, checked against the same Autofill oracle as
    TestAc3Oracle. Run explicitly: pytest cli/tests/unit/test_propagator.py
    -m slow -v -- pytest.ini deselects `slow` by default."""

    def test_threshold_and_per_slot_domain_equality_on_real_wordlist(self, model):
        assert COMPREHENSIVE_WORDLIST.is_file()
        real_word_list = WordList.from_file(str(COMPREHENSIVE_WORDLIST))
        real_index = LetterBitsetIndex.from_word_list(real_word_list)

        grid = _new_fix_a_grid()
        matcher = TriePatternMatcher(real_word_list)
        largest = max(
            len(matcher.find(grid.get_pattern_for_slot(slot), 0, max_results=None)) for slot in grid.get_word_slots()
        )
        assert largest <= 10000

        af = Autofill(grid, real_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        assert af._ac3() is True

        result = propagate(model, real_index, EMPTY_FIXED, min_score=0, not_equals=False)
        for slot in model.slots:
            expected = af.domains[af.slot_id_map[model.slot_key(slot.id)]]
            actual = {text for text, _ in real_index.words(slot.length, result.state.word_masks[slot.id])}
            assert actual == expected

    def test_fixed_letters_drive_real_removals_on_multi_chunk_masks(self, model):
        """The test above is a genuine C1 equivalence check at scale, but it
        propagates nothing: on a blank FIX-A the real list is already arc
        consistent, so both sides are no-ops and restrict/Revision/re-enqueue
        never run once on a multi-chunk mask. Fixing three letters makes them
        run. The same Autofill oracle still applies here only because _ac3()
        returns True -- it is a valid fixed-point oracle nowhere else."""
        assert COMPREHENSIVE_WORDLIST.is_file()
        real_word_list = WordList.from_file(str(COMPREHENSIVE_WORDLIST))
        real_index = LetterBitsetIndex.from_word_list(real_word_list)

        grid = _new_fix_a_grid()
        grid.set_letter(0, 0, "X")
        grid.set_letter(0, 1, "Y")
        grid.set_letter(0, 2, "L")
        af = Autofill(grid, real_word_list, min_score=0)
        af._initialize_csp(grid.get_empty_slots())
        assert af._ac3() is True

        fixed = _fixed_with({0: "X", 1: "Y", 2: "L"})
        result = propagate(model, real_index, fixed, min_score=0, not_equals=False)

        # The point of the test: revisions that actually narrowed masks wider
        # than one uint64 chunk, which the blank-grid case never produces.
        assert result.revisions
        assert all(result.state.word_masks[r.slot].shape[0] > 1 for r in result.revisions)
        assert all(real_index.count(r.removed) >= 1 for r in result.revisions)

        # Slot 0 is fixed by XYL, so it is closed and carries no mask; Autofill
        # was likewise seeded from get_empty_slots(), so neither side holds it.
        assert result.state.word_masks[0] is None
        for slot in model.slots:
            mask = result.state.word_masks[slot.id]
            if mask is None:
                continue
            expected = af.domains[af.slot_id_map[model.slot_key(slot.id)]]
            actual = {text for text, _ in real_index.words(slot.length, mask)}
            assert actual == expected

    def test_fixed_word_removal_clears_a_real_list_word_from_its_same_length_slots(self, model):
        """not_equals=True has no multi-chunk coverage anywhere else on this
        branch. CAT fixed at cells 0-2 closes slot 0 on a word that is on the
        real list, so step 2's fixed-word removal must strike CAT from every
        open same-length slot -- an exact, falsifiable claim about which word
        leaves which slots, on masks many chunks wide. This is step 2, not
        step 5: slot 0 is closed, so it is never a singleton source."""
        assert COMPREHENSIVE_WORDLIST.is_file()
        real_word_list = WordList.from_file(str(COMPREHENSIVE_WORDLIST))
        real_index = LetterBitsetIndex.from_word_list(real_word_list)
        fixed = _fixed_with({0: "C", 1: "A", 2: "T"})

        def words_at(result, slot_id):
            slot = model.slots[slot_id]
            return {text for text, _ in real_index.words(slot.length, result.state.word_masks[slot_id])}

        off = propagate(model, real_index, fixed, min_score=0, not_equals=False)
        on = propagate(model, real_index, fixed, min_score=0, not_equals=True)

        assert on.state.word_masks[0] is None, "slot 0 is closed by CAT, so it holds no mask"
        target_slots = [1, 4, 5, 8]
        for slot_id in target_slots:
            assert on.state.word_masks[slot_id].shape[0] > 1
            assert "CAT" in words_at(off, slot_id)
            assert words_at(off, slot_id) - words_at(on, slot_id) == {"CAT"}

        phase_revisions = [r for r in on.revisions if r.source_crossing == -1]
        assert {r.slot for r in phase_revisions} == set(target_slots)
        assert all(r.source_slot == 0 for r in phase_revisions)
        assert not any(r.source_crossing == -1 for r in off.revisions)


@pytest.mark.slow
class TestDomainStateEqualityRealWordList:
    """The task-1 brief's mask-width criterion: DomainState.__eq__ must not
    raise regardless of how many uint64 chunks a mask spans.
    data/wordlists/comprehensive.txt on FIX-A produces open-slot masks wider
    than the single chunk FIXTURE_WORDS' 14 words fit in, unlike every other
    equality test in this file. Run explicitly: pytest
    cli/tests/unit/test_propagator.py -m slow -v -- pytest.ini deselects
    `slow` by default."""

    def test_two_states_from_the_same_real_wordlist_inputs_are_equal(self, model):
        assert COMPREHENSIVE_WORDLIST.is_file()
        real_word_list = WordList.from_file(str(COMPREHENSIVE_WORDLIST))
        real_index = LetterBitsetIndex.from_word_list(real_word_list)

        a = initial_state(model, real_index, EMPTY_FIXED, min_score=0)
        b = initial_state(model, real_index, EMPTY_FIXED, min_score=0)
        assert any(
            mask is not None and mask.shape[0] > 1 for mask in a.word_masks
        ), "fixture must actually exercise a multi-chunk mask"
        assert a == b

    def test_a_real_wordlist_state_is_not_equal_to_a_differently_fixed_one(self, model):
        assert COMPREHENSIVE_WORDLIST.is_file()
        real_word_list = WordList.from_file(str(COMPREHENSIVE_WORDLIST))
        real_index = LetterBitsetIndex.from_word_list(real_word_list)

        a = initial_state(model, real_index, EMPTY_FIXED, min_score=0)
        b = initial_state(model, real_index, _fixed_with({0: "C", 1: "A", 2: "T"}), min_score=0)
        assert a != b


class TestRevisionFieldsAreConsistent:
    """No normative table pins individual Revision values (only masks,
    wiped and cell_letters are asserted against exact tables), but every
    Revision refine/_refine records must still describe a real edge in
    model.crossings and a genuine, non-empty removal -- checked here so a
    swapped source_slot/slot or a spurious no-op revision would be caught
    even though nothing above happens to exercise it."""

    def test_every_revision_on_fixa_names_a_real_crossing_between_its_two_slots(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        assert result.revisions, "expected at least one revision propagating FIX-A to its fixed point"
        for revision in result.revisions:
            # not_equals=False runs no phase, so every revision must name a real arc.
            # Without this, source_crossing == -1 would index the LAST crossing and
            # compare against the wrong one instead of failing.
            assert revision.source_crossing >= 0
            crossing = model.crossings[revision.source_crossing]
            assert {crossing.across_id, crossing.down_id} == {revision.slot, revision.source_slot}
            assert revision.slot != revision.source_slot

    def test_every_revision_on_fixa_actually_removed_at_least_one_word(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        for revision in result.revisions:
            assert bitset_index.count(revision.removed) >= 1


class TestFixBTwins:
    """FIX-B, the twins (task-3 brief) -- two isolated length-3 slots, no
    crossings, both patterns "?PY" and both masks the singleton {SPY}
    under not_equals=False. Both settings from the brief's table."""

    @pytest.fixture
    def fix_b_fixed(self) -> tuple:
        return _fixed_with({1: "P", 2: "Y", 11: "P", 12: "Y"})

    def test_no_crossings_in_this_geometry(self, fix_b_model):
        assert fix_b_model.crossings == ()

    def test_both_patterns_are_py(self, fix_b_model, fix_b_fixed):
        assert pattern(fix_b_model, 0, fix_b_fixed) == "?PY"
        assert pattern(fix_b_model, 1, fix_b_fixed) == "?PY"

    def test_not_equals_false_both_slots_keep_spy(self, fix_b_model, bitset_index, fix_b_fixed):
        result = propagate(fix_b_model, bitset_index, fix_b_fixed, min_score=0, not_equals=False)
        assert bitset_index.words(3, result.state.word_masks[0]) == [("SPY", 20)]
        assert bitset_index.words(3, result.state.word_masks[1]) == [("SPY", 20)]
        assert result.wiped == ()

    def test_not_equals_true_both_slots_wipe(self, fix_b_model, bitset_index, fix_b_fixed):
        result = propagate(fix_b_model, bitset_index, fix_b_fixed, min_score=0, not_equals=True)
        assert bitset_index.count(result.state.word_masks[0]) == 0
        assert bitset_index.count(result.state.word_masks[1]) == 0
        assert result.wiped == (0, 1)

    def test_not_equals_true_records_a_revision_for_each_side(self, fix_b_model, bitset_index, fix_b_fixed):
        """Each slot clears the other -- two Revisions, one per direction
        (spec section 7 step 5: 'two same-length slots holding the same
        singleton clear each other and both wipe'). Presence, never
        position: never compare a Revision with ==/in/set()."""
        result = propagate(fix_b_model, bitset_index, fix_b_fixed, min_score=0, not_equals=True)
        assert any(r.source_crossing == -1 and r.source_slot == 1 and r.slot == 0 for r in result.revisions)
        assert any(r.source_crossing == -1 and r.source_slot == 0 and r.slot == 1 for r in result.revisions)


class TestFixGGentleCase:
    """FIX-G (task-3 brief) -- the rule removes without collapsing. Slot
    0's own pattern is already the singleton {SPY} (no crossing needed),
    and step 5 clears SPY from slots 1 and 2 without wiping either."""

    @pytest.fixture
    def fix_g_fixed(self) -> tuple:
        return _fixed_with({1: "P", 2: "Y", 10: "S"})

    def test_no_crossings_in_this_geometry(self, fix_g_model):
        assert fix_g_model.crossings == ()

    def test_patterns_match_the_table(self, fix_g_model, fix_g_fixed):
        assert pattern(fix_g_model, 0, fix_g_fixed) == "?PY"
        assert pattern(fix_g_model, 1, fix_g_fixed) == "S??"
        assert pattern(fix_g_model, 2, fix_g_fixed) == "???"

    def test_slot_0_is_open_not_fixed(self, fix_g_model, bitset_index, fix_g_fixed):
        """Open, since '?' is still present -- this is exactly what makes
        it a singleton the step-5 phase can see, unlike FIX-H's slot 0."""
        state = initial_state(fix_g_model, bitset_index, fix_g_fixed, min_score=0)
        assert state.word_masks[0] is not None

    def test_not_equals_false_row(self, fix_g_model, bitset_index, fix_g_fixed):
        result = propagate(fix_g_model, bitset_index, fix_g_fixed, min_score=0, not_equals=False)
        assert bitset_index.words(3, result.state.word_masks[0]) == [("SPY", 20)]
        words_1 = {t for t, _ in bitset_index.words(3, result.state.word_masks[1])}
        words_2 = {t for t, _ in bitset_index.words(3, result.state.word_masks[2])}
        assert words_1 == {"SEA", "SPA", "SET", "SAP", "SPY"}
        assert words_2 == set(CANONICAL_LENGTH_3_WORDS)
        assert result.wiped == ()

    def test_not_equals_true_row(self, fix_g_model, bitset_index, fix_g_fixed):
        result = propagate(fix_g_model, bitset_index, fix_g_fixed, min_score=0, not_equals=True)
        assert bitset_index.words(3, result.state.word_masks[0]) == [("SPY", 20)]
        words_1 = {t for t, _ in bitset_index.words(3, result.state.word_masks[1])}
        words_2 = {t for t, _ in bitset_index.words(3, result.state.word_masks[2])}
        assert words_1 == {"SEA", "SPA", "SET", "SAP"}
        assert words_2 == set(CANONICAL_LENGTH_3_WORDS) - {"SPY"}
        assert result.wiped == ()

    def test_not_equals_true_revisions_are_sourced_from_slot_0(self, fix_g_model, bitset_index, fix_g_fixed):
        result = propagate(fix_g_model, bitset_index, fix_g_fixed, min_score=0, not_equals=True)
        assert any(r.source_crossing == -1 and r.source_slot == 0 and r.slot == 1 for r in result.revisions)
        assert any(r.source_crossing == -1 and r.source_slot == 0 and r.slot == 2 for r in result.revisions)


class TestFixHStepTwoDiscriminator:
    """FIX-H (task-3 brief) -- same geometry as FIX-G, but slot 0 is fully
    fixed at SPY rather than an open singleton, so identical removals on
    slots 1/2 must come from step 2, not step 5. The brief is explicit
    that testing only FIX-G or only FIX-H cannot tell the two rules apart
    -- see TestFixGAndFixHProduceIdenticalRemovalsByDifferentRules below
    for the direct side-by-side comparison."""

    @pytest.fixture
    def fix_h_fixed(self) -> tuple:
        return _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})

    def test_slot_0_pattern_is_fully_fixed(self, fix_g_model, fix_h_fixed):
        assert pattern(fix_g_model, 0, fix_h_fixed) == "SPY"

    def test_slot_0_word_mask_is_none_not_a_singleton_step_5_can_see(self, fix_g_model, bitset_index, fix_h_fixed):
        state = initial_state(fix_g_model, bitset_index, fix_h_fixed, min_score=0)
        assert state.word_masks[0] is None

    def test_not_equals_false_leaves_1_and_2_at_the_full_domains(self, fix_g_model, bitset_index, fix_h_fixed):
        result = propagate(fix_g_model, bitset_index, fix_h_fixed, min_score=0, not_equals=False)
        words_1 = {t for t, _ in bitset_index.words(3, result.state.word_masks[1])}
        words_2 = {t for t, _ in bitset_index.words(3, result.state.word_masks[2])}
        assert words_1 == {"SEA", "SPA", "SET", "SAP", "SPY"}
        assert words_2 == set(CANONICAL_LENGTH_3_WORDS)
        assert result.wiped == ()

    def test_not_equals_true_row(self, fix_g_model, bitset_index, fix_h_fixed):
        result = propagate(fix_g_model, bitset_index, fix_h_fixed, min_score=0, not_equals=True)
        assert result.state.word_masks[0] is None
        words_1 = {t for t, _ in bitset_index.words(3, result.state.word_masks[1])}
        words_2 = {t for t, _ in bitset_index.words(3, result.state.word_masks[2])}
        assert words_1 == {"SEA", "SPA", "SET", "SAP"}
        assert words_2 == set(CANONICAL_LENGTH_3_WORDS) - {"SPY"}
        assert result.wiped == ()

    def test_revision_present_for_slot_1_sourced_from_the_fixed_slot(self, fix_g_model, bitset_index, fix_h_fixed):
        """The task's own presence check: source_crossing == -1 and
        source_slot == 0 (the fixed slot) for slot 1, asserted by
        presence, never position."""
        result = propagate(fix_g_model, bitset_index, fix_h_fixed, min_score=0, not_equals=True)
        assert any(r.source_crossing == -1 and r.source_slot == 0 and r.slot == 1 for r in result.revisions)

    def test_revision_present_for_slot_2_sourced_from_the_fixed_slot(self, fix_g_model, bitset_index, fix_h_fixed):
        result = propagate(fix_g_model, bitset_index, fix_h_fixed, min_score=0, not_equals=True)
        assert any(r.source_crossing == -1 and r.source_slot == 0 and r.slot == 2 for r in result.revisions)


class TestFixGAndFixHProduceIdenticalRemovalsByDifferentRules:
    """The task-3 brief's discriminator point, made explicit as its own
    comparison: FIX-G's step-5 removal and FIX-H's step-2 removal land on
    the same final masks for slots 1 and 2, even though slot 0 is open in
    one and fixed in the other."""

    def test_slot_1_masks_are_equal(self, fix_g_model, bitset_index):
        fixed_g = _fixed_with({1: "P", 2: "Y", 10: "S"})
        fixed_h = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        result_g = propagate(fix_g_model, bitset_index, fixed_g, min_score=0, not_equals=True)
        result_h = propagate(fix_g_model, bitset_index, fixed_h, min_score=0, not_equals=True)
        assert np.array_equal(result_g.state.word_masks[1], result_h.state.word_masks[1])

    def test_slot_2_masks_are_equal(self, fix_g_model, bitset_index):
        fixed_g = _fixed_with({1: "P", 2: "Y", 10: "S"})
        fixed_h = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        result_g = propagate(fix_g_model, bitset_index, fixed_g, min_score=0, not_equals=True)
        result_h = propagate(fix_g_model, bitset_index, fixed_h, min_score=0, not_equals=True)
        assert np.array_equal(result_g.state.word_masks[2], result_h.state.word_masks[2])


class TestOffListContrastOnFixHGeometry:
    """The off-list contrast (task-3 brief) -- FIX-H's own geometry, but
    slot 0's fixed text is XYZ: X and Z are outside FIXTURE_WORDS' alphabet
    (AEINPRSTVY), so slot 0 is still fixed (no wildcard) but off-list.
    Step 2 removes nothing; both settings leave slots 1/2 at their
    not_equals=False values."""

    @pytest.fixture
    def off_list_fixed(self) -> tuple:
        return _fixed_with({0: "X", 1: "Y", 2: "Z", 10: "S"})

    def test_slot_0_is_fixed_and_off_list(self, fix_g_model, bitset_index, off_list_fixed):
        assert pattern(fix_g_model, 0, off_list_fixed) == "XYZ"
        state = initial_state(fix_g_model, bitset_index, off_list_fixed, min_score=0)
        assert state.word_masks[0] is None
        assert bitset_index.count(bitset_index.mask("XYZ", 0)) == 0

    def test_not_equals_true_leaves_1_and_2_unchanged(self, fix_g_model, bitset_index, off_list_fixed):
        result = propagate(fix_g_model, bitset_index, off_list_fixed, min_score=0, not_equals=True)
        words_1 = {t for t, _ in bitset_index.words(3, result.state.word_masks[1])}
        words_2 = {t for t, _ in bitset_index.words(3, result.state.word_masks[2])}
        assert words_1 == {"SEA", "SPA", "SET", "SAP", "SPY"}
        assert words_2 == set(CANONICAL_LENGTH_3_WORDS)

    def test_no_not_equals_revisions_are_produced(self, fix_g_model, bitset_index, off_list_fixed):
        result = propagate(fix_g_model, bitset_index, off_list_fixed, min_score=0, not_equals=True)
        assert not any(r.source_crossing == -1 for r in result.revisions)


class TestPartialEntryFlipWithNotEqualsDefault:
    """The partial-entry flip (spec section 7 [NOTE], FIX-A), re-run
    through propagate's not_equals=True default: fixing only cell 0 to X
    keeps slot 0 open with an empty mask (0 in wiped); completing to XYZ
    makes it fixed (0 not in wiped). Correct behaviour, not a defect --
    Task 1 pinned this at the initial_state level; this re-pins it at
    propagate's new default so a not-equals regression could not silently
    flip which side of the boundary either fixed tuple lands on."""

    def test_partial_x_leaves_slot_0_open_and_wiped(self, model, bitset_index):
        fixed = _fixed_with({0: "X"})
        result = propagate(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "X??"
        assert result.state.word_masks[0] is not None
        assert 0 in result.wiped

    def test_complete_xyz_makes_slot_0_fixed_and_excludes_it_from_wiped(self, model, bitset_index):
        fixed = _fixed_with({0: "X", 1: "Y", 2: "Z"})
        result = propagate(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "XYZ"
        assert result.state.word_masks[0] is None
        assert 0 not in result.wiped


class TestConfluenceWithNotEquals:
    """Confluence (task-3 brief's property list), now with not_equals=True
    -- the same permutation harness as Task 2's TestConfluence, reused
    rather than duplicated, on both FIX-A scenarios that class covers.
    Independently confirmed before writing this file: neither scenario's
    not_equals=False fixed point has a same-length singleton collision
    (FIX-A's own singletons -- ARISE/TRIES/EVERY at length 5, NEAR/EARN at
    length 4, SPY/SAP at length 3 -- are already pairwise distinct), so
    this exercises the phase loop under queue permutation without itself
    triggering a removal; FIX-B/FIX-G/FIX-H above and TestIdempotence-
    WithNotEquals below cover cases where the rule does remove something."""

    def test_natural_and_reverse_order_agree(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, True, queue)
        reversed_result = _refine(state, bitset_index, 0, True, list(reversed(queue)))

        assert _states_equal(natural.state, reversed_result.state)
        assert natural.wiped == reversed_result.wiped

    @pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
    def test_random_shuffles_agree_with_natural_order(self, model, bitset_index, seed):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, True, queue)
        shuffled = list(queue)
        random.Random(seed).shuffle(shuffled)
        shuffled_result = _refine(state, bitset_index, 0, True, shuffled)

        assert _states_equal(natural.state, shuffled_result.state)
        assert natural.wiped == shuffled_result.wiped

    def test_confluence_also_holds_on_a_partially_fixed_grid_that_cascades(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        state = initial_state(model, bitset_index, fixed, min_score=0)
        queue = _natural_queue(model, state.word_masks)

        natural = _refine(state, bitset_index, 0, True, queue)
        shuffled = list(queue)
        random.Random(7).shuffle(shuffled)
        shuffled_result = _refine(state, bitset_index, 0, True, shuffled)

        assert _states_equal(natural.state, shuffled_result.state)
        assert natural.wiped == shuffled_result.wiped


# CASCADE_WORDS -- a supplementary, length-3-only word list scoped to
# TestConfluenceWithNotEqualsCascade below, used instead of FIXTURE_WORDS
# because FIXTURE_WORDS' 14 words over a 10-letter alphabet leave no room
# to arrange a fixture where the not-equals phase both fires on a real
# crossing and re-enqueues it without the whole grid collapsing to an
# empty domain or cascading to a full wipe (independently confirmed before
# writing this class): every letter and word below is chosen so each
# slot's own local pattern picks out an exact, disjoint candidate set from
# the other slots' local patterns, so the propagation path the class
# docstring describes is the only one the word list can produce.
CASCADE_WORDS = [
    ("CAT", 50),
    ("BAT", 50),
    ("CIG", 50),
    ("BIG", 50),
    ("TOP", 50),
    ("TUB", 50),
    ("DEN", 50),
    ("FEZ", 50),
    ("FOX", 50),
    ("NOR", 50),
]

CASCADE_SIZE = 7

# Open cells of an isolated singleton slot (0-2), a fully open bystander
# slot (4-6) that exists only so the mutation-sensitivity mechanism below
# has a same-length slot to remove a word from, an across slot crossing
# two down slots at row 2 cols 0-2, and a second, independent across/down
# trio at row 2 cols 4-6 -- see the class docstring for what each one is
# for. Blacks are every other cell of the CASCADE_SIZE x CASCADE_SIZE grid.
_CASCADE_OPEN_CELLS = frozenset({0, 1, 2, 4, 5, 6, 14, 15, 16, 18, 19, 20, 21, 28, 23, 30, 25, 32, 27, 34})
CASCADE_BLACKS = tuple(cell for cell in range(CASCADE_SIZE * CASCADE_SIZE) if cell not in _CASCADE_OPEN_CELLS)


@pytest.fixture(scope="module")
def cascade_word_list() -> WordList:
    return WordList(list(CASCADE_WORDS))


@pytest.fixture(scope="module")
def cascade_index(cascade_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(cascade_word_list)


@pytest.fixture(scope="module")
def cascade_model() -> SlotModel:
    return SlotModel.from_blacks(CASCADE_SIZE, CASCADE_BLACKS, min_length=3)


@pytest.fixture
def cascade_fixed() -> tuple:
    """
    Pins every slot's pattern (global-constraints.md / spec section 2's
    cell-index rule): slot 0 -> "CA?" (the singleton source, CAT); slot 1 -> "???" (the
    bystander target, fully open); slot 2 -> "?A?" (the direct not-equals
    target, CAT/BAT); slot 3 -> "?E?" (the pivot, DEN/FEZ); slot 4 -> "?I?"
    (the downstream slot, CIG/BIG); slot 5 -> "???" (the untouched slot,
    crosses slot 2's other cell); slot 6 -> "?OX" (FOX, one pivot anchor);
    slot 7 -> "?OR" (NOR, the other). Cell numbers are literal, verified
    against SlotModel.from_blacks(CASCADE_SIZE, CASCADE_BLACKS) directly
    rather than derived by hand.
    """
    empty = tuple("" for _ in range(CASCADE_SIZE * CASCADE_SIZE))
    overrides = {0: "C", 1: "A", 15: "A", 19: "E", 21: "I", 25: "O", 32: "X", 27: "O", 34: "R"}
    fixed = list(empty)
    for cell, letter in overrides.items():
        fixed[cell] = letter
    return tuple(fixed)


class TestConfluenceWithNotEqualsCascade:
    """
    Closes the evidentiary gap the task-3 review flagged: every other
    confluence test in this file either has zero crossings (FIX-B/FIX-G/
    FIX-H) or has crossings but never actually triggers the not-equals
    phase (FIX-A, whose own singletons are already pairwise distinct at
    the arc-consistent fixed point). Nothing in that set exercises the
    phase-then-re-enqueue branch at propagator.py's step-5 handling
    (`for slot_id in changed_slots: _enqueue_other_crossings(...)`).

    cascade_model has 8 slots, all length 3, over two independent
    components:

    - Slot 0 is isolated and already a singleton (CAT) at initial_state --
      no crossing needed to produce it. Slot 2 is a direct not-equals
      target: it starts at {CAT, BAT} and crosses slot 4 at one cell and
      slot 5 at the other. Arc consistency alone (not_equals=False) leaves
      slot 2 untouched (both its letters are already present on both
      sides of each crossing), so the CAT/BAT split survives to the
      not_equals=False fixed point. Only the not-equals phase, once slot 0
      is collected as a singleton, removes CAT from slot 2 (a
      source_crossing=-1 Revision) -- and that removal is what the phase
      itself re-enqueues: slot 2's crossing with slot 4 is reprocessed,
      and slot 4 -- never a direct target of the phase, no Revision on it
      ever carries source_crossing=-1 -- loses a candidate through that
      real arc, ending at a different fixed point than not_equals=False
      leaves it at. Slot 5 crosses slot 2 too, and ordinary arc consistency
      does reduce it -- through a real crossing revision, under both
      settings alike -- so slot 5's fixed point is identical with the rule
      on and off. That is what makes it a control for the phase's cascade
      specifically; it is not a claim that nothing touches slot 5.

    - Slots 3, 6, 7 are a second, independent trio: slot 3 starts at
      {DEN, FEZ} and crosses slot 6 (a singleton, FOX) at one cell and
      slot 7 (a singleton, NOR) at the other. Both crossings remove one of
      slot 3's two candidates, so slot 3 (and, transitively, slots 6/7)
      reach an empty mask at the true, order-independent arc-consistent
      fixed point regardless of which crossing is processed first -- but
      on the way there, slot 3 passes through a transient singleton (FEZ
      if slot 3-slot 6's crossing is processed first, DEN if slot 3-slot
      7's is processed first). Slot 1 is fully open and same-length, so it
      holds both DEN and FEZ as candidates going in. A correct
      implementation never lets this transience leak out (slot 3 is empty,
      not a singleton, by the time the phase legitimately runs, so it is
      never treated as a source), which is exactly why every confluence
      assertion below must hold; the "prove it can fail" step in the task
      report interleaves the phase into the arc loop instead and shows
      slot 1 ending up missing FEZ xor DEN depending on processing order.

    Every value below comes from running propagate/_refine against
    cascade_model/cascade_index/cascade_fixed, not from hand-computation.
    """

    DOWNSTREAM = 4

    def test_patterns_match_cascade_fixed_s_docstring(self, cascade_model, cascade_fixed):
        """Pins the slot-role mapping the class docstring and DOWNSTREAM
        rely on against cascade_model's actual slot order -- a guard
        against a from_blacks ordering change silently retargeting which
        slot id is "the downstream one", the way FIX-B/FIX-G/FIX-H each
        pin their own patterns."""
        expected = {0: "CA?", 1: "???", 2: "?A?", 3: "?E?", 4: "?I?", 5: "???", 6: "?OX", 7: "?OR"}
        for slot_id, expected_pattern in expected.items():
            assert pattern(cascade_model, slot_id, cascade_fixed) == expected_pattern

    def test_geometry_has_real_crossings(self, cascade_model):
        assert len(cascade_model.crossings) > 0

    def test_phase_produces_at_least_one_direct_removal(self, cascade_model, cascade_index, cascade_fixed):
        result = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=True)
        assert any(r.source_crossing == -1 for r in result.revisions)

    def test_downstream_slot_is_never_a_direct_target_of_the_phase(self, cascade_model, cascade_index, cascade_fixed):
        result = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=True)
        assert not any(r.slot == self.DOWNSTREAM and r.source_crossing == -1 for r in result.revisions)

    def test_downstream_slot_has_a_real_crossing_revision(self, cascade_model, cascade_index, cascade_fixed):
        """The cascade itself: a Revision on the downstream slot whose
        source_crossing is a real arc index, produced only because the
        phase's own removal on slot 2 re-enqueued slot 2's crossing with
        this slot -- and that Revision does not appear at all under
        not_equals=False, confirming _refine's post-phase re-enqueue branch
        (dead in every other test in this file) is what produces it. Named
        by symbol, not by line: the previous citation here was a line
        number that the very next commit invalidated."""
        result_true = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=True)
        result_false = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=False)
        assert any(r.slot == self.DOWNSTREAM and r.source_crossing != -1 for r in result_true.revisions)
        assert not any(r.slot == self.DOWNSTREAM for r in result_false.revisions)

    def test_downstream_slot_fixed_point_differs_from_not_equals_false(self, cascade_model, cascade_index, cascade_fixed):
        result_true = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=True)
        result_false = propagate(cascade_model, cascade_index, cascade_fixed, min_score=0, not_equals=False)
        assert not np.array_equal(
            result_true.state.word_masks[self.DOWNSTREAM], result_false.state.word_masks[self.DOWNSTREAM]
        )

    def test_natural_and_reverse_order_agree(self, cascade_model, cascade_index, cascade_fixed):
        state = initial_state(cascade_model, cascade_index, cascade_fixed, min_score=0)
        queue = _natural_queue(cascade_model, state.word_masks)

        natural = _refine(state, cascade_index, 0, True, queue)
        reversed_result = _refine(state, cascade_index, 0, True, list(reversed(queue)))

        assert _states_equal(natural.state, reversed_result.state)
        assert natural.wiped == reversed_result.wiped

    @pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
    def test_random_shuffles_agree_with_natural_order(self, cascade_model, cascade_index, cascade_fixed, seed):
        state = initial_state(cascade_model, cascade_index, cascade_fixed, min_score=0)
        queue = _natural_queue(cascade_model, state.word_masks)

        natural = _refine(state, cascade_index, 0, True, queue)
        shuffled = list(queue)
        random.Random(seed).shuffle(shuffled)
        shuffled_result = _refine(state, cascade_index, 0, True, shuffled)

        assert _states_equal(natural.state, shuffled_result.state)
        assert natural.wiped == shuffled_result.wiped


class TestNotEqualsPhaseRunsOnlyAtArcConsistentPoints:
    """Structural guard against the exact anti-pattern the task-3 brief
    warns against ('do not optimise it into the loop'): every masks
    snapshot the not-equals phase actually sees must already satisfy the
    arc-consistency support property (every open-open crossing agrees at
    its shared cell -- the same property TestSupportAtFixedPoint checks
    at the very end, checked here at every intermediate phase call too).
    If the phase were interleaved into step 4's loop instead of run only
    once that loop drains, some crossing would still be unprocessed at an
    intermediate call and this would catch the disagreement."""

    def test_every_phase_call_on_fixa_sees_full_arc_support(self, model, bitset_index, monkeypatch):
        import src.domain.propagator as propagator_module

        snapshots = []
        real_phase = propagator_module._singleton_not_equals_phase

        def spy(model_arg, index_arg, masks_arg):
            snapshots.append(list(masks_arg))
            return real_phase(model_arg, index_arg, masks_arg)

        monkeypatch.setattr(propagator_module, "_singleton_not_equals_phase", spy)

        propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=True)

        assert snapshots, "expected the not-equals phase to run at least once on FIX-A"
        for masks in snapshots:
            for crossing in model.crossings:
                mask_a = masks[crossing.across_id]
                mask_b = masks[crossing.down_id]
                if mask_a is None or mask_b is None:
                    continue
                length_a = model.slots[crossing.across_id].length
                length_b = model.slots[crossing.down_id].length
                letters_a = bitset_index.letters_at(length_a, crossing.across_pos, mask_a)
                letters_b = bitset_index.letters_at(length_b, crossing.down_pos, mask_b)
                assert letters_a == letters_b


class TestIdempotenceWithNotEquals:
    """Idempotence (task-3 brief's property list), now with not_equals=True,
    across FIX-A's own fixed point, FIX-A's wiped-out cascade, and the
    three not-equals fixtures where the rule actually removed something
    the first time through."""

    def test_fixa_baseline(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=True)
        again = refine(result.state, bitset_index, min_score=0, not_equals=True)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()

    def test_fixa_wiped_out_cascade(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        result = propagate(model, bitset_index, fixed, min_score=0, not_equals=True)
        again = refine(result.state, bitset_index, min_score=0, not_equals=True)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()

    def test_fix_b(self, fix_b_model, bitset_index):
        fixed = _fixed_with({1: "P", 2: "Y", 11: "P", 12: "Y"})
        result = propagate(fix_b_model, bitset_index, fixed, min_score=0, not_equals=True)
        again = refine(result.state, bitset_index, min_score=0, not_equals=True)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()

    def test_fix_g(self, fix_g_model, bitset_index):
        fixed = _fixed_with({1: "P", 2: "Y", 10: "S"})
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        again = refine(result.state, bitset_index, min_score=0, not_equals=True)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()

    def test_fix_h(self, fix_g_model, bitset_index):
        fixed = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        again = refine(result.state, bitset_index, min_score=0, not_equals=True)
        assert _states_equal(again.state, result.state)
        assert again.revisions == ()


class TestSoundnessAgainstBruteForceWithNotEquals:
    """Soundness (task-3 brief's property list) against brute force with
    not_equals=True -- FIX-A (where the rule fires but removes nothing
    extra, independently confirmed above) and FIX-G/FIX-H (where it does),
    using the corrected _brute_force_fills that seeds distinctness with
    fixed slots' own on-list text. Necessary on FIX-H: slot 0 is fixed at
    SPY, an on-list word, and without the seed the enumerator would
    happily place SPY at slot 1 or 2 too, which not_equals=True's fixed
    point (correctly) never allows."""

    def test_fixa_every_fill_word_survives(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=True)
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        assert fills, "expected at least one brute-force fill on FIX-A"
        for fill in fills:
            for slot_id, word in fill.items():
                slot = model.slots[slot_id]
                mask = result.state.word_masks[slot_id]
                words_in_mask = {text for text, _ in bitset_index.words(slot.length, mask)}
                assert word in words_in_mask

    def test_fix_b_has_zero_brute_force_solutions_matching_its_nonempty_wiped(self, fix_b_model, bitset_index):
        fixed = _fixed_with({1: "P", 2: "Y", 11: "P", 12: "Y"})
        result = propagate(fix_b_model, bitset_index, fixed, min_score=0, not_equals=True)
        fills = _brute_force_fills(fix_b_model, fixed, bitset_index)
        assert result.wiped != ()
        assert fills == []

    def test_fix_h_every_fill_word_survives_and_never_reuses_the_fixed_word(self, fix_g_model, bitset_index):
        fixed = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        fills = _brute_force_fills(fix_g_model, fixed, bitset_index)
        assert fills, "expected at least one brute-force fill on FIX-H's open slots"
        for fill in fills:
            assert "SPY" not in fill.values()
            for slot_id, word in fill.items():
                slot = fix_g_model.slots[slot_id]
                mask = result.state.word_masks[slot_id]
                words_in_mask = {text for text, _ in bitset_index.words(slot.length, mask)}
                assert word in words_in_mask

    def test_fix_g_every_fill_word_survives(self, fix_g_model, bitset_index):
        fixed = _fixed_with({1: "P", 2: "Y", 10: "S"})
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        fills = _brute_force_fills(fix_g_model, fixed, bitset_index)
        assert fills, "expected at least one brute-force fill on FIX-G's open slots"
        for fill in fills:
            for slot_id, word in fill.items():
                slot = fix_g_model.slots[slot_id]
                mask = result.state.word_masks[slot_id]
                words_in_mask = {text for text, _ in bitset_index.words(slot.length, mask)}
                assert word in words_in_mask


class TestCrossingCountsContractShape:
    """Structural guard on the last public name the module exports (task-4 brief)."""

    def test_signature(self):
        params = inspect.signature(crossing_counts).parameters
        assert list(params) == ["state", "index", "slot_id", "word"]


class TestCrossingCountsNormativeCases:
    """Task-4 brief's normative table, verbatim: FIX-A, all-empty fixed,
    min_score=0, evaluated on initial_state (unpropagated) -- crossing_counts
    reads a state, it does not propagate, so every case here builds
    initial_state directly and never calls refine or propagate."""

    def test_slot_2_arise(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert crossing_counts(state, bitset_index, 2, "ARISE") == (3, 1, 2, 5, 1)

    def test_slot_2_zrise_out_of_alphabet_letter_contributes_zero_not_raise(self, model, bitset_index):
        """Z is outside AEINPRSTVY -- the brief's own note on this row."""
        assert "Z" not in bitset_index.alphabet
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert crossing_counts(state, bitset_index, 2, "ZRISE") == (0, 1, 2, 5, 1)

    def test_slot_7_tries(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert crossing_counts(state, bitset_index, 7, "TRIES") == (2, 2, 2, 1, 5)

    def test_slot_2_word_too_short_raises_with_exact_message(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        with pytest.raises(ValueError) as exc_info:
            crossing_counts(state, bitset_index, 2, "SPY")
        assert str(exc_info.value) == "word 'SPY' has length 3; slot 2 has length 5"

    def test_slot_2_word_too_long_raises_with_exact_message(self, model, bitset_index):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        with pytest.raises(ValueError) as exc_info:
            crossing_counts(state, bitset_index, 2, "ARISEN")
        assert str(exc_info.value) == "word 'ARISEN' has length 6; slot 2 has length 5"

    def test_length_guard_raises_before_any_crossing_is_walked(self, model, bitset_index, monkeypatch):
        """The brief: 'Before any crossing is walked, len(word) != ... raises'
        -- guarded here by making LetterBitsetIndex.restrict itself fail the
        test if the implementation ever reaches the crossing loop before
        raising. Patched on the class (not the module-scoped bitset_index
        instance) so monkeypatch's teardown removes it cleanly."""
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("restrict must not run before the length guard raises")

        monkeypatch.setattr(LetterBitsetIndex, "restrict", fail_if_called)
        with pytest.raises(ValueError):
            crossing_counts(state, bitset_index, 2, "SPY")

    def test_slot_2_arise_with_fixed_crossing_omitted_not_zero_padded(self, model, bitset_index):
        """fixed[0]="S", fixed[5]="P", fixed[10]="A" fixes slot 5 (down,
        cells 0/5/10) to SPA, so the cell-10 crossing (slot 2 <-> slot 5) is
        omitted -- the tuple has 4 entries, not 5 with a 0 standing in for it."""
        fixed = _fixed_with({0: "S", 5: "P", 10: "A"})
        assert pattern(model, 5, fixed) == "SPA"  # confirms slot 5 is fixed, not still open
        state = initial_state(model, bitset_index, fixed, min_score=0)

        result = crossing_counts(state, bitset_index, 2, "ARISE")

        assert result == (1, 2, 5, 1)
        assert len(result) == 4  # shorter than slot 2's 5 crossings, not zero-padded to 5


class TestCrossingCountsAgainstPlacementImpactOracle:
    """The brief's differential oracle: on initial_state with no placed
    words and no fixed crossing slots, each entry equals the `after` count
    analyze_placement_impact reports for the corresponding crossing slot,
    reordered into model.crossings' by-cell order. The brief pins this for
    crossing_counts(s, index, 2, "ARISE") only, and explicitly forbids
    extending it to the fixed-crossing or off-list-fixed-word rows (the
    analyzer counts fixed crossings and reports a phantom elimination for
    an off-list fixed word) -- those two rows stay hand-built, above."""

    def test_slot_2_arise_matches_the_analyzers_after_counts_reordered(self, model, bitset_index, fixture_word_list):
        state = initial_state(model, bitset_index, EMPTY_FIXED, min_score=0)
        actual = crossing_counts(state, bitset_index, 2, "ARISE")

        grid = _new_fix_a_grid()
        slot = model.slots[2]
        slot_dict = {"row": slot.row, "col": slot.col, "direction": slot.direction, "length": slot.length}
        matcher = TriePatternMatcher(fixture_word_list)
        impact = analyze_placement_impact(grid, "ARISE", slot_dict, fixture_word_list, matcher)

        expected = []
        for crossing in model.crossings:
            if crossing.across_id != 2:
                continue
            row, col, direction = model.slot_key(crossing.down_id)
            expected.append(impact["impacts"][f"{row},{col},{direction}"]["after"])

        assert actual == tuple(expected) == (3, 1, 2, 5, 1)
