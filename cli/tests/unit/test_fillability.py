"""
Tests for src.domain.fillability: FillabilityReport and assess() (C4), built
on the merged C3 propagator (src.domain.propagator).

Fixture is FIX-A, the same 5x5 grid and 14-word FIXTURE_WORDS as
test_propagator.py (blacks at cell indices 3, 8, 15, 21; one unslotted
cell, 20). There is no conftest.py under cli/tests and this file does not
add one -- test_propagator.py's own docstring notes this repo duplicates
fixtures per test module rather than sharing one, and fixture_word_list/
bitset_index/model already exist in both test_propagator.py and
test_letter_bitset.py. This file follows the same convention: every
constant and fixture below is transcribed from test_propagator.py, not
imported from it.

FIX-C (three isolated length-4 across slots, no crossings) and the FIX-G
geometry (three isolated length-3 across slots, no crossings) are copied
the same way, for the off_list_fixed tests decision 19 is about: a fixed
slot's word can be on-list or off-list independent of any open slot's own
domain, which is what an uncrossed geometry isolates cleanly and FIX-A's
crossing-heavy one does not.
"""

from __future__ import annotations

import dataclasses
import inspect

import numpy as np
import pytest
from src.domain.fillability import FillabilityReport, assess
from src.domain.letter_bitset import LetterBitsetIndex
from src.domain.propagator import propagate
from src.domain.slot_model import SlotModel, pattern
from src.fill.word_list import WordList

FIXTURE_SIZE = 5
FIXTURE_BLACKS = (3, 8, 15, 21)

# (text, score) -- literal, transcribed from test_propagator.py's FIXTURE_WORDS
# (itself transcribed from global-constraints.md).
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

EMPTY_FIXED = tuple("" for _ in range(FIXTURE_SIZE * FIXTURE_SIZE))


def _fixed_with(overrides: dict) -> tuple:
    """EMPTY_FIXED with a handful of cells overridden -- the rest stay unfixed."""
    fixed = list(EMPTY_FIXED)
    for cell, letter in overrides.items():
        fixed[cell] = letter
    return tuple(fixed)


# FIX-C (test_propagator.py): three isolated length-4 across slots (cells
# 0-3, 10-13, 20-23), no crossings.
FIX_C_BLACKS = (4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 19, 24)

# FIX-G geometry (test_propagator.py): three isolated length-3 across slots
# (cells 0-2, 10-12, 20-22), no crossings.
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
def fix_c_model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIX_C_BLACKS, min_length=3)


@pytest.fixture(scope="module")
def fix_g_model() -> SlotModel:
    return SlotModel.from_blacks(FIXTURE_SIZE, FIX_G_BLACKS, min_length=3)


class TestContractShapes:
    """FillabilityReport's dataclass shape is the contract itself (spec
    section 8's literal class body), so pin it directly -- mirrors
    TestContractShapes in test_propagator.py. The exact five-name field
    list is also decision 18's negative test: unslotted_cells is not a
    field."""

    def test_fields_are_exactly_the_five_in_the_spec(self):
        assert [f.name for f in dataclasses.fields(FillabilityReport)] == [
            "refuted",
            "wiped_slots",
            "domain_sizes",
            "cell_letters",
            "off_list_fixed",
        ]

    def test_frozen_but_eq_false(self):
        assert FillabilityReport.__dataclass_params__.frozen is True
        assert FillabilityReport.__dataclass_params__.eq is False

    def test_eq_is_defined_in_the_class_body(self):
        """Decision 16: bare eq=False with no __eq__ leaves object identity
        __hash__ in place -- explicitly rejected. __eq__ must be an explicit
        member of this class, not inherited from object."""
        assert "__eq__" in FillabilityReport.__dict__

    def test_hash_is_none(self):
        assert FillabilityReport.__hash__ is None

    def test_assess_signature(self):
        params = inspect.signature(assess).parameters
        assert list(params) == ["model", "index", "fixed", "min_score"]
        assert params["min_score"].default == 0


class TestEquality:
    """Mirrors Result.__eq__'s own tests: equal iff every plain field
    compares == and cell_letters compares np.array_equal."""

    def test_equal_reports_compare_equal(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert a == b

    def test_differing_refuted_are_unequal(self, model, bitset_index):
        """Isolated via dataclasses.replace -- every other field held fixed
        -- rather than two independently-assessed reports that would also
        differ in wiped_slots, domain_sizes and cell_letters at once and so
        pin nothing about __eq__'s own refuted branch specifically."""
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = dataclasses.replace(a, refuted=not a.refuted)
        assert a != b

    def test_differing_wiped_slots_are_unequal(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = dataclasses.replace(a, wiped_slots=a.wiped_slots + (0,))
        assert a != b

    def test_differing_domain_sizes_are_unequal(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = dataclasses.replace(a, domain_sizes=tuple(0 for _ in a.domain_sizes))
        assert a != b

    def test_differing_cell_letters_are_unequal(self, model, bitset_index):
        """cell_letters is the field the dataclass-generated __eq__ could
        not even reach (decision 16) -- two reports differing only there
        must still compare unequal through the explicit __eq__."""
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = dataclasses.replace(a, cell_letters=np.zeros_like(a.cell_letters))
        assert a != b

    def test_differing_off_list_fixed_are_unequal(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        b = dataclasses.replace(a, off_list_fixed=(0,))
        assert a != b

    def test_not_equal_to_a_non_report(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert a != object()

    def test_unhashable_because_hash_is_none(self, model, bitset_index):
        a = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        with pytest.raises(TypeError):
            {a}


class TestRefutedAndWipedSlots:
    """refuted = bool(result.wiped); wiped_slots = result.wiped verbatim
    (spec section 8: 'assess is propagate plus a report')."""

    def test_not_refuted_on_the_empty_grid(self, model, bitset_index):
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert report.refuted is False
        assert report.wiped_slots == ()

    def test_refuted_and_wiped_slots_match_propagate_on_a_cascading_wipeout(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        report = assess(model, bitset_index, fixed, min_score=0)
        result = propagate(model, bitset_index, fixed, min_score=0)
        assert report.refuted is True
        assert report.wiped_slots == result.wiped
        assert report.wiped_slots != ()

    def test_wiped_slots_matches_propagate_on_the_empty_grid(self, model, bitset_index):
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert report.wiped_slots == result.wiped


class TestDomainSizes:
    """Parallel to slots: -1 for a fixed slot, index.count(mask) at the
    fixed point for an open one."""

    def test_fixed_slot_is_minus_one(self, fix_c_model, bitset_index):
        fixed = _fixed_with({10: "N", 11: "E", 12: "A", 13: "R"})
        report = assess(fix_c_model, bitset_index, fixed, min_score=0)
        assert pattern(fix_c_model, 1, fixed) == "NEAR"
        assert report.domain_sizes[1] == -1

    def test_open_slot_matches_the_fixed_point_count(self, model, bitset_index):
        """FIX-A's empty grid does not wipe anything (TestRefutedAndWipedSlots),
        so every open slot's domain is nonzero at the fixed point."""
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert report.domain_sizes[0] == bitset_index.count(result.state.word_masks[0])
        assert report.domain_sizes[0] > 0

    def test_domain_sizes_parallel_to_all_slots(self, model, bitset_index):
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert len(report.domain_sizes) == len(model.slots)


class TestCellLetters:
    """cell_letters is carried through from propagate's own Result
    unchanged (module docstring)."""

    def test_matches_propagate_state_cell_letters_on_the_empty_grid(self, model, bitset_index):
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        result = propagate(model, bitset_index, EMPTY_FIXED, min_score=0)
        assert np.array_equal(report.cell_letters, result.state.cell_letters)

    def test_matches_on_a_cascading_wipeout_too(self, model, bitset_index):
        fixed = _fixed_with({0: "E", 1: "A", 2: "R"})
        report = assess(model, bitset_index, fixed, min_score=0)
        result = propagate(model, bitset_index, fixed, min_score=0)
        assert np.array_equal(report.cell_letters, result.state.cell_letters)


class TestOffListFixed:
    """Decision 19: membership alone, independent of min_score (trap 1); an
    out-of-alphabet fixed letter is off-list, never an exception (trap 3)."""

    def test_open_slot_is_never_in_off_list_fixed(self, model, bitset_index):
        report = assess(model, bitset_index, EMPTY_FIXED, min_score=0)
        for slot in model.slots:
            if report.domain_sizes[slot.id] != -1:  # open
                assert slot.id not in report.off_list_fixed

    def test_fixed_off_list_word_with_out_of_alphabet_letters(self, fix_g_model, bitset_index):
        """XYZ: X and Z are outside FIXTURE_WORDS' alphabet (AEINPRSTVY).
        index.mask must not raise (trap 3) -- count 0, reported here."""
        fixed = _fixed_with({0: "X", 1: "Y", 2: "Z", 10: "S"})
        report = assess(fix_g_model, bitset_index, fixed, min_score=0)
        assert pattern(fix_g_model, 0, fixed) == "XYZ"
        assert 0 in report.off_list_fixed

    def test_fixed_on_list_word_is_absent_from_off_list_fixed(self, fix_g_model, bitset_index):
        fixed = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        report = assess(fix_g_model, bitset_index, fixed, min_score=0)
        assert pattern(fix_g_model, 0, fixed) == "SPY"
        assert 0 not in report.off_list_fixed

    def test_fixed_on_list_word_scoring_below_a_nonzero_floor_stays_on_list(self, fix_c_model, bitset_index):
        """Trap 1, and this file's mutation-gate target: membership is
        decided at score floor 0, independent of min_score. NEAR scores 50;
        min_score=99 is above every score in FIXTURE_WORDS (nothing would
        pass a 99 floor), yet the fixed slot's own on-list word must not be
        reported as off-list."""
        fixed = _fixed_with({10: "N", 11: "E", 12: "A", 13: "R"})
        report = assess(fix_c_model, bitset_index, fixed, min_score=99)
        assert pattern(fix_c_model, 1, fixed) == "NEAR"
        assert 1 not in report.off_list_fixed

    def test_fix_c_slot_1_off_list_and_never_wiped(self, fix_c_model, bitset_index):
        """FIX-C (test_propagator.py's TestFixCWipeoutWithOpenRegionRemaining):
        slot 1 fixed to ARIS, off-list, never in wiped_slots regardless."""
        fixed = _fixed_with({10: "A", 11: "R", 12: "I", 13: "S", 20: "V"})
        report = assess(fix_c_model, bitset_index, fixed, min_score=0)
        assert pattern(fix_c_model, 1, fixed) == "ARIS"
        assert 1 in report.off_list_fixed
        assert 1 not in report.wiped_slots


class TestPartialEntryFlip:
    """spec section 7's [NOTE] (FIX-A, test_propagator.py's
    TestPartialEntryFlipWithNotEqualsDefault): a partially typed off-list
    entry wipes while partial and clears -- becomes fixed -- the instant its
    last letter lands. Correct behaviour, not a defect; asserted in both
    directions."""

    def test_partial_x_is_open_wiped_and_not_off_list(self, model, bitset_index):
        fixed = _fixed_with({0: "X"})
        report = assess(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "X??"
        assert report.domain_sizes[0] != -1  # still open
        assert 0 in report.wiped_slots
        assert 0 not in report.off_list_fixed

    def test_complete_xyz_is_fixed_not_wiped_and_off_list(self, model, bitset_index):
        fixed = _fixed_with({0: "X", 1: "Y", 2: "Z"})
        report = assess(model, bitset_index, fixed, min_score=0)
        assert pattern(model, 0, fixed) == "XYZ"
        assert report.domain_sizes[0] == -1  # fixed now
        assert 0 not in report.wiped_slots
        assert 0 in report.off_list_fixed


class TestOffListFixedAgreesWithC3StepTwo:
    """Oracle test (trap 2): off_list_fixed must not be derived by calling
    propagator._fixed_word_removals or reusing its loop -- that function only
    runs when not_equals=True. Pin agreement behaviourally instead, against
    propagate's own observable not-equals revisions on the FIX-G/FIX-H
    geometry (test_propagator.py's TestFixGAndFixHProduceIdenticalRemovals-
    ByDifferentRules / TestOffListContrastOnFixHGeometry): an on-list fixed
    word removes itself from same-length open slots (a Revision with
    source_crossing == -1 sourced from the fixed slot); an off-list one
    removes nothing. Agreement between what off_list_fixed reports and
    whether C3 actually produced that removal is the oracle -- the same
    pattern the spec already uses for AC-3 and the analyzer."""

    def test_on_list_fixed_word_is_on_list_and_c3_removes_it(self, fix_g_model, bitset_index):
        fixed = _fixed_with({0: "S", 1: "P", 2: "Y", 10: "S"})
        report = assess(fix_g_model, bitset_index, fixed, min_score=0)
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        assert 0 not in report.off_list_fixed
        assert any(r.source_crossing == -1 and r.source_slot == 0 for r in result.revisions)

    def test_off_list_fixed_word_is_off_list_and_c3_removes_nothing(self, fix_g_model, bitset_index):
        fixed = _fixed_with({0: "X", 1: "Y", 2: "Z", 10: "S"})
        report = assess(fix_g_model, bitset_index, fixed, min_score=0)
        result = propagate(fix_g_model, bitset_index, fixed, min_score=0, not_equals=True)
        assert 0 in report.off_list_fixed
        assert not any(r.source_crossing == -1 and r.source_slot == 0 for r in result.revisions)
