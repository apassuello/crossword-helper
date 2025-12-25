"""
BeamSearchOrchestrator - Main coordinator for beam search.

This module coordinates all beam search components to fill crossword grids.
"""

from typing import List, Tuple, Dict, Optional, Set
import time
import logging

from ...core.grid import Grid
from ..word_list import WordList
from ..pattern_matcher import PatternMatcher
from .state import BeamState
from .selection.slot_selector import MRVSlotSelector
from .constraints.engine import MACConstraintEngine
from .selection.value_ordering import CompositeValueOrdering, LCVValueOrdering, StratifiedValueOrdering
from .beam.diversity import DiversityManager
from .beam.manager import BeamManager
from .evaluation.state_evaluator import StateEvaluator
from .utils.slot_utils import SlotIntersectionHelper

logger = logging.getLogger(__name__)


class BeamSearchOrchestrator:
    """
    Main coordinator for beam search crossword filling.

    Composes all beam search components and orchestrates the search process.
    Uses dependency injection for all components to enable testing and flexibility.
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
        Initialize beam search orchestrator.

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine
            beam_width: Number of parallel solutions (default: 5)
            candidates_per_slot: Top-K words to try per slot (default: 10)
            min_score: Minimum word quality score (default: 0)
            diversity_bonus: Bonus for diverse beams 0.0-1.0 (default: 0.1)
            progress_reporter: Optional progress reporting
            theme_entries: Dict of theme entries {(row, col, direction): word}

        Raises:
            ValueError: If parameters out of valid ranges
        """
        # Validate parameters
        if beam_width < 1 or beam_width > 20:
            raise ValueError(f"beam_width must be 1-20, got {beam_width}")
        if candidates_per_slot < 1 or candidates_per_slot > 100:
            raise ValueError(f"candidates_per_slot must be 1-100, got {candidates_per_slot}")
        if min_score < 0 or min_score > 100:
            raise ValueError(f"min_score must be 0-100, got {min_score}")
        if diversity_bonus < 0.0 or diversity_bonus > 1.0:
            raise ValueError(f"diversity_bonus must be 0.0-1.0, got {diversity_bonus}")

        self.grid = grid
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher
        self.beam_width = beam_width
        self.candidates_per_slot = candidates_per_slot
        self.min_score = min_score
        self.diversity_bonus = diversity_bonus
        self.progress_reporter = progress_reporter
        self.theme_entries = theme_entries or {}

        # State tracking
        self.start_time = 0.0
        self.iterations = 0

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all search components."""
        # Slot selection
        self.slot_selector = MRVSlotSelector(
            pattern_matcher=self.pattern_matcher,
            get_min_score_func=self._get_min_score_for_length
        )

        # Constraint propagation
        self.constraint_engine = MACConstraintEngine(
            pattern_matcher=self.pattern_matcher
        )

        # Value ordering (composite strategy: LCV + stratified shuffling)
        lcv_ordering = LCVValueOrdering(
            pattern_matcher=self.pattern_matcher,
            min_score_func=self._get_min_score_for_length
        )
        stratified_ordering = StratifiedValueOrdering(tier_size=5)
        self.value_ordering = CompositeValueOrdering([lcv_ordering, stratified_ordering])

        # Diversity management
        self.diversity_manager = DiversityManager()

        # State evaluation
        self.state_evaluator = StateEvaluator(
            pattern_matcher=self.pattern_matcher,
            get_min_score_func=self._get_min_score_for_length,
            get_intersecting_slots_func=SlotIntersectionHelper.get_intersecting_slots
        )

        # Beam management
        self.beam_manager = BeamManager(
            pattern_matcher=self.pattern_matcher,
            get_min_score_func=self._get_min_score_for_length,
            evaluate_viability_func=self.state_evaluator.evaluate_state_viability,
            compute_score_func=self.state_evaluator.compute_score,
            is_quality_word_func=self.state_evaluator.is_quality_word,
            base_beam_width=self.beam_width
        )

    def _get_min_score_for_length(self, length: int) -> int:
        """
        Return quality threshold appropriate for word length.

        Different word lengths require different quality standards.

        Args:
            length: Word length in letters

        Returns:
            Minimum score threshold for this length
        """
        if length <= 3:
            return 0    # Accept any word (crosswordese OK)
        elif length == 4:
            return 10   # Slightly filtered
        elif length <= 6:
            return 30   # Prefer common words
        elif length <= 8:
            return 50   # Common words only
        else:  # 9+ letters
            return 70   # High-quality phrases only

    def fill(self, timeout: int = 300):
        """
        Fill grid using beam search.

        Main orchestration method that coordinates all components.

        Args:
            timeout: Maximum seconds to spend

        Returns:
            FillResult with best solution found

        Raises:
            ValueError: If timeout < 10 seconds
        """
        from ..autofill import FillResult

        if timeout < 10:
            raise ValueError(f"timeout must be >=10 seconds, got {timeout}")

        self.start_time = time.time()
        self.iterations = 0

        # Get all empty slots
        all_slots = self.grid.get_empty_slots()
        total_slots = len(all_slots)

        # Early exit if already complete
        if total_slots == 0:
            return FillResult(
                success=True,
                grid=self.grid,
                time_elapsed=0.0,
                slots_filled=0,
                total_slots=0,
                problematic_slots=[],
                iterations=0
            )

        # Handle theme entries
        initial_grid, theme_slot_count, theme_slot_assignments, theme_words, sorted_slots = (
            self._prepare_initial_state(all_slots)
        )

        # Initialize beam
        initial_state = BeamState(
            grid=initial_grid,
            slots_filled=theme_slot_count,
            total_slots=total_slots,
            score=100.0 * theme_slot_count,
            used_words=theme_words.copy(),
            slot_assignments=theme_slot_assignments.copy()
        )
        beam = [initial_state.clone() for _ in range(self.beam_width)]

        logger.debug(f"\nDEBUG: Using DYNAMIC MRV variable ordering")
        logger.debug(f"Total slots to fill: {total_slots}")

        # Main beam search loop
        filled_slots = set(self.theme_entries.keys())
        slot_idx = 0

        while len(filled_slots) < total_slots:
            self.iterations += 1
            slot_idx += 1

            # Check timeout
            if time.time() - self.start_time > timeout:
                break

            # Select next slot (Dynamic MRV)
            unfilled_slots = [s for s in all_slots
                             if (s['row'], s['col'], s['direction']) not in filled_slots]

            if not unfilled_slots:
                break

            slot = self.slot_selector.select_next_slot(unfilled_slots, beam[0])
            if slot is None:
                break

            slot_id = (slot['row'], slot['col'], slot['direction'])
            filled_slots.add(slot_id)

            # Progress reporting
            if self.progress_reporter:
                progress = int((len(filled_slots) / total_slots) * 90) + 10
                self.progress_reporter.update(
                    progress,
                    f"Beam search: slot {len(filled_slots)}/{total_slots}"
                )

            # Expand beam
            expanded_beam = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot)

            # Backtracking if needed
            if not expanded_beam and slot_idx > 0:
                expanded_beam = self._try_backtracking(beam, slot)

            if not expanded_beam:
                logger.debug(f"\nDEBUG: Beam expansion failed at slot {slot_idx}! Exiting.")
                break

            # Adaptive beam width
            adaptive_width = self.beam_manager.get_adaptive_beam_width(
                beam, unfilled_slots, total_slots, slot
            )

            # Prune beam with diversity
            if len(expanded_beam) > adaptive_width:
                beam = self.diversity_manager.diverse_beam_prune(
                    expanded_beam, slot, adaptive_width, num_groups=4, diversity_lambda=0.5
                )
            else:
                beam = expanded_beam

            # Check for complete solution
            complete_states = [s for s in beam if s.slots_filled == total_slots]
            if complete_states:
                return self._create_result(
                    max(complete_states, key=lambda s: s.score),
                    all_slots,
                    total_slots,
                    success=True
                )

        # Return best partial solution
        best_state = max(beam, key=lambda s: (s.slots_filled, s.score))
        return self._create_result(best_state, all_slots, total_slots, success=False)

    def _prepare_initial_state(self, all_slots: List[Dict]) -> Tuple:
        """Prepare initial grid state with theme entries."""
        if self.theme_entries:
            sorted_slots, theme_words = self.slot_selector.prioritize_theme_entries(
                all_slots, self.theme_entries
            )
        else:
            sorted_slots = self.slot_selector.order_slots(all_slots)
            theme_words = set()

        # Pre-fill theme entries
        initial_grid = self.grid.clone()
        theme_slot_count = 0
        theme_slot_assignments = {}

        for slot_id, word in self.theme_entries.items():
            row, col, direction = slot_id
            initial_grid.place_word(word.upper(), row, col, direction)
            theme_slot_assignments[slot_id] = word.upper()
            theme_slot_count += 1

        return initial_grid, theme_slot_count, theme_slot_assignments, theme_words, sorted_slots

    def _try_backtracking(self, beam: List[BeamState], slot: Dict) -> List[BeamState]:
        """Try backtracking with more candidates if expansion fails."""
        logger.debug(f"\nDEBUG: Trying backtracking...")

        # Try 2x candidates
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 2)
        if expanded:
            return expanded

        # Try 5x candidates
        logger.debug(f"  Retry with 5x candidates...")
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 5)
        if expanded:
            return expanded

        # Try with no score filter
        logger.debug(f"  Retry with min_score=0...")
        old_min_score = self.min_score
        self.min_score = 0
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 10)
        self.min_score = old_min_score

        return expanded

    def _create_result(
        self,
        best_state: BeamState,
        all_slots: List[Dict],
        total_slots: int,
        success: bool
    ):
        """Create FillResult from best state."""
        from ..autofill import FillResult

        time_elapsed = time.time() - self.start_time

        # Find problematic slots
        problematic_slots = []
        if not success:
            for slot in all_slots:
                slot_id = (slot['row'], slot['col'], slot['direction'])
                if slot_id not in best_state.slot_assignments:
                    # Clear gibberish from unfilled slots
                    pattern = best_state.grid.get_pattern_for_slot(slot)
                    if self.state_evaluator.is_gibberish_pattern(pattern):
                        best_state.grid.remove_word(
                            slot['row'], slot['col'], slot['length'], slot['direction']
                        )
                    problematic_slots.append(slot)

        # Calculate actual filled slots
        actual_filled = sum(1 for slot in all_slots
                           if '?' not in best_state.grid.get_pattern_for_slot(slot))

        return FillResult(
            success=success,
            grid=best_state.grid,
            time_elapsed=time_elapsed,
            slots_filled=actual_filled,
            total_slots=total_slots,
            problematic_slots=problematic_slots,
            iterations=self.iterations
        )
