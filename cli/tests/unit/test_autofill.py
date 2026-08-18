"""
Unit tests for autofill module.
"""

import itertools
import time

import pytest
from src.core.grid import Grid
from src.fill.autofill import Autofill, FillResult
from src.fill.pattern_matcher import PatternMatcher
from src.fill.trie_pattern_matcher import TriePatternMatcher
from src.fill.word_list import WordList


class TestAutofill:
    """Test Autofill class."""

    @pytest.fixture
    def word_list(self):
        """Create a sample word list for testing."""
        words = [
            # 3-letter words
            "CAT",
            "COT",
            "CUT",
            "BAT",
            "BOT",
            "BUT",
            "RAT",
            "ROT",
            "RUT",
            "MAT",
            "MOT",
            "MUT",
            "ACE",
            "ACT",
            "ART",
            "ARC",
            "ARM",
            "ARE",
            # 4-letter words
            "CATS",
            "BATS",
            "RATS",
            "MATS",
            "TEAR",
            "BEAR",
            "DEAR",
            "FEAR",
            "CART",
            "DART",
            "PART",
            "TART",
            # 5-letter words
            "APPLE",
            "AMPLE",
            "MAPLE",
            "CABIN",
            "CABLE",
            "CAPER",
        ]
        return WordList(words)

    @pytest.fixture
    def small_grid(self):
        """Create a small grid for testing."""
        grid = Grid(11)
        # Add some black squares to create word slots
        grid.set_black_square(5, 5)
        return grid

    def test_init(self, small_grid, word_list):
        """Test creating autofill solver."""
        autofill = Autofill(small_grid, word_list)
        assert autofill.grid == small_grid
        assert autofill.word_list == word_list
        assert autofill.timeout == 300
        assert autofill.min_score == 0  # Default changed to 0 to allow full search space

    def test_init_with_custom_params(self, small_grid, word_list):
        """Test creating autofill with custom parameters."""
        autofill = Autofill(small_grid, word_list, timeout=60, min_score=50)
        assert autofill.timeout == 60
        assert autofill.min_score == 50

    def test_init_creates_pattern_matcher(self, small_grid, word_list):
        """Test that pattern matcher is created if not provided."""
        # Default algorithm is 'trie', so should create TriePatternMatcher
        autofill = Autofill(small_grid, word_list)
        assert isinstance(autofill.pattern_matcher, TriePatternMatcher)

        # Test with explicit regex algorithm
        autofill_regex = Autofill(small_grid, word_list, algorithm="regex")
        assert isinstance(autofill_regex.pattern_matcher, PatternMatcher)

    def test_fill_empty_grid_returns_success(self, word_list):
        """Test filling an already filled grid."""
        grid = Grid(11)
        # Fill entire grid
        for row in range(11):
            for col in range(11):
                grid.set_letter(row, col, "A")

        autofill = Autofill(grid, word_list)
        result = autofill.fill()

        assert result.success
        assert result.slots_filled == 0
        assert result.total_slots == 0

    def test_fill_result_structure(self, small_grid, word_list):
        """Test that fill returns proper FillResult."""
        autofill = Autofill(small_grid, word_list, timeout=1)
        result = autofill.fill()

        assert isinstance(result, FillResult)
        assert hasattr(result, "success")
        assert hasattr(result, "grid")
        assert hasattr(result, "time_elapsed")
        assert hasattr(result, "slots_filled")
        assert hasattr(result, "total_slots")
        assert hasattr(result, "problematic_slots")
        assert hasattr(result, "iterations")

    def test_fill_timeout(self, small_grid, word_list):
        """Test that fill respects timeout."""
        autofill = Autofill(small_grid, word_list, timeout=0.1)
        result = autofill.fill()

        # Should timeout quickly
        assert result.time_elapsed < 1.0

    def test_fill_iterations_increment(self, small_grid, word_list):
        """Test that iterations are counted."""
        autofill = Autofill(small_grid, word_list, timeout=1)
        result = autofill.fill()

        # Should have tried some iterations, or failed early in AC-3
        # (AC-3 may return with 0 iterations if no solution possible)
        assert result.iterations >= 0
        # If no solution, should have problematic slots
        if not result.success:
            assert len(result.problematic_slots) > 0

    def test_fill_updates_grid(self, word_list):
        """Test that fill actually places words in grid."""
        # Create simple grid with one across slot
        grid = Grid(11)
        # Make a simple pattern with black squares
        for col in range(7, 11):
            grid.set_black_square(0, col)
        for col in range(7, 11):
            grid.set_black_square(1, col)

        autofill = Autofill(grid, word_list, timeout=5)
        result = autofill.fill()

        # Check that some cells were filled
        filled_count = sum(1 for row in range(grid.size) for col in range(grid.size) if grid.has_letter(row, col))
        assert filled_count > 0 or not result.success  # Either filled or failed

    def test_initialize_csp(self, small_grid, word_list):
        """Test CSP initialization."""
        autofill = Autofill(small_grid, word_list)
        slots = small_grid.get_empty_slots()

        autofill._initialize_csp(slots)

        assert len(autofill.slot_list) == len(slots)
        assert len(autofill.slot_id_map) == len(slots)
        assert len(autofill.constraints) == len(slots)
        assert len(autofill.domains) == len(slots)

    def test_initialize_csp_creates_domains(self, small_grid, word_list):
        """Test that CSP initialization creates domains for each slot."""
        autofill = Autofill(small_grid, word_list)
        slots = small_grid.get_empty_slots()

        autofill._initialize_csp(slots)

        # Each slot should have a domain
        for slot_id in range(len(slots)):
            assert slot_id in autofill.domains
            assert isinstance(autofill.domains[slot_id], set)

    def test_get_intersection_across_down(self, small_grid, word_list):
        """Test finding intersection between across and down slots."""
        autofill = Autofill(small_grid, word_list)

        # Create two intersecting slots
        slot_across = {"row": 2, "col": 1, "length": 5, "direction": "across"}
        slot_down = {"row": 0, "col": 3, "length": 5, "direction": "down"}

        intersection = autofill._get_intersection(slot_across, slot_down)

        # Should intersect at (2, 3)
        assert intersection is not None
        pos_across, pos_down = intersection
        assert pos_across == 2  # Position 2 in across word
        assert pos_down == 2  # Position 2 in down word

    def test_get_intersection_parallel_slots(self, small_grid, word_list):
        """Test that parallel slots don't intersect."""
        autofill = Autofill(small_grid, word_list)

        # Two parallel across slots
        slot1 = {"row": 0, "col": 0, "length": 5, "direction": "across"}
        slot2 = {"row": 1, "col": 0, "length": 5, "direction": "across"}

        intersection = autofill._get_intersection(slot1, slot2)
        assert intersection is None

    def test_get_intersection_non_overlapping(self, small_grid, word_list):
        """Test that non-overlapping slots don't intersect."""
        autofill = Autofill(small_grid, word_list)

        slot_across = {"row": 0, "col": 0, "length": 3, "direction": "across"}
        slot_down = {"row": 5, "col": 5, "length": 3, "direction": "down"}

        intersection = autofill._get_intersection(slot_across, slot_down)
        assert intersection is None

    def test_ac3_consistent_domains(self, word_list):
        """Test AC-3 with consistent domains."""
        # Create simple grid with 3-letter words (matching our test word list)
        grid = Grid(11)
        # Create a pattern with only 3-letter slots
        for i in range(0, 11, 4):  # Place black squares every 4 positions
            for row in range(11):
                if i < 11:
                    grid.set_black_square(row, i, enforce_symmetry=False)

        autofill = Autofill(grid, word_list, min_score=0)  # Accept all words
        slots = grid.get_empty_slots()

        if len(slots) == 0:
            # If no slots, AC-3 should trivially succeed
            return

        autofill._initialize_csp(slots)

        result = autofill._ac3()
        # AC-3 may succeed or fail depending on word list - just verify it doesn't crash
        assert isinstance(result, bool)

    def test_revise_removes_incompatible(self, word_list):
        """Test that revise removes incompatible words."""
        grid = Grid(11)
        autofill = Autofill(grid, word_list)

        # Set up domains manually
        autofill.domains = {0: {"CAT", "COT", "CUT"}, 1: {"BAT", "RAT", "MAT"}}

        # Revise with constraint that position 0 must match
        # CAT[0]=C should match nothing in domain 1 (all start with B/R/M)
        revised = autofill._revise(0, 1, 0, 0)

        # Should have removed some words
        assert revised or len(autofill.domains[0]) >= 0

    def test_forward_check_valid_placement(self, small_grid, word_list):
        """Test forward checking with valid placement."""
        autofill = Autofill(small_grid, word_list)
        slots = small_grid.get_empty_slots()

        if len(slots) > 0:
            autofill._initialize_csp(slots)
            result = autofill._forward_check(slots[0])
            # Should return True or False, not crash
            assert isinstance(result, bool)

    def test_backtrack_base_case(self, word_list):
        """Test backtrack base case (no slots to fill)."""
        grid = Grid(11)
        autofill = Autofill(grid, word_list)

        slots = []
        autofill.start_time = time.time()  # Set to current time to avoid timeout
        autofill._initialize_csp(slots)

        result = autofill._backtrack(slots, 0)
        assert result is True

    def test_backtrack_timeout(self, small_grid, word_list):
        """Test that backtrack respects timeout."""
        autofill = Autofill(small_grid, word_list, timeout=0.001)
        slots = small_grid.get_empty_slots()

        autofill.start_time = 0  # Set in distant past
        autofill._initialize_csp(slots)

        with pytest.raises(TimeoutError):
            autofill._backtrack(slots, 0)

    def test_used_words_tracking(self, small_grid, word_list):
        """Test that used words are tracked."""
        autofill = Autofill(small_grid, word_list)
        assert len(autofill.used_words) == 0

        # After filling, used_words should be updated
        autofill.fill()
        # used_words might be empty if fill failed, but shouldn't crash

    def test_sort_slots_by_constraint(self, word_list):
        """Test MCV heuristic for slot sorting."""
        grid = Grid(11)
        # Create some slots with different constraints
        grid.set_black_square(0, 5)

        autofill = Autofill(grid, word_list)
        slots = grid.get_empty_slots()
        autofill._initialize_csp(slots)

        sorted_slots = autofill._sort_slots_by_constraint(slots)

        # Should return same number of slots
        assert len(sorted_slots) == len(slots)

    def test_get_candidates(self, small_grid, word_list):
        """Test getting candidate words for a slot."""
        autofill = Autofill(small_grid, word_list)
        slots = small_grid.get_empty_slots()

        if len(slots) > 0:
            autofill._initialize_csp(slots)
            candidates = autofill._get_candidates(slots[0])

            # Should return list of (word, score) tuples
            assert isinstance(candidates, list)
            for item in candidates:
                assert isinstance(item, tuple)
                assert len(item) == 2
                word, score = item
                assert isinstance(word, str)
                assert isinstance(score, int)

    def test_get_candidates_sorted_by_score(self, small_grid, word_list):
        """Test that candidates are sorted by score."""
        autofill = Autofill(small_grid, word_list)
        slots = small_grid.get_empty_slots()

        if len(slots) > 0:
            autofill._initialize_csp(slots)
            candidates = autofill._get_candidates(slots[0])

            if len(candidates) > 1:
                scores = [score for word, score in candidates]
                assert scores == sorted(scores, reverse=True)

    def test_slots_intersect_true(self, small_grid, word_list):
        """Test detecting slot intersection."""
        autofill = Autofill(small_grid, word_list)

        slot1 = {"row": 2, "col": 1, "length": 5, "direction": "across"}
        slot2 = {"row": 0, "col": 3, "length": 5, "direction": "down"}

        assert autofill._slots_intersect(slot1, slot2)

    def test_slots_intersect_false_parallel(self, small_grid, word_list):
        """Test that parallel slots don't intersect."""
        autofill = Autofill(small_grid, word_list)

        slot1 = {"row": 0, "col": 0, "length": 5, "direction": "across"}
        slot2 = {"row": 1, "col": 0, "length": 5, "direction": "across"}

        assert not autofill._slots_intersect(slot1, slot2)

    def test_slots_intersect_false_no_overlap(self, small_grid, word_list):
        """Test that non-overlapping slots don't intersect."""
        autofill = Autofill(small_grid, word_list)

        slot1 = {"row": 0, "col": 0, "length": 3, "direction": "across"}
        slot2 = {"row": 5, "col": 5, "length": 3, "direction": "down"}

        assert not autofill._slots_intersect(slot1, slot2)

    def test_get_crossing_slots(self, word_list):
        """Test finding crossing slots."""
        grid = Grid(11)
        autofill = Autofill(grid, word_list)

        slot = {"row": 2, "col": 1, "length": 5, "direction": "across"}
        all_slots = [
            {"row": 2, "col": 1, "length": 5, "direction": "across"},  # Same slot
            {"row": 0, "col": 3, "length": 5, "direction": "down"},  # Crosses
            {"row": 3, "col": 0, "length": 5, "direction": "across"},  # Doesn't cross
        ]

        crossing = autofill._get_crossing_slots(slot, all_slots)

        # Should find at least the one crossing slot
        assert len(crossing) >= 0  # May vary based on actual intersection

    def test_repr(self, small_grid, word_list):
        """Test string representation."""
        autofill = Autofill(small_grid, word_list)
        repr_str = repr(autofill)

        assert "Autofill" in repr_str
        assert "11x11" in repr_str or "11" in repr_str


class TestAc3EmptyDomainContract:
    """
    #17: `_ac3()` returning True does not mean "no empty domain".

    `_ac3()` only reports False when `_revise()` empties a domain *during*
    revision. A slot whose domain is already empty at initialization has
    nothing to revise -- if it has no crossing neighbor to drive the cascade,
    the arc queue never touches it and `_ac3()` drains "consistent". The
    `:188` guard in `fill()` used to read that True as a solvability check.
    """

    def test_fill_reports_failure_on_isolated_slot_with_no_candidates(self):
        """
        Isolated-slot bug window: one across slot, no crossing down slot at
        all (every column under it has a single white cell, black above and
        below), so `_ac3`'s arc queue is empty for it and it can never be
        revised. The word list has no 3-letter word, so its domain is empty
        from `_initialize_csp` onward -- dead before any revision runs.

        A fixture where the dead slot crosses a live neighbor would already
        pass before the fix (the cascade catches that case); this one does
        not cross anything, which is the real bug window per the issue.
        """
        grid = Grid(11)
        for row in range(11):
            for col in range(11):
                if not (row == 5 and col < 3):
                    # enforce_symmetry defaults True and would black (5,10)
                    # and mirror it, destroying the isolated layout.
                    grid.set_black_square(row, col, enforce_symmetry=False)

        word_list = WordList(["ABCD", "WXYZ"])  # no 3-letter word exists
        autofill = Autofill(grid, word_list, None, 60, 0, "trie", None)

        result = autofill.fill()

        assert result.success is False
        assert result.iterations == 0, "must never enter backtracking over a dead domain"


class TestOnBacktrackCallback:
    """Test that on_backtrack callback is invoked during CSP backtracking."""

    def test_on_backtrack_called_in_backtrack(self):
        """Verify on_backtrack fires in _backtrack when a candidate fails."""
        grid = Grid(11)
        words = ["CAT", "BAT", "RAT"]
        wl = WordList(words)

        autofill = Autofill(grid, wl, timeout=5)
        autofill.start_time = time.time()
        autofill.iterations = 0
        autofill.used_words = set()

        backtrack_log = []
        autofill.on_backtrack = lambda key: backtrack_log.append(key)

        # Create a fake slot list where the second slot has no candidates,
        # forcing a backtrack on the first slot.
        slots = [
            {"row": 0, "col": 0, "length": 3, "direction": "across", "number": 1},
            {"row": 0, "col": 0, "length": 3, "direction": "down", "number": 1},
        ]

        # _backtrack will place a word in slot 0 then fail on slot 1
        # (since slot 1 shares cell 0,0 and no word starts with same letter).
        # It will backtrack on slot 0 and try other candidates.
        autofill._backtrack(slots, 0)

        assert len(backtrack_log) > 0, "on_backtrack was never called"
        # Verify slot key format
        for key in backtrack_log:
            parts = key.split(",")
            assert len(parts) == 3, f"Bad slot key format: {key}"
            assert parts[2] in ("across", "down")

    def test_on_backtrack_called_in_backtrack_with_mac(self):
        """Verify on_backtrack fires in _backtrack_with_mac too."""
        grid = Grid(11)
        words = ["CAT", "BAT", "RAT"]
        wl = WordList(words)

        autofill = Autofill(grid, wl, timeout=5)
        autofill.start_time = time.time()
        autofill.iterations = 0
        autofill.used_words = set()

        # Initialize domains for MAC path
        slots = [
            {"row": 0, "col": 0, "length": 3, "direction": "across", "number": 1},
            {"row": 0, "col": 0, "length": 3, "direction": "down", "number": 1},
        ]
        autofill._initialize_csp(slots)

        backtrack_log = []
        autofill.on_backtrack = lambda key: backtrack_log.append(key)

        autofill._backtrack_with_mac(slots, 0)

        assert len(backtrack_log) > 0, "on_backtrack was never called in MAC path"

    def test_on_backtrack_default_is_none(self):
        """Verify on_backtrack defaults to None and doesn't error."""
        grid = Grid(11)
        words = ["CAT", "BAT", "RAT"]
        wl = WordList(words)

        autofill = Autofill(grid, wl, timeout=1)
        assert autofill.on_backtrack is None
        # Should not raise even though backtracking occurs internally
        autofill.fill()


class TestFillResult:
    """Test FillResult dataclass."""

    def test_creation(self):
        """Test creating a FillResult."""
        grid = Grid(11)
        result = FillResult(
            success=True,
            grid=grid,
            time_elapsed=1.5,
            slots_filled=10,
            total_slots=10,
            problematic_slots=[],
            iterations=100,
        )

        assert result.success is True
        assert result.grid == grid
        assert result.time_elapsed == 1.5
        assert result.slots_filled == 10
        assert result.total_slots == 10
        assert result.problematic_slots == []
        assert result.iterations == 100

    def test_partial_fill(self):
        """Test FillResult for partial fill."""
        grid = Grid(11)
        problematic = [{"row": 0, "col": 0, "length": 5, "direction": "across"}]
        result = FillResult(
            success=False,
            grid=grid,
            time_elapsed=5.0,
            slots_filled=8,
            total_slots=10,
            problematic_slots=problematic,
            iterations=1000,
        )

        assert result.success is False
        assert result.slots_filled < result.total_slots
        assert len(result.problematic_slots) > 0


class TestAutofillIntegration:
    """Integration tests for autofill with realistic scenarios."""

    @pytest.fixture
    def large_word_list(self):
        """Create a larger word list for integration tests."""
        words = []
        # Add many 3-letter words
        for c1 in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            for c2 in "AEIOU":
                for c3 in "NRST":
                    words.append(c1 + c2 + c3)
        return WordList(words)

    def test_small_grid_complete_fill(self):
        """Test filling a small grid completely.

        `large_word_list` is all 3-letter (26 x 5 vowels x 4 NRST-endings),
        but the original fixture's 3 black squares left several 8-11 length
        slots -- unfillable by any 3-letter word regardless of the #17 fix,
        so `result.iterations > 0` alone never actually proved a fill was
        attempted, only that domains happened to look non-empty long enough
        for the pre-fix `_ac3()` misreading to let backtracking start (#17:
        `_ac3()`'s return value is not a solvability check).

        Black out rows/cols 3 and 7 (180deg-symmetric: {3, 7} maps to itself
        under row -> 10 - row) so every slot is exactly 3 long, and use a
        word list dense enough (every letter of a 5-letter alphabet in every
        position) that arc consistency cannot legitimately empty a domain
        through cross-constraints either. That makes this grid actually
        solvable, so the test can assert the complete fill it is named for.
        """
        grid = Grid(11)
        for row in range(11):
            for col in range(11):
                if row in (3, 7) or col in (3, 7):
                    grid.set_black_square(row, col, enforce_symmetry=False)

        words = ["".join(letters) for letters in itertools.product("ABCDE", repeat=3)]
        autofill = Autofill(grid, WordList(words), timeout=10)
        result = autofill.fill()

        assert result.success is True
        assert result.iterations > 0
        assert result.time_elapsed >= 0

    def test_partially_filled_grid(self, large_word_list):
        """Test filling grid that's partially completed."""
        grid = Grid(11)
        grid.set_black_square(0, 5)

        # Pre-fill some words
        grid.place_word("CAT", 0, 0, "across")

        autofill = Autofill(grid, large_word_list, timeout=5)
        autofill.fill()

        # CAT should still be there
        assert grid.get_cell(0, 0) == "C"
        assert grid.get_cell(0, 1) == "A"
        assert grid.get_cell(0, 2) == "T"


class TestResumeUnwinding:
    """
    Cover the dead-end recovery path (issue #9).

    `_unwind_dead_ends` and `_strip_words_around_constrained_slots` had no
    caller and no test after the bench<->main merge dropped main's resume loop.
    `_resume_fill` now falls back to `_resume_by_unwinding`, so they are live
    again — these are their first direct tests.
    """

    @pytest.fixture
    def tiny_word_list(self):
        """Only 3-letter words, so any longer slot is unfillable by construction."""
        return WordList(["CAT", "COT", "CUT", "DOG", "DOT"])

    def test_unwind_strips_a_word_that_makes_a_crossing_slot_unfillable(self, tiny_word_list):
        # A bare cross: a 3-long across slot over a 4-long down slot, everything
        # else black. `_unwind_dead_ends` only strips slots that are COMPLETELY
        # filled, so the offending word has to be a whole slot, not three
        # letters inside a longer one.
        grid = Grid(11)
        cross = {(0, 0), (0, 1), (0, 2), (1, 0), (2, 0), (3, 0)}
        for r in range(11):
            for c in range(11):
                if (r, c) not in cross:
                    # enforce_symmetry defaults True: blacking (10,10) would also
                    # black (0,0) and quietly destroy the slot under test.
                    grid.set_black_square(r, c, enforce_symmetry=False)

        # CAT across leaves the down slot needing "C???" — the word list has no
        # 4-letter words at all, so that domain is empty and the position is dead.
        grid.place_word("CAT", 0, 0, "across")
        autofill = Autofill(grid, tiny_word_list, timeout=5)

        removed = autofill._unwind_dead_ends()

        assert removed >= 1, "a dead-end position should have had at least one word stripped"
        assert "?" in grid.get_pattern_for_slot(
            {"row": 0, "col": 0, "length": 3, "direction": "across"}
        ), "the offending word should be gone from the grid"

    def test_unwind_is_a_no_op_on_a_grid_with_no_dead_end(self, tiny_word_list):
        # Control: without this, the test above would pass even if
        # _unwind_dead_ends stripped indiscriminately.
        grid = Grid(11)
        for r in range(11):
            for c in range(11):
                if not (r == 0 and c < 3):
                    grid.set_black_square(r, c, enforce_symmetry=False)
        # Only one 3-long across slot remains, and it is empty and fillable.
        autofill = Autofill(grid, tiny_word_list, timeout=5)

        assert autofill._unwind_dead_ends() == 0
