"""
Tests for src.domain.propagator (Task 1: dataclasses/initial_state; Task 2:
arc-consistency refine/propagate with not_equals=False).

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
from src.core.grid import Grid
from src.domain.letter_bitset import LetterBitsetIndex
from src.domain.propagator import DomainState, MinScore, Result, Revision, _refine, initial_state, propagate, refine
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


@pytest.fixture(scope="module")
def fixture_word_list() -> WordList:
    return WordList(list(FIXTURE_WORDS))


@pytest.fixture(scope="module")
def bitset_index(fixture_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(fixture_word_list)


@pytest.fixture(scope="module")
def model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIXTURE_BLACKS, min_length=3)


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


def _states_equal(a: DomainState, b: DomainState) -> bool:
    """Task-2 brief's state-equality predicate: DomainState holds NumPy
    arrays, so plain == raises -- model and fixed compare by ==, word_masks
    pairwise both-None or np.array_equal, cell_letters by np.array_equal."""
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
    reading (task-2 brief).

    Returns a list of {slot_id: word} dicts, one per complete fill.
    """
    open_slots = [slot for slot in model.slots if slot.id in _open_slot_ids(model, fixed)]
    candidates = {
        slot.id: [text for text, _ in index.words(slot.length, index.mask("?" * slot.length, 0))] for slot in open_slots
    }
    patterns = {slot.id: pattern(model, slot.id, fixed) for slot in open_slots}

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

    backtrack(0, {}, set(), {})
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

    def test_fixa_nonempty_wiped_would_imply_zero_solutions(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        fills = _brute_force_fills(model, EMPTY_FIXED, bitset_index)
        if result.wiped:
            assert fills == []

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
            crossing = model.crossings[revision.source_crossing]
            assert {crossing.across_id, crossing.down_id} == {revision.slot, revision.source_slot}
            assert revision.slot != revision.source_slot

    def test_every_revision_on_fixa_actually_removed_at_least_one_word(self, model, bitset_index):
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0, not_equals=False)
        for revision in result.revisions:
            assert bitset_index.count(revision.removed) >= 1
