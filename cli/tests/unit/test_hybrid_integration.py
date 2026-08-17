"""
Integration tests for hybrid autofill (beam search + iterative repair).
"""

import random
import time

import pytest
from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamSearchAutofill
from src.fill.hybrid_autofill import HybridAutofill
from src.fill.iterative_repair import IterativeRepair
from src.fill.trie_pattern_matcher import TriePatternMatcher
from src.fill.word_list import WordList

# Fixed seed for the hybrid-vs-beam comparison below. Any value works; it is
# pinned only so both solvers start from the same RNG position.
_COMPARISON_SEED = 20260817


class TestHybridIntegration:
    """Test HybridAutofill integration."""

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
            "TEA",
            "TEN",
            "TAN",
            "TAR",
            "TAX",
            "TUB",
            # 4-letter words
            "CATS",
            "BATS",
            "RATS",
            "MATS",
            "ARTS",
            "TEAR",
            "BEAR",
            "DEAR",
            "FEAR",
            "HEAR",
            "CART",
            "DART",
            "PART",
            "TART",
            "WART",
            # 5-letter words
            "APPLE",
            "AMPLE",
            "MAPLE",
            "TABLE",
            "CABLE",
            "CABIN",
            "CAPER",
            "TAPER",
            "PAPER",
            # 7-letter words
            "CABBAGE",
            "BAGGAGE",
            "PACKAGE",
            # 11-letter words
            "ABRACADABRA",
            "HOCUSPOCUS",
        ]
        return WordList(words)

    @pytest.fixture
    def small_grid(self):
        """Create a small grid for testing."""
        grid = Grid(11)
        grid.set_black_square(5, 5)
        return grid

    @pytest.fixture
    def pattern_matcher_trie(self, word_list):
        """Create a trie pattern matcher."""
        return TriePatternMatcher(word_list)

    def test_init(self, small_grid, word_list, pattern_matcher_trie):
        """Test creating HybridAutofill solver."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie)

        assert hybrid.grid == small_grid
        assert hybrid.word_list == word_list
        assert hybrid.min_score == 0
        assert hybrid.beam_width == 5
        assert hybrid.max_repair_iterations == 500

    def test_init_custom_params(self, small_grid, word_list, pattern_matcher_trie):
        """Test creating solver with custom parameters."""
        hybrid = HybridAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            min_score=20,
            beam_width=3,
            max_repair_iterations=100,
        )

        assert hybrid.min_score == 20
        assert hybrid.beam_width == 3
        assert hybrid.max_repair_iterations == 100

    def test_fill_invalid_timeout(self, small_grid, word_list, pattern_matcher_trie):
        """Test that timeout < 30 raises ValueError."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie)

        with pytest.raises(ValueError, match="timeout must be ≥30 seconds"):
            hybrid.fill(timeout=20)

    def test_fill_invalid_timeout_ratios(self, small_grid, word_list, pattern_matcher_trie):
        """Test that invalid timeout ratios raise ValueError."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie)

        with pytest.raises(ValueError, match="must be ≤1.0"):
            hybrid.fill(timeout=60, beam_timeout_ratio=0.8, repair_timeout_ratio=0.5)

    def test_fill_result_structure(self, small_grid, word_list, pattern_matcher_trie):
        """Test that fill returns proper FillResult."""
        hybrid = HybridAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            beam_width=2,
            max_repair_iterations=50,
        )

        result = hybrid.fill(timeout=30)

        # Check result structure
        assert hasattr(result, "success")
        assert hasattr(result, "grid")
        assert hasattr(result, "time_elapsed")
        assert hasattr(result, "slots_filled")
        assert hasattr(result, "total_slots")
        assert hasattr(result, "problematic_slots")
        assert hasattr(result, "iterations")

        # Check types
        assert isinstance(result.success, bool)
        assert isinstance(result.grid, Grid)
        assert isinstance(result.time_elapsed, float)
        assert isinstance(result.slots_filled, int)
        assert isinstance(result.total_slots, int)
        assert isinstance(result.problematic_slots, list)
        assert isinstance(result.iterations, int)

    def test_fill_already_complete_grid(self, word_list, pattern_matcher_trie):
        """Test filling an already complete grid."""
        grid = Grid(11)
        # Fill entire grid with letters
        for row in range(11):
            for col in range(11):
                grid.set_letter(row, col, "A")

        hybrid = HybridAutofill(grid, word_list, pattern_matcher_trie)
        result = hybrid.fill(timeout=30)

        # Should succeed immediately (no slots to fill)
        assert result.success is True
        assert result.slots_filled == 0
        assert result.total_slots == 0

    def test_fill_respects_timeout(self, small_grid, word_list, pattern_matcher_trie):
        """Test that fill respects timeout."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie, beam_width=2)

        timeout = 30
        start = time.time()
        hybrid.fill(timeout=timeout)
        elapsed = time.time() - start

        # Should not exceed timeout by more than 20% (some overhead expected)
        assert elapsed <= timeout * 1.2

    def test_fill_no_duplicate_words(self, small_grid, word_list, pattern_matcher_trie):
        """Test that fill doesn't use duplicate words."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie, beam_width=2)

        result = hybrid.fill(timeout=30)

        # Extract all words from result grid
        words_in_grid = []
        for slot in result.grid.get_word_slots():
            pattern = result.grid.get_pattern_for_slot(slot)
            if "?" not in pattern:  # Only filled slots
                words_in_grid.append(pattern)

        # Check for duplicates
        assert len(words_in_grid) == len(set(words_in_grid)), f"Found duplicate words: {words_in_grid}"

    def test_repair_receives_cloned_grid_not_beam_grid(self, small_grid, word_list, pattern_matcher_trie, monkeypatch):
        """Phase 2 (IterativeRepair) must be handed an independently-owned clone of the
        phase-1 beam grid, not the beam grid object itself.

        `small_grid` (11x11, one black square) against the tiny fixture word list can't be
        completed by beam search alone, so phase 2 is guaranteed to run.

        Intercepts the boundary two ways, since `beam_result` is never exposed by
        `HybridAutofill.fill()`:
        - wraps `BeamSearchAutofill.fill` to capture the `FillResult.grid` phase 1 produced
          (and a snapshot of its cells taken right after phase 1 finishes)
        - wraps `IterativeRepair.__init__` to capture the grid object phase 2 receives

        If phase 2 is holding the same object beam search returned, mutating it in place
        (as `IterativeRepair.fill` does) changes `beam_grid.cells` out from under phase 1's
        result -- exactly the aliasing bug in #13.
        """
        captured = {}

        original_beam_fill = BeamSearchAutofill.fill

        def capturing_beam_fill(self, *args, **kwargs):
            result = original_beam_fill(self, *args, **kwargs)
            captured["beam_grid"] = result.grid
            captured["beam_cells_snapshot"] = result.grid.cells.copy()
            return result

        monkeypatch.setattr(BeamSearchAutofill, "fill", capturing_beam_fill)

        original_repair_init = IterativeRepair.__init__

        def capturing_repair_init(self, grid_arg, *args, **kwargs):
            captured["repair_grid"] = grid_arg
            original_repair_init(self, grid_arg, *args, **kwargs)

        monkeypatch.setattr(IterativeRepair, "__init__", capturing_repair_init)

        hybrid = HybridAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            beam_width=2,
            max_repair_iterations=50,
        )
        hybrid.fill(timeout=30)

        assert "beam_grid" in captured, "beam search never ran -- test setup invalid"
        assert "repair_grid" in captured, "phase 2 (repair) never ran -- test setup invalid, beam must have succeeded outright"

        assert captured["repair_grid"] is not captured["beam_grid"], (
            "IterativeRepair received the SAME grid object BeamSearchAutofill returned; "
            "phase 2 must receive an independently-owned clone (see Grid.clone())"
        )
        assert (captured["beam_grid"].cells == captured["beam_cells_snapshot"]).all(), (
            "beam_result.grid was mutated by phase 2 -- the grid handed to IterativeRepair "
            "aliases the beam-phase grid instead of being an independent clone"
        )

    def test_fill_result_slots_filled_matches_grid_state(self, small_grid, word_list, pattern_matcher_trie):
        """Self-consistency guard: `slots_filled` must agree with what the returned grid
        actually contains, i.e. it can't be a stale count from a phase whose grid was later
        mutated by the other phase (the aliasing bug this task fixes).
        """
        hybrid = HybridAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            beam_width=2,
            max_repair_iterations=50,
        )

        result = hybrid.fill(timeout=30)

        assert result.slots_filled == len(result.grid.get_word_slots()) - len(result.grid.get_empty_slots())

    def test_hybrid_vs_beam_alone(self, word_list, pattern_matcher_trie):
        """Test that hybrid performs at least as well as beam alone."""
        # Create simple grid
        grid = Grid(11)
        # Make most of it black to simplify
        for row in range(11):
            for col in range(11):
                if row < 3 and col < 3:
                    pass  # Leave white
                elif row == 1 and col == 1:
                    grid.set_black_square(row, col, enforce_symmetry=False)
                else:
                    grid.set_black_square(row, col, enforce_symmetry=False)

        # Both solvers draw from the module-level RNG unseeded
        # (`iterative_repair.py` and `beam_search/selection/value_ordering.py`
        # both call random.shuffle), so running them back to back samples two
        # INDEPENDENT searches. Hybrid ≥ an independent beam run is not a
        # property the code guarantees, and asserting it is a coin flip.
        #
        # Seeding both identically makes hybrid's own phase-1 beam reproduce the
        # standalone beam run, so what this asserts is hybrid's actual contract:
        # it returns the better of its beam and repair phases
        # (`hybrid_autofill.py:200-215`), never worse than the beam it ran.
        #
        # Restore the RNG afterwards — a leaked seed would silently make every
        # later stochastic test in this process deterministic.
        rng_state = random.getstate()
        try:
            # Run beam search alone
            random.seed(_COMPARISON_SEED)
            beam = BeamSearchAutofill(grid.clone(), word_list, pattern_matcher_trie, beam_width=3)
            beam_result = beam.fill(timeout=20)

            # Run hybrid (beam + repair) from the same RNG position
            random.seed(_COMPARISON_SEED)
            hybrid = HybridAutofill(grid.clone(), word_list, pattern_matcher_trie, beam_width=3)
            hybrid_result = hybrid.fill(timeout=30)
        finally:
            random.setstate(rng_state)

        # Hybrid should be at least as good as the beam phase it ran
        assert (
            hybrid_result.slots_filled >= beam_result.slots_filled
        ), f"Hybrid ({hybrid_result.slots_filled}) should be ≥ beam ({beam_result.slots_filled})"

    def test_timeout_allocation(self, small_grid, word_list, pattern_matcher_trie):
        """Test that timeout is allocated correctly between phases."""
        hybrid = HybridAutofill(small_grid, word_list, pattern_matcher_trie, beam_width=2)

        # beam_timeout is capped at min(beam_cap, int(timeout * beam_timeout_ratio)) = 21s here;
        # repair_timeout is whatever remains of the 30s budget after beam actually finishes
        # (beam typically returns well before its cap, so repair gets most of the 30s -- see
        # hybrid_autofill.py:_compute_beam_cap and the repair_timeout calculation in fill()).
        result = hybrid.fill(timeout=30, beam_timeout_ratio=0.7, repair_timeout_ratio=0.3)

        # Just verify it completes without error
        assert isinstance(result.time_elapsed, float)
        assert result.time_elapsed <= 30 * 1.2  # Within 20% tolerance

    def test_fill_simple_grid(self, word_list, pattern_matcher_trie):
        """Test filling a simple grid end-to-end."""
        # Create very simple grid (3x3 with one black square)
        grid = Grid(11)
        # Make most of it black to simplify
        for row in range(11):
            for col in range(11):
                if row < 3 and col < 3:
                    pass  # Leave white
                elif row == 1 and col == 1:
                    grid.set_black_square(row, col, enforce_symmetry=False)
                else:
                    grid.set_black_square(row, col, enforce_symmetry=False)

        hybrid = HybridAutofill(
            grid,
            word_list,
            pattern_matcher_trie,
            beam_width=3,
            max_repair_iterations=50,
        )

        result = hybrid.fill(timeout=30)

        # Should make some progress
        assert result.slots_filled > 0, f"Expected some slots filled, got {result.slots_filled}"
        assert result.time_elapsed < 30.0


class TestBeamTimeoutScaling:
    """Test that beam timeout scales with grid size."""

    def test_small_grid_gets_short_beam_timeout(self):
        """11x11 grid should get beam_cap=30."""
        assert HybridAutofill._compute_beam_cap(11) == 30

    def test_large_grid_gets_long_beam_timeout(self):
        """21x21 grid should get beam_cap=120."""
        assert HybridAutofill._compute_beam_cap(21) == 120

    def test_standard_grid_beam_timeout(self):
        """15x15 grid should get beam_cap=66."""
        assert HybridAutofill._compute_beam_cap(15) == 66

    def test_nonstandard_grid_beam_timeout(self):
        """19x19 grid should get beam_cap=102 (linear interpolation)."""
        assert HybridAutofill._compute_beam_cap(19) == 102
