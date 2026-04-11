"""
Hybrid autofill combining beam search and iterative repair.

Two-phase approach: beam search (20% of timeout, capped per grid size)
then iterative repair (remaining time). Returns best result from either phase.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .autofill import FillResult

from ..core.grid import Grid
from .beam_search_autofill import BeamSearchAutofill
from .iterative_repair import IterativeRepair
from .pattern_matcher import PatternMatcher
from .word_list import WordList


class HybridAutofill:
    """
    Hybrid solver: beam search then iterative repair.

    Phase 1: Beam search with 20% of timeout (capped by grid size).
    Phase 2: Iterative repair with remaining time.
    Returns best result from either phase.
    """

    def __init__(
        self,
        grid: Grid,
        word_list: WordList,
        pattern_matcher: PatternMatcher,
        min_score: int = 0,
        beam_width: int = 5,
        max_repair_iterations: int = 500,
        progress_reporter=None,
        theme_entries=None,
        theme_words=None,
        all_valid_words: set = None,
    ):
        """
        Initialize hybrid autofill solver.

        Args:
            grid: Grid to fill
            word_list: Available words
            pattern_matcher: Pattern matching engine
            min_score: Minimum word quality score (default: 0)
            beam_width: Beam search parameter (default: 5)
            max_repair_iterations: Repair parameter (default: 500)
            progress_reporter: Optional progress reporting
            theme_entries: Dict of theme entries {(row, col, direction): word} (optional)
            theme_words: Set of words from theme wordlist to prioritize (optional)
            all_valid_words: Set of ALL valid words across all wordlists (for validation only)
        """
        self.grid = grid
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher
        self.min_score = min_score
        self.beam_width = beam_width
        self.max_repair_iterations = max_repair_iterations
        self.progress_reporter = progress_reporter
        self.theme_entries = theme_entries
        self.all_valid_words = all_valid_words or set()
        self.theme_words = theme_words or set()

    @staticmethod
    def _compute_beam_cap(size: int) -> int:
        """Compute beam timeout cap for a given grid size.

        Linear scale: 30s at size 11, +9s per size step, max 120s.
        Examples: 11→30, 15→66, 19→102, 21→120
        """
        return min(120, max(30, (size - 11) * 9 + 30))

    def fill(
        self,
        timeout: int = 300,
        beam_timeout_ratio: float = 0.2,
        repair_timeout_ratio: float = 0.8,
    ) -> FillResult:
        """
        Fill grid using hybrid approach.

        Args:
            timeout: Total time budget in seconds (minimum 30)
            beam_timeout_ratio: Fraction of time for beam search (default: 0.2)
            repair_timeout_ratio: Fraction of time for repair (default: 0.8)

        Returns:
            FillResult with best solution found

        Raises:
            ValueError: If timeout < 30 or beam_timeout_ratio + repair_timeout_ratio > 1.0
        """

        # Validate parameters
        if timeout < 30:
            raise ValueError(f"timeout must be ≥30 seconds for hybrid, got {timeout}")
        if beam_timeout_ratio + repair_timeout_ratio > 1.0:
            raise ValueError(
                "beam_timeout_ratio + repair_timeout_ratio must be ≤1.0, "
                f"got {beam_timeout_ratio} + {repair_timeout_ratio} = "
                f"{beam_timeout_ratio + repair_timeout_ratio}"
            )

        time.time()

        # Scale beam timeout cap with grid size (linear: 30s at size 11, +9s per size step, max 120s)
        beam_cap = self._compute_beam_cap(self.grid.size)
        beam_timeout = min(beam_cap, max(10, int(timeout * beam_timeout_ratio)))
        repair_timeout = max(10, timeout - beam_timeout)

        # Phase 1: Beam Search
        if self.progress_reporter:
            self.progress_reporter.update(0, "Phase 1: Beam search")

        beam_search = BeamSearchAutofill(
            self.grid.clone(),  # Clone to avoid modifying original
            self.word_list,
            self.pattern_matcher,
            beam_width=self.beam_width,
            min_score=self.min_score,
            progress_reporter=self.progress_reporter,
            theme_entries=self.theme_entries,
            theme_words=self.theme_words,
        )

        beam_result = beam_search.fill(timeout=beam_timeout)

        # Early exit if beam search succeeded
        if beam_result.success:
            if self.progress_reporter:
                self.progress_reporter.update(
                    100,
                    f"Beam search complete: {beam_result.slots_filled}/{beam_result.total_slots}",
                )
            return beam_result

        # Phase 2: Iterative Repair (start from beam result)
        if self.progress_reporter:
            self.progress_reporter.update(
                70,
                f"Phase 2: Repair ({beam_result.slots_filled}/{beam_result.total_slots} filled)",
            )

        # Use beam result grid as starting point
        repair = IterativeRepair(
            beam_result.grid,  # Start from beam output
            self.word_list,
            self.pattern_matcher,
            min_score=self.min_score,
            max_iterations=self.max_repair_iterations,
            progress_reporter=self.progress_reporter,
            theme_entries=self.theme_entries,
            theme_words=self.theme_words,
            all_valid_words=self.all_valid_words,
        )

        repair_result = repair.fill(timeout=repair_timeout)

        # Return best result
        if repair_result.success:
            # Repair succeeded - use it
            if self.progress_reporter:
                self.progress_reporter.update(
                    100,
                    f"Repair complete: {repair_result.slots_filled}/{repair_result.total_slots}",
                )
            return repair_result
        elif repair_result.slots_filled >= beam_result.slots_filled:
            # Repair improved or maintained - use it
            if self.progress_reporter:
                self.progress_reporter.update(
                    100,
                    f"Repair improved: {repair_result.slots_filled}/{repair_result.total_slots}",
                )
            return repair_result
        else:
            # Beam was better - use beam result
            if self.progress_reporter:
                self.progress_reporter.update(
                    100,
                    f"Beam best: {beam_result.slots_filled}/{beam_result.total_slots}",
                )
            return beam_result
