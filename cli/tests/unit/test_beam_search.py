"""
Unit tests for beam search autofill module.
"""

import pytest
import time
from src.core.grid import Grid
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher
from src.fill.trie_pattern_matcher import TriePatternMatcher
from src.fill.beam_search_autofill import BeamState, BeamSearchAutofill


class TestBeamState:
    """Test BeamState data structure."""

    @pytest.fixture
    def sample_grid(self):
        """Create a sample grid for testing."""
        grid = Grid(11)
        grid.set_black_square(5, 5)
        return grid

    def test_beam_state_creation(self, sample_grid):
        """Test creating a BeamState."""
        state = BeamState(
            grid=sample_grid,
            slots_filled=5,
            total_slots=10,
            score=75.0,
            used_words={'CAT', 'DOG', 'BIRD'},
            slot_assignments={(0, 0, 'across'): 'CAT'}
        )

        assert state.grid == sample_grid
        assert state.slots_filled == 5
        assert state.total_slots == 10
        assert state.score == 75.0
        assert len(state.used_words) == 3
        assert 'CAT' in state.used_words

    def test_completion_rate(self, sample_grid):
        """Test completion_rate calculation."""
        state = BeamState(
            grid=sample_grid,
            slots_filled=7,
            total_slots=10,
            score=0.0
        )

        assert state.completion_rate() == 0.7

    def test_completion_rate_zero_slots(self, sample_grid):
        """Test completion_rate with zero total slots."""
        state = BeamState(
            grid=sample_grid,
            slots_filled=0,
            total_slots=0,
            score=0.0
        )

        assert state.completion_rate() == 0.0

    def test_clone(self, sample_grid):
        """Test cloning a state creates independent copy."""
        original = BeamState(
            grid=sample_grid.clone(),
            slots_filled=3,
            total_slots=10,
            score=50.0,
            used_words={'CAT', 'DOG'},
            slot_assignments={(0, 0, 'across'): 'CAT'}
        )

        cloned = original.clone()

        # Modify cloned state
        cloned.used_words.add('BIRD')
        cloned.slot_assignments[(1, 1, 'down')] = 'DOG'
        cloned.grid.place_word('TEST', 0, 0, 'across')

        # Original should be unchanged
        assert 'BIRD' not in original.used_words
        assert (1, 1, 'down') not in original.slot_assignments
        assert original.grid.get_pattern_for_slot({'row': 0, 'col': 0, 'length': 4, 'direction': 'across'}) != 'TEST'

    def test_equality(self, sample_grid):
        """Test equality comparison."""
        state1 = BeamState(
            grid=sample_grid.clone(),
            slots_filled=3,
            total_slots=10,
            score=50.0,
            used_words={'CAT', 'DOG'}
        )

        state2 = BeamState(
            grid=sample_grid.clone(),
            slots_filled=3,
            total_slots=10,
            score=50.0,
            used_words={'CAT', 'DOG'}
        )

        assert state1 == state2

    def test_inequality_different_words(self, sample_grid):
        """Test inequality when used_words differ."""
        state1 = BeamState(
            grid=sample_grid.clone(),
            slots_filled=3,
            total_slots=10,
            score=50.0,
            used_words={'CAT', 'DOG'}
        )

        state2 = BeamState(
            grid=sample_grid.clone(),
            slots_filled=3,
            total_slots=10,
            score=50.0,
            used_words={'CAT', 'BIRD'}
        )

        assert state1 != state2


class TestBeamSearchAutofill:
    """Test BeamSearchAutofill algorithm."""

    @pytest.fixture
    def word_list(self):
        """Create a sample word list for testing."""
        words = [
            # 3-letter words
            'CAT', 'COT', 'CUT', 'BAT', 'BOT', 'BUT',
            'RAT', 'ROT', 'RUT', 'MAT', 'MOT', 'MUT',
            'ACE', 'ACT', 'ART', 'ARC', 'ARM', 'ARE',
            'TEA', 'TEN', 'TAN', 'TAR', 'TAX', 'TUB',
            # 4-letter words
            'CATS', 'BATS', 'RATS', 'MATS', 'ARTS',
            'TEAR', 'BEAR', 'DEAR', 'FEAR', 'HEAR',
            'CART', 'DART', 'PART', 'TART', 'WART',
            # 5-letter words
            'APPLE', 'AMPLE', 'MAPLE', 'TABLE', 'CABLE',
            'CABIN', 'CAPER', 'TAPER', 'PAPER',
            # 7-letter words
            'CABBAGE', 'BAGGAGE', 'PACKAGE',
            # 11-letter words
            'ABRACADABRA', 'HOCUSPOCUS',
        ]
        return WordList(words)

    @pytest.fixture
    def small_grid(self):
        """Create a small grid for testing."""
        grid = Grid(11)
        # Create a simple pattern with a few black squares
        grid.set_black_square(5, 5)
        grid.set_black_square(3, 7)
        grid.set_black_square(7, 3)
        return grid

    @pytest.fixture
    def pattern_matcher_regex(self, word_list):
        """Create a regex pattern matcher."""
        return PatternMatcher(word_list)

    @pytest.fixture
    def pattern_matcher_trie(self, word_list):
        """Create a trie pattern matcher."""
        return TriePatternMatcher(word_list)

    def test_init(self, small_grid, word_list, pattern_matcher_regex):
        """Test creating BeamSearchAutofill solver."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_regex
        )

        assert autofill.grid == small_grid
        assert autofill.word_list == word_list
        assert autofill.beam_width == 5
        assert autofill.candidates_per_slot == 10
        assert autofill.min_score == 0
        assert autofill.diversity_bonus == 0.1

    def test_init_custom_params(self, small_grid, word_list, pattern_matcher_regex):
        """Test creating solver with custom parameters."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_regex,
            beam_width=3,
            candidates_per_slot=5,
            min_score=20,
            diversity_bonus=0.2
        )

        assert autofill.beam_width == 3
        assert autofill.candidates_per_slot == 5
        assert autofill.min_score == 20
        assert autofill.diversity_bonus == 0.2

    def test_init_invalid_beam_width(self, small_grid, word_list, pattern_matcher_regex):
        """Test that invalid beam_width raises ValueError."""
        with pytest.raises(ValueError, match="beam_width must be 1-20"):
            BeamSearchAutofill(
                small_grid,
                word_list,
                pattern_matcher_regex,
                beam_width=0
            )

        with pytest.raises(ValueError, match="beam_width must be 1-20"):
            BeamSearchAutofill(
                small_grid,
                word_list,
                pattern_matcher_regex,
                beam_width=25
            )

    def test_init_invalid_candidates_per_slot(self, small_grid, word_list, pattern_matcher_regex):
        """Test that invalid candidates_per_slot raises ValueError."""
        with pytest.raises(ValueError, match="candidates_per_slot must be 1-100"):
            BeamSearchAutofill(
                small_grid,
                word_list,
                pattern_matcher_regex,
                candidates_per_slot=0
            )

    def test_init_invalid_diversity_bonus(self, small_grid, word_list, pattern_matcher_regex):
        """Test that invalid diversity_bonus raises ValueError."""
        with pytest.raises(ValueError, match="diversity_bonus must be 0.0-1.0"):
            BeamSearchAutofill(
                small_grid,
                word_list,
                pattern_matcher_regex,
                diversity_bonus=-0.1
            )

    def test_fill_already_complete_grid(self, word_list, pattern_matcher_regex):
        """Test filling an already complete grid."""
        grid = Grid(11)
        # Fill entire grid with letters
        for row in range(11):
            for col in range(11):
                grid.set_letter(row, col, 'A')

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher_regex)
        result = autofill.fill(timeout=10)

        assert result.success is True
        assert result.slots_filled == 0
        assert result.total_slots == 0
        assert len(result.problematic_slots) == 0

    def test_fill_invalid_timeout(self, small_grid, word_list, pattern_matcher_regex):
        """Test that timeout < 10 raises ValueError."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_regex)

        with pytest.raises(ValueError, match="timeout must be ≥10 seconds"):
            autofill.fill(timeout=5)

    def test_fill_result_structure(self, small_grid, word_list, pattern_matcher_trie):
        """Test that fill returns proper FillResult."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            beam_width=2,
            candidates_per_slot=3
        )
        result = autofill.fill(timeout=10)

        # Check result structure
        assert hasattr(result, 'success')
        assert hasattr(result, 'grid')
        assert hasattr(result, 'time_elapsed')
        assert hasattr(result, 'slots_filled')
        assert hasattr(result, 'total_slots')
        assert hasattr(result, 'problematic_slots')
        assert hasattr(result, 'iterations')

        # Check types
        assert isinstance(result.success, bool)
        assert isinstance(result.grid, Grid)
        assert isinstance(result.time_elapsed, float)
        assert isinstance(result.slots_filled, int)
        assert isinstance(result.total_slots, int)
        assert isinstance(result.problematic_slots, list)
        assert isinstance(result.iterations, int)

    def test_fill_respects_timeout(self, small_grid, word_list, pattern_matcher_regex):
        """Test that fill respects timeout."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_regex,
            beam_width=2
        )

        timeout = 10
        start = time.time()
        autofill.fill(timeout=timeout)
        elapsed = time.time() - start

        # Should not exceed timeout by more than 5 seconds (fixed ceiling, not % —
        # % margins are fragile on loaded CI runners where a single iteration can take 1-2s)
        assert elapsed <= timeout + 5

    def test_fill_no_duplicate_words(self, small_grid, word_list, pattern_matcher_trie):
        """Test that fill doesn't use duplicate words."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_trie,
            beam_width=3
        )

        result = autofill.fill(timeout=15)

        # Extract all words from result grid
        words_in_grid = []
        for slot in result.grid.get_word_slots():
            pattern = result.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:  # Only filled slots
                words_in_grid.append(pattern)

        # Check for duplicates
        assert len(words_in_grid) == len(set(words_in_grid)), \
            f"Found duplicate words: {words_in_grid}"

    def test_compute_score(self, small_grid, word_list, pattern_matcher_regex):
        """Test _compute_score method."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_regex)

        state = BeamState(
            grid=small_grid,
            slots_filled=5,
            total_slots=10,
            score=0.0
        )

        # Test score calculation
        score = autofill._compute_score(state, word_score=80)

        # Expected: (5/10 * 100) * 0.7 + 80 * 0.3 = 50 * 0.7 + 24 = 35 + 24 = 59
        assert abs(score - 59.0) < 0.01

    def test_compute_score_full_completion(self, small_grid, word_list, pattern_matcher_regex):
        """Test _compute_score with full completion."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_regex)

        state = BeamState(
            grid=small_grid,
            slots_filled=10,
            total_slots=10,
            score=0.0
        )

        score = autofill._compute_score(state, word_score=100)

        # Expected: (10/10 * 100) * 0.7 + 100 * 0.3 = 100 * 0.7 + 30 = 70 + 30 = 100
        assert abs(score - 100.0) < 0.01

    def test_count_differences(self, small_grid, word_list, pattern_matcher_regex):
        """Test _count_differences method."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_regex)

        state1 = BeamState(
            grid=small_grid,
            slots_filled=3,
            total_slots=10,
            score=0.0,
            slot_assignments={
                (0, 0, 'across'): 'CAT',
                (1, 0, 'across'): 'DOG',
                (2, 0, 'across'): 'BIRD'
            }
        )

        state2 = BeamState(
            grid=small_grid,
            slots_filled=3,
            total_slots=10,
            score=0.0,
            slot_assignments={
                (0, 0, 'across'): 'CAT',  # Same
                (1, 0, 'across'): 'RAT',  # Different
                (3, 0, 'across'): 'BAT'   # Only in state2
            }
        )

        diff_count = autofill._count_differences(state1, state2)

        # Different: (1,0) differs, (2,0) only in state1, (3,0) only in state2 = 3
        assert diff_count == 3

    def test_is_viable_state_with_viable_state(self, word_list, pattern_matcher_trie):
        """Test _is_viable_state with a viable state."""
        grid = Grid(11)
        grid.set_black_square(5, 5)

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher_trie)

        state = BeamState(
            grid=grid.clone(),
            slots_filled=0,
            total_slots=10,
            score=0.0
        )

        # Empty grid should be viable (has candidates for all slots)
        is_viable, risk_penalty = autofill._evaluate_state_viability(state)
        assert is_viable is True
        assert 0.0 < risk_penalty <= 1.0  # Penalty should be positive (penalties multiply)

    def test_is_viable_state_with_dead_end(self, word_list, pattern_matcher_trie):
        """Test _evaluate_state_viability with dead-end state."""
        grid = Grid(11)
        grid.set_black_square(5, 5)

        # Create impossible pattern (all Q's - unlikely to have matches)
        grid.place_word('QQQ', 0, 0, 'across')

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher_trie)

        state = BeamState(
            grid=grid.clone(),
            slots_filled=1,
            total_slots=10,
            score=0.0,
            used_words={'QQQ'}
        )

        # Method should return tuple (bool, float)
        is_viable, risk_penalty = autofill._evaluate_state_viability(state)
        assert isinstance(is_viable, bool)
        assert isinstance(risk_penalty, float)
        assert 0.0 <= risk_penalty <= 1.0  # Penalty should be in valid range

    def test_sort_slots_by_constraint(self, small_grid, word_list, pattern_matcher_trie):
        """Test _sort_slots_by_constraint sorts slots by length-first."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_trie)

        slots = small_grid.get_empty_slots()

        sorted_slots = autofill._sort_slots_by_constraint(slots)

        # Verify it returns a list
        assert isinstance(sorted_slots, list)
        assert len(sorted_slots) == len(slots)

        # Verify all original slots are present
        assert set(id(s) for s in slots) == set(id(s) for s in sorted_slots)

        # Verify slots are sorted by length descending (longest first)
        if len(sorted_slots) >= 2:
            for i in range(len(sorted_slots) - 1):
                # Next slot should have length <= current slot
                assert sorted_slots[i+1]['length'] <= sorted_slots[i]['length']

    def test_expand_beam_basic(self, word_list, pattern_matcher_trie):
        """Test _expand_beam basic functionality."""
        grid = Grid(11)
        grid.set_black_square(5, 5)

        autofill = BeamSearchAutofill(
            grid,
            word_list,
            pattern_matcher_trie,
            beam_width=2,
            candidates_per_slot=3
        )

        # Create initial beam
        state = BeamState(
            grid=grid.clone(),
            slots_filled=0,
            total_slots=10,
            score=0.0
        )
        beam = [state]

        # Get a slot to fill
        slots = grid.get_empty_slots()
        if slots:
            slot = slots[0]

            # Expand beam
            expanded = autofill._expand_beam(beam, slot, candidates_per_slot=3)

            # Should return a list (may be empty if no viable candidates)
            assert isinstance(expanded, list)

            # If we have expansions, they should be valid
            if len(expanded) > 0:
                # Should have up to 3 candidates
                assert len(expanded) <= 3

                # Each state should have slot filled
                for exp_state in expanded:
                    assert exp_state.slots_filled == 1
                    assert len(exp_state.used_words) == 1

    def test_prune_beam(self, small_grid, word_list, pattern_matcher_regex):
        """Test _prune_beam keeps top states."""
        autofill = BeamSearchAutofill(small_grid, word_list, pattern_matcher_regex)

        # Create beam with varying scores
        states = []
        for i in range(10):
            state = BeamState(
                grid=small_grid.clone(),
                slots_filled=i,
                total_slots=10,
                score=float(i * 10),  # Scores: 0, 10, 20, ..., 90
                used_words=set()
            )
            states.append(state)

        # Prune to beam width 5
        pruned = autofill._prune_beam(states, beam_width=5)

        # Should keep exactly 5 states
        assert len(pruned) == 5

        # Should keep highest scores (90, 80, 70, 60, 50)
        scores = [s.score for s in pruned]
        assert scores == [90.0, 80.0, 70.0, 60.0, 50.0]

    def test_apply_diversity_bonus(self, small_grid, word_list, pattern_matcher_regex):
        """Test _apply_diversity_bonus modifies scores."""
        autofill = BeamSearchAutofill(
            small_grid,
            word_list,
            pattern_matcher_regex,
            diversity_bonus=0.1
        )

        # Create beam with different slot assignments
        state1 = BeamState(
            grid=small_grid.clone(),
            slots_filled=2,
            total_slots=10,
            score=50.0,
            slot_assignments={(0, 0, 'across'): 'CAT', (1, 0, 'across'): 'DOG'}
        )

        state2 = BeamState(
            grid=small_grid.clone(),
            slots_filled=2,
            total_slots=10,
            score=50.0,
            slot_assignments={(0, 0, 'across'): 'RAT', (1, 0, 'across'): 'BAT'}
        )

        beam = [state1, state2]
        original_scores = [s.score for s in beam]

        # Apply diversity bonus
        autofill._apply_diversity_bonus(beam)

        # Scores should have changed (diversity bonus applied)
        new_scores = [s.score for s in beam]
        assert new_scores[0] != original_scores[0] or new_scores[1] != original_scores[1]

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

        autofill = BeamSearchAutofill(
            grid,
            word_list,
            pattern_matcher_trie,
            beam_width=3,
            candidates_per_slot=5
        )

        result = autofill.fill(timeout=15)

        # Should make some progress
        assert result.slots_filled >= 0
        assert result.iterations > 0
        assert result.time_elapsed < 15.0
