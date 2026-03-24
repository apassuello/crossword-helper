"""
Unit tests for EditMerger.

Tests grid change detection, domain pruning via AC-3, state validation,
and the full merge_edits workflow used by the pause/resume feature.
"""

import json
import pytest
from unittest.mock import MagicMock

from backend.core.edit_merger import EditMerger, GridChanges
from cli.src.core.grid import Grid


# ---------------------------------------------------------------------------
# Helpers — use size 11 (smallest standard size accepted by Grid.from_dict)
# ---------------------------------------------------------------------------

GRID_SIZE = 11


def _make_grid_dict(letters=None, blacks=None):
    """Build an 11x11 grid dict.

    Args:
        letters: dict of {(row, col): letter}.
        blacks: set of (row, col) positions for black squares.
    """
    grid = Grid(GRID_SIZE, validate_size=True)
    if blacks:
        for r, c in blacks:
            grid.set_black_square(r, c, enforce_symmetry=False)
    if letters:
        for (r, c), letter in letters.items():
            grid.set_letter(r, c, letter)
    return grid.to_dict()


def _make_slot_list_and_id_map(grid_dict):
    """Derive slot_list and slot_id_map from a grid dict."""
    grid = Grid.from_dict(grid_dict)
    slots = grid.get_word_slots()
    slot_id_map = {}
    for idx, slot in enumerate(slots):
        key = json.dumps([slot['row'], slot['col'], slot['direction']])
        slot_id_map[key] = idx
    return slots, slot_id_map


def _find_slot_id(slots, slot_id_map, row, col, direction):
    """Find slot ID by position and direction."""
    key = json.dumps([row, col, direction])
    return slot_id_map.get(key)


def _make_csp_state(
    grid_dict,
    domains=None,
    constraints=None,
    locked_slots=None,
    used_words=None,
):
    """Build a mock CSPState with the minimum attributes EditMerger needs."""
    slots, slot_id_map = _make_slot_list_and_id_map(grid_dict)
    state = MagicMock()
    state.grid_dict = grid_dict
    state.slot_list = slots
    state.slot_id_map = slot_id_map
    state.domains = domains if domains is not None else {
        i: [] for i in range(len(slots))
    }
    state.constraints = constraints if constraints is not None else {}
    state.locked_slots = locked_slots if locked_slots is not None else []
    state.used_words = used_words if used_words is not None else []
    state.slots_sorted = list(range(len(slots)))
    state.current_slot_index = 0
    state.iteration_count = 0
    state.timestamp = "2026-01-01T00:00:00"
    state.random_seed = None
    state.letter_frequency_table = None
    return state


def _fill_row(row, word):
    """Return letters dict that fills an 11-cell row with a word (must be len 11)."""
    return {(row, c): ch for c, ch in enumerate(word)}


# ---------------------------------------------------------------------------
# Tests: get_edit_summary
# ---------------------------------------------------------------------------

class TestGetEditSummary:
    """Tests for EditMerger.get_edit_summary()."""

    def setup_method(self):
        self.merger = EditMerger()

    def test_no_changes(self):
        """Identical grids produce an empty summary."""
        gd = _make_grid_dict()
        slots, sid_map = _make_slot_list_and_id_map(gd)

        summary = self.merger.get_edit_summary(gd, gd, slots, sid_map)

        assert summary['filled_count'] == 0
        assert summary['emptied_count'] == 0
        assert summary['modified_count'] == 0
        assert summary['new_words'] == []
        assert summary['removed_words'] == []

    def test_added_letters_detected(self):
        """Filling a previously empty slot is detected as filled."""
        saved = _make_grid_dict()
        word = 'ABCDEFGHIJK'
        edited = _make_grid_dict(letters=_fill_row(0, word))
        slots, sid_map = _make_slot_list_and_id_map(saved)

        summary = self.merger.get_edit_summary(saved, edited, slots, sid_map)

        assert summary['filled_count'] >= 1
        assert word in summary['new_words']

    def test_removed_letters_detected(self):
        """Emptying a previously filled slot is detected."""
        word = 'ABCDEFGHIJK'
        saved = _make_grid_dict(letters=_fill_row(0, word))
        edited = _make_grid_dict()
        slots, sid_map = _make_slot_list_and_id_map(saved)

        summary = self.merger.get_edit_summary(saved, edited, slots, sid_map)

        assert summary['emptied_count'] >= 1
        assert word in summary['removed_words']

    def test_changed_letters_detected(self):
        """Changing a filled slot to a different word is detected as modified."""
        old_word = 'ABCDEFGHIJK'
        new_word = 'ZBCDEFGHIJK'
        saved = _make_grid_dict(letters=_fill_row(0, old_word))
        edited = _make_grid_dict(letters=_fill_row(0, new_word))
        slots, sid_map = _make_slot_list_and_id_map(saved)

        summary = self.merger.get_edit_summary(saved, edited, slots, sid_map)

        assert summary['modified_count'] >= 1
        assert old_word in summary['removed_words']
        assert new_word in summary['new_words']


# ---------------------------------------------------------------------------
# Tests: _detect_changes (via internal access)
# ---------------------------------------------------------------------------

class TestDetectChanges:
    """Tests for EditMerger._detect_changes()."""

    def setup_method(self):
        self.merger = EditMerger()

    def test_partial_fill_not_counted_as_filled(self):
        """A slot that still has gaps should not appear in filled_slots."""
        saved = _make_grid_dict()
        # Fill only 2 of 11 cells in the across slot at row 0
        edited = _make_grid_dict(letters={(0, 0): 'A', (0, 1): 'B'})
        slots, sid_map = _make_slot_list_and_id_map(saved)

        saved_grid = Grid.from_dict(saved)
        edited_grid = Grid.from_dict(edited)
        changes = self.merger._detect_changes(saved_grid, edited_grid, slots, sid_map)

        # The across slot at row 0 still has gaps, so not "filled"
        across_0_id = _find_slot_id(slots, sid_map, 0, 0, 'across')
        assert across_0_id not in changes.filled_slots

    def test_returns_grid_changes_dataclass(self):
        """_detect_changes returns a GridChanges instance."""
        gd = _make_grid_dict()
        grid = Grid.from_dict(gd)
        slots, sid_map = _make_slot_list_and_id_map(gd)

        result = self.merger._detect_changes(grid, grid, slots, sid_map)

        assert isinstance(result, GridChanges)


# ---------------------------------------------------------------------------
# Tests: _revise (AC-3 arc revision)
# ---------------------------------------------------------------------------

class TestRevise:
    """Tests for EditMerger._revise()."""

    def setup_method(self):
        self.merger = EditMerger()

    def test_prunes_incompatible_words(self):
        """Words that conflict at the crossing position are removed."""
        # slot 0 crosses slot 1: slot 0 position 1 must equal slot 1 position 0
        domains = {
            0: {'CAT', 'COT', 'CUT'},
            1: {'APE', 'OWL'},
        }
        # slot_0[1] must equal slot_1[0]
        # APE[0]='A' -> CAT[1]='A' ok
        # OWL[0]='O' -> COT[1]='O' ok
        # CUT[1]='U' -> no match in {A, O}
        revised = self.merger._revise(domains, 0, 1, 1, 0)

        assert revised is True
        assert domains[0] == {'CAT', 'COT'}

    def test_no_pruning_when_compatible(self):
        """No revision when all words are already compatible."""
        domains = {
            0: {'CAT'},
            1: {'APE'},
        }
        # CAT[1]='A', APE[0]='A' -> compatible
        revised = self.merger._revise(domains, 0, 1, 1, 0)

        assert revised is False
        assert domains[0] == {'CAT'}

    def test_missing_slot_returns_false(self):
        """If either slot is missing from domains, return False without error."""
        domains = {0: {'CAT'}}

        assert self.merger._revise(domains, 0, 99, 0, 0) is False
        assert self.merger._revise(domains, 99, 0, 0, 0) is False


# ---------------------------------------------------------------------------
# Tests: _validate_state
# ---------------------------------------------------------------------------

class TestValidateState:
    """Tests for EditMerger._validate_state()."""

    def setup_method(self):
        self.merger = EditMerger()

    def test_valid_domains(self):
        """Non-empty domains pass validation."""
        domains = {0: {'CAT'}, 1: {'DOG'}}
        slot_list = [
            {'row': 0, 'col': 0, 'direction': 'across', 'length': 3},
            {'row': 0, 'col': 0, 'direction': 'down', 'length': 3},
        ]

        result = self.merger._validate_state(domains, {}, slot_list)

        assert result['is_valid'] is True
        assert result['empty_domains'] == []

    def test_empty_domain_detected(self):
        """An empty domain makes the state invalid."""
        domains = {0: set(), 1: {'DOG'}}
        slot_list = [
            {'row': 0, 'col': 0, 'direction': 'across', 'length': 3},
            {'row': 0, 'col': 0, 'direction': 'down', 'length': 3},
        ]

        result = self.merger._validate_state(domains, {}, slot_list)

        assert result['is_valid'] is False
        assert 0 in result['empty_domains']


# ---------------------------------------------------------------------------
# Tests: merge_edits (integration through the public API)
# ---------------------------------------------------------------------------

class TestMergeEdits:
    """Tests for EditMerger.merge_edits()."""

    def setup_method(self):
        self.merger = EditMerger()

    def _build_state_with_domains(self, grid_dict, domains=None, constraints=None):
        """Build a CSP state for the given grid with specified domains."""
        slots, sid_map = _make_slot_list_and_id_map(grid_dict)
        if domains is None:
            # Default: give each slot a list of dummy words of the right length
            domains = {}
            for idx, slot in enumerate(slots):
                length = slot['length']
                filler = 'A' * length
                domains[idx] = [filler]
        return _make_csp_state(
            grid_dict,
            domains=domains,
            constraints=constraints or {},
        )

    def test_merge_returns_updated_state(self):
        """merge_edits returns a CSPState with the edited grid_dict."""
        grid_dict = _make_grid_dict()
        state = self._build_state_with_domains(grid_dict)
        word = 'ABCDEFGHIJK'
        edited = _make_grid_dict(letters=_fill_row(0, word))

        result = self.merger.merge_edits(state, edited)

        assert result.grid_dict == edited

    def test_merge_locks_filled_slots(self):
        """Newly filled slots are added to locked_slots."""
        grid_dict = _make_grid_dict()
        state = self._build_state_with_domains(grid_dict)
        word = 'ABCDEFGHIJK'
        edited = _make_grid_dict(letters=_fill_row(0, word))

        result = self.merger.merge_edits(state, edited)

        assert len(result.locked_slots) > 0

    def test_merge_updates_used_words(self):
        """New words from filled slots appear in used_words."""
        grid_dict = _make_grid_dict()
        state = self._build_state_with_domains(grid_dict)
        word = 'ABCDEFGHIJK'
        edited = _make_grid_dict(letters=_fill_row(0, word))

        result = self.merger.merge_edits(state, edited)

        assert word in result.used_words

    def test_merge_raises_on_empty_domain(self):
        """If edits cause an empty domain, ValueError is raised."""
        grid_dict = _make_grid_dict()
        slots, sid_map = _make_slot_list_and_id_map(grid_dict)

        # Find the across slot at row 0 and the down slot at col 0
        across_0 = _find_slot_id(slots, sid_map, 0, 0, 'across')
        down_0 = _find_slot_id(slots, sid_map, 0, 0, 'down')

        assert across_0 is not None and down_0 is not None

        # Domains: across has word starting with 'A' at pos 0,
        # down has only words starting with 'Z' -- conflict at (0,0).
        domains = {}
        for idx, slot in enumerate(slots):
            length = slot['length']
            if idx == across_0:
                domains[idx] = ['A' * length]
            elif idx == down_0:
                domains[idx] = ['Z' * length]
            else:
                domains[idx] = ['A' * length]

        # Constraint: across_0[0] must equal down_0[0]
        constraints = {
            across_0: [[down_0, 0, 0]],
            down_0: [[across_0, 0, 0]],
        }

        state = _make_csp_state(
            grid_dict,
            domains=domains,
            constraints=constraints,
        )

        # Edit: fill row 0 with 'A's, locking across_0
        edited = _make_grid_dict(letters=_fill_row(0, 'A' * GRID_SIZE))

        with pytest.raises(ValueError, match="unsolvable"):
            self.merger.merge_edits(state, edited)

    def test_merge_preserves_metadata(self):
        """Metadata fields like iteration_count and timestamp pass through."""
        grid_dict = _make_grid_dict()
        state = self._build_state_with_domains(grid_dict)
        state.iteration_count = 42
        state.timestamp = "2026-03-24T12:00:00"
        edited = _make_grid_dict()

        result = self.merger.merge_edits(state, edited)

        assert result.iteration_count == 42
        assert result.timestamp == "2026-03-24T12:00:00"
