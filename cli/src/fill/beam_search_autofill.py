"""
Beam search autofill engine for crossword grids.

BACKWARD COMPATIBILITY WRAPPER - This module now delegates to BeamSearchOrchestrator.

The original 1,989-line god class has been refactored into focused components.
This wrapper maintains the original API for backward compatibility.
"""

import logging
from typing import Dict, Optional, Tuple

from ..core.grid import Grid
from .word_list import WordList
from .pattern_matcher import PatternMatcher
from .beam_search.orchestrator import BeamSearchOrchestrator
from .beam_search.state import BeamState

# Module-level logger for backward compatibility with tests
logger = logging.getLogger(__name__)

# Re-export BeamState for backward compatibility
__all__ = ["BeamSearchAutofill", "BeamState"]


class BeamSearchAutofill(BeamSearchOrchestrator):
    """
    Beam search solver for crossword grids.

    BACKWARD COMPATIBILITY WRAPPER - Inherits from BeamSearchOrchestrator.

    This class now simply inherits all functionality from BeamSearchOrchestrator,
    which composes the refactored components:
    - SlotSelector (MRV selection)
    - ConstraintEngine (MAC propagation)
    - ValueOrdering (LCV + stratified shuffling)
    - DiversityManager (beam diversity)
    - StateEvaluator (viability + quality)
    - BeamManager (expansion + pruning)

    The original monolithic implementation has been decomposed into these
    focused, testable components while maintaining the same external API.

    Algorithm:
    1. Initialize beam with beam_width empty grids
    2. For each slot (in MRV order):
        a. Expand: Try top-K words in each beam state
        b. Prune: Keep only top beam_width diverse states
        c. Check: Stop if any state is complete
    3. Return best state (most slots filled)
    """

    def __init__(
        self,
        grid: Grid,
        word_list: WordList,
        pattern_matcher: PatternMatcher,
        beam_width: int = 5,
        candidates_per_slot: int = 10,
        min_score: int = 0,
        diversity_bonus: float = 0.1,
        progress_reporter=None,
        theme_entries: Optional[Dict[Tuple[int, int, str], str]] = None,
        theme_words=None,
        partial_fill_mode: bool = False,
    ):
        """
        Initialize beam search solver.

        All parameters are forwarded to BeamSearchOrchestrator.

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine (trie or regex)
            beam_width: Number of parallel solutions (default: 5)
            candidates_per_slot: Top-K words to try per slot (default: 10)
            min_score: Minimum word quality score (default: 0)
            diversity_bonus: Bonus for diverse beams 0.0-1.0 (default: 0.1)
            progress_reporter: Optional progress reporting
            theme_entries: Dict of theme entries {(row, col, direction): word}
                          These are NON-NEGOTIABLE and will be placed first
            theme_words: Set of words from theme wordlist to prioritize (optional)
            partial_fill_mode: Enable partial fill mode - stops when stuck instead of aggressive backtracking

        Raises:
            ValueError: If parameters out of valid ranges
        """
        # Simply delegate to the orchestrator
        super().__init__(
            grid=grid,
            word_list=word_list,
            pattern_matcher=pattern_matcher,
            beam_width=beam_width,
            candidates_per_slot=candidates_per_slot,
            min_score=min_score,
            diversity_bonus=diversity_bonus,
            progress_reporter=progress_reporter,
            theme_entries=theme_entries,
            theme_words=theme_words,
            partial_fill_mode=partial_fill_mode,
        )

    # The fill() method and all other methods are inherited from BeamSearchOrchestrator
    # No code duplication needed - the orchestrator handles everything!

    # Backward compatibility proxy methods for tests
    # These delegate to the appropriate components

    def _compute_score(self, state: BeamState, word_score: int) -> float:
        """Proxy to StateEvaluator.compute_score() for backward compatibility."""
        return self.state_evaluator.compute_score(state, word_score)

    def _evaluate_state_viability(self, state: BeamState, last_filled_slot=None):
        """Proxy to StateEvaluator.evaluate_state_viability() for backward compatibility."""
        return self.state_evaluator.evaluate_state_viability(state, last_filled_slot)

    def _count_differences(self, state1: BeamState, state2: BeamState) -> int:
        """Proxy to DiversityManager.count_differences() for backward compatibility."""
        return self.diversity_manager.count_differences(state1, state2)

    def _sort_slots_by_constraint(self, slots, grid=None):
        """Proxy to SlotSelector.order_slots() for backward compatibility."""
        if grid is None:
            grid = self.grid
        return self.slot_selector.order_slots(slots, grid)

    def _expand_beam(self, beam, slot, candidates_per_slot):
        """Proxy to BeamManager.expand_beam() for backward compatibility."""
        return self.beam_manager.expand_beam(beam, slot, candidates_per_slot)

    def _prune_beam(self, beam, beam_width):
        """Proxy to BeamManager.prune_beam() for backward compatibility."""
        return self.beam_manager.prune_beam(beam, beam_width)

    def _apply_diversity_bonus(self, beam, slot=None):
        """
        Apply diversity bonus to beam states (for backward compatibility).

        Modifies beam state scores in-place to add diversity bonuses.
        This is a simplified version for test compatibility.
        """
        if len(beam) <= 1:
            return beam

        # Calculate pairwise diversity and apply bonuses
        for i, state in enumerate(beam):
            diversity_bonus = 0.0
            for j, other in enumerate(beam):
                if i != j:
                    diff_count = self.diversity_manager.count_differences(state, other)
                    diversity_bonus += diff_count * self.diversity_bonus

            # Apply average diversity bonus
            if len(beam) > 1:
                avg_bonus = diversity_bonus / (len(beam) - 1)
                state.score += avg_bonus

        return beam

    def _is_gibberish_pattern(self, word: str) -> bool:
        """
        Proxy to StateEvaluator.is_gibberish_pattern() for backward compatibility.

        Check if a pattern contains obvious gibberish (repeated letters, impossible clusters).

        Args:
            word: Word or pattern to check (may contain '?' wildcards)

        Returns:
            True if pattern appears to be gibberish

        Examples:
            AAAAA -> True (all same letter)
            III -> True (all same letter)
            NNN -> True (all same letter)
            AAA?? -> True (repeated letters)
            HELLO -> False (valid word pattern)
            VISA -> False (valid word pattern)
        """
        return self.state_evaluator.is_gibberish_pattern(word)

    def _is_quality_word(self, word: str) -> bool:
        """
        Proxy to StateEvaluator.is_quality_word() for backward compatibility.

        Check if word is likely real (not gibberish).

        Uses linguistic heuristics to filter obvious gibberish:
        1. Vowel ratio (~40% in English)
        2. No excessive letter repetition
        3. No excessive consonant clusters
        4. Q followed by U (standard pattern)

        Args:
            word: Word to check (uppercase)

        Returns:
            True if word passes quality checks, False if likely gibberish

        Examples:
            QZXRTPL -> False (no vowels)
            AAAAAN -> False (repeated letters)
            NNRRRN -> False (excessive repetition)
            HELLO -> True (valid word)
            WORLD -> True (valid word)
            PYTHON -> True (valid word)
        """
        return self.state_evaluator.is_quality_word(word)
