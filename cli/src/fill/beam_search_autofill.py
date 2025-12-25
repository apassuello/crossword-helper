"""
Beam search autofill engine for crossword grids.

BACKWARD COMPATIBILITY WRAPPER - This module now delegates to BeamSearchOrchestrator.

The original 1,989-line god class has been refactored into focused components.
This wrapper maintains the original API for backward compatibility.
"""

from typing import Dict, Optional, Tuple

from ..core.grid import Grid
from .word_list import WordList
from .pattern_matcher import PatternMatcher
from .beam_search.orchestrator import BeamSearchOrchestrator
from .beam_search.state import BeamState

# Re-export BeamState for backward compatibility
__all__ = ['BeamSearchAutofill', 'BeamState']


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
        theme_entries: Optional[Dict[Tuple[int, int, str], str]] = None
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
            theme_entries=theme_entries
        )

    # The fill() method and all other methods are inherited from BeamSearchOrchestrator
    # No code duplication needed - the orchestrator handles everything!
