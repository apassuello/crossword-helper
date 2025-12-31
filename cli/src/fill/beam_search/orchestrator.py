"""
BeamSearchOrchestrator - Main coordinator for beam search.

This module coordinates all beam search components to fill crossword grids.
"""

from typing import List, Tuple, Dict, Optional, Set
import time
import logging
import json

from ...core.grid import Grid
from ..word_list import WordList
from ..pattern_matcher import PatternMatcher
from .state import BeamState
from .selection.slot_selector import MRVSlotSelector
from .constraints.engine import MACConstraintEngine
from .selection.value_ordering import (
    CompositeValueOrdering,
    LCVValueOrdering,
    StratifiedValueOrdering,
    ThresholdDiverseOrdering,
    ThemeWordPriorityOrdering
)
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
        theme_entries: Optional[Dict[Tuple[int, int, str], str]] = None,
        theme_words=None,
        pause_controller=None,
        task_id: Optional[str] = None
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
            theme_words: Set of words from theme wordlist to prioritize (optional)
            pause_controller: Optional PauseController for pause/resume
            task_id: Optional task identifier for pause/resume

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
        self.theme_words = theme_words or set()
        self.pause_controller = pause_controller
        self.task_id = task_id

        # State tracking
        self.start_time = 0.0
        self.iterations = 0

        # Failure tracking (prevents thrashing on impossible slots)
        self.slot_attempt_history = {}  # (beam_signature, slot_id) -> attempt_count
        self.recently_failed = []  # List of recently failed slot_ids (for MRV deprioritization)
        self.max_attempts_per_slot = 3  # Max retries per (beam, slot) combination before backtracking

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all search components."""
        # Slot selection
        self.slot_selector = MRVSlotSelector(
            pattern_matcher=self.pattern_matcher,
            word_list=self.word_list,
            theme_entries=self.theme_entries
        )

        # Constraint propagation
        self.constraint_engine = MACConstraintEngine(
            pattern_matcher=self.pattern_matcher
        )

        # Value ordering (composite strategy: theme priority + LCV + threshold-diverse + stratified)
        # Phase 4.5: Added ThresholdDiverseOrdering for exploration-exploitation balance
        # Phase 5.1: Increased temperature to 0.8 for more exploration
        # Phase 3.4: Added ThemeWordPriorityOrdering for theme list prioritization
        theme_priority = ThemeWordPriorityOrdering(theme_words=self.theme_words)  # Phase 3.4
        lcv_ordering = LCVValueOrdering(
            pattern_matcher=self.pattern_matcher,
            min_score_func=self._get_min_score_for_length
        )
        threshold_ordering = ThresholdDiverseOrdering(threshold=50, temperature=0.8)  # Phase 5.1: Was 0.4
        stratified_ordering = StratifiedValueOrdering(tier_size=5)
        # Phase 4.5: Composite value ordering (theme priority FIRST, then LCV + threshold-diverse + stratified)
        self.value_ordering = CompositeValueOrdering([
            theme_priority,          # Phase 3.4: Theme words first (before LCV)
            lcv_ordering,           # Least constraining value (prefer words that leave options open)
            threshold_ordering,      # Threshold + temperature exploration (Phase 4.5)
            stratified_ordering      # Stratified shuffling for diversity
        ])

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
            base_beam_width=self.beam_width,
            value_ordering=self.value_ordering  # Phase 4.5: Wire up value ordering!
        )

    def _get_min_score_for_length(self, length: int) -> int:
        """
        Return quality threshold appropriate for word length.

        Respects user's --min-score setting as baseline, with 3-letter
        words allowed to be more lenient (crosswordese needed for fill).

        Args:
            length: Word length in letters

        Returns:
            Minimum score threshold for this length
        """
        if length <= 3:
            return 0    # Accept any word (crosswordese OK)
        else:
            # Use user's min_score for all other lengths
            return self.min_score

    def _get_beam_signature(self, beam: List[BeamState]) -> int:
        """
        Create signature representing current beam configuration.

        Uses the first beam state's slot assignments as a signature to identify
        unique (beam, slot) combinations. This prevents retrying the same slot
        with the same beam constraints.

        Args:
            beam: Current beam states

        Returns:
            Hash of beam configuration
        """
        if not beam:
            return hash(frozenset())

        # Use first beam state's assignments as signature
        assignments = frozenset(beam[0].slot_assignments.items())
        return hash(assignments)

    def fill(self, timeout: int = 300, resume_state=None):
        """
        Fill grid using beam search.

        Main orchestration method that coordinates all components.

        Args:
            timeout: Maximum seconds to spend
            resume_state: Optional BeamSearchState to resume from

        Returns:
            FillResult with best solution found

        Raises:
            ValueError: If timeout < 10 seconds
        """
        from ..autofill import FillResult

        if timeout < 10:
            raise ValueError(f"timeout must be ≥10 seconds, got {timeout}")

        # Check if resuming from saved state
        if resume_state is not None:
            return self._resume_fill(resume_state, timeout)

        self.start_time = time.time()
        self.iterations = 0
        self.failed_expansions = 0  # Phase 4.5: Track expansion failures
        self.max_failed_expansions = 10  # Phase 4.5: Allow 10 failures before giving up

        # Reset failure tracking for this fill attempt
        self.slot_attempt_history.clear()
        self.recently_failed.clear()

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

        logger.debug("\nDEBUG: Using DYNAMIC MRV variable ordering")
        logger.debug(f"Total slots to fill: {total_slots}")

        # Main beam search loop
        filled_slots = set(self.theme_entries.keys())
        slot_idx = 0

        while len(filled_slots) < total_slots:
            self.iterations += 1
            slot_idx += 1

            # Check for pause request (every 10 iterations for performance)
            if self.pause_controller and self.iterations % 10 == 0:
                if self.pause_controller.should_pause():
                    logger.info(f"Pause requested at iteration {self.iterations}")
                    # Save state before pausing
                    self._save_state_and_pause(
                        beam, filled_slots, slot_idx, all_slots, total_slots
                    )
                    # Return partial result with paused status
                    best_state = max(beam, key=lambda s: (s.slots_filled, s.score))
                    result = self._create_result(best_state, all_slots, total_slots, success=False)
                    result.paused = True  # Mark as paused
                    return result

            # Check timeout
            if time.time() - self.start_time > timeout:
                break

            # Select next slot (Dynamic MRV)
            unfilled_slots = [s for s in all_slots
                             if (s['row'], s['col'], s['direction']) not in filled_slots]

            if not unfilled_slots:
                break

            slot = self.slot_selector.select_next_slot(unfilled_slots, beam[0], recently_failed=self.recently_failed)
            if slot is None:
                break

            slot_id = (slot['row'], slot['col'], slot['direction'])
            filled_slots.add(slot_id)

            # Progress reporting with incremental grid updates
            if self.progress_reporter:
                progress = int((len(filled_slots) / total_slots) * 90) + 10
                self.progress_reporter.update(
                    progress,
                    f"Beam search: slot {len(filled_slots)}/{total_slots}",
                    'running',
                    {'grid': beam[0].grid.to_dict()['grid']}  # Send current grid state
                )

            # Expand beam
            expanded_beam = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot)

            # Backtracking if needed
            if not expanded_beam and slot_idx > 0:
                expanded_beam = self._try_backtracking(beam, slot)

            if not expanded_beam:
                # Track this failure to prevent thrashing on same (beam, slot) combination
                beam_sig = self._get_beam_signature(beam)
                attempt_key = (beam_sig, slot_id)

                # Increment attempt count for this specific (beam, slot) combination
                attempts = self.slot_attempt_history.get(attempt_key, 0) + 1
                self.slot_attempt_history[attempt_key] = attempts

                # Track in recently_failed list for MRV deprioritization
                if slot_id not in self.recently_failed:
                    self.recently_failed.insert(0, slot_id)
                    # Keep only last 5 failures
                    if len(self.recently_failed) > 5:
                        self.recently_failed.pop()

                logger.debug(f"\nWARNING: Beam expansion failed at slot {slot_id}")
                logger.debug(f"  Attempt {attempts}/{self.max_attempts_per_slot} for this (beam, slot) combination")
                logger.debug(f"  Recently failed slots: {self.recently_failed[:3]}")

                # If we haven't exhausted attempts for this combination, continue
                # MRV will now heavily penalize this slot and try alternatives
                if attempts < self.max_attempts_per_slot:
                    logger.debug(f"  Removing slot from filled_slots, MRV will deprioritize it (penalty={1000 * (len(self.recently_failed))})")
                    filled_slots.discard(slot_id)
                    continue

                # Attempts exhausted for this (beam, slot) - need proper backtracking
                logger.debug("  Max attempts reached for this slot, attempting backtracking...")

                # If no filled slots to backtrack from, we're stuck
                if len(filled_slots) == 0:
                    logger.debug("  No slots to backtrack from, grid may be impossible")
                    break

                # Proper CSP backtracking: undo last assignment(s)
                backtracked_beam = self._backtrack_beam_states(beam, depth=1)

                if not backtracked_beam:
                    logger.debug("  Backtracking failed, grid may be impossible")
                    break

                # Update beam to backtracked state
                beam = backtracked_beam

                # Remove the slot we just backtracked from filled_slots
                # (it's the most recently added slot to the backtracked state)
                if filled_slots:
                    # Find slots in beam that are no longer filled after backtracking
                    beam_filled_slots = set(beam[0].slot_assignments.keys())
                    removed_slots = filled_slots - beam_filled_slots
                    for removed_slot in removed_slots:
                        filled_slots.discard(removed_slot)
                        logger.debug(f"  Backtracked slot {removed_slot}")

                # Remove current failing slot from filled_slots too
                filled_slots.discard(slot_id)

                logger.debug(f"  Backtracking complete, now have {len(filled_slots)} filled slots")
                continue

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
                all_slots
            )
        else:
            sorted_slots = self.slot_selector.order_slots(all_slots, self.grid)
            theme_words = set()

        # Pre-fill theme entries
        initial_grid = self.grid.clone()
        theme_slot_count = 0
        theme_slot_assignments = {}

        for slot_id, word in self.theme_entries.items():
            row, col, direction = slot_id
            # THEME PRESERVATION FIX: Lock theme word cells to prevent overwriting
            initial_grid.place_word(word.upper(), row, col, direction, lock=True)
            theme_slot_assignments[slot_id] = word.upper()
            theme_slot_count += 1

            # THEME PRESERVATION FIX: Log theme entry placement
            logger.debug(f"Theme entry placed and LOCKED: {word.upper()} at {slot_id}")

        return initial_grid, theme_slot_count, theme_slot_assignments, theme_words, sorted_slots

    def _slot_overlaps_with_theme(self, slot: Dict) -> bool:
        """
        Check if a slot overlaps with any theme entry slots.

        This prevents the slot selector from choosing theme slots that
        should remain untouched.

        Args:
            slot: Slot to check {'row': int, 'col': int, 'direction': str, 'length': int}

        Returns:
            True if slot overlaps with any theme entry, False otherwise
        """
        slot_id = (slot['row'], slot['col'], slot['direction'])

        # Exact match
        if slot_id in self.theme_entries:
            return True

        # Check for partial overlaps (same position but different detected length)
        # This can happen if grid.get_empty_slots() splits a theme slot
        for theme_slot_id in self.theme_entries.keys():
            theme_row, theme_col, theme_dir = theme_slot_id
            if slot['row'] == theme_row and slot['col'] == theme_col and slot['direction'] == theme_dir:
                return True

        return False

    def _analyze_slot_conflicts(self, state: BeamState, slot: Dict) -> Set[Tuple[int, int, str]]:
        """
        Identify which filled slots are causing the current slot to have no valid candidates.

        This enables intelligent backjumping: instead of chronologically undoing the
        most recent assignment, we can jump back to the actual conflicting slot.

        Args:
            state: Current beam state
            slot: The slot that failed (has no valid candidates)

        Returns:
            Set of slot_ids (row, col, direction) that conflict with current slot
        """
        conflicts = set()
        pattern = state.grid.get_pattern_for_slot(slot)

        # Get all filled intersecting slots
        for slot_id, word in state.slot_assignments.items():
            row, col, direction = slot_id

            # Check if slots intersect
            if not self._slots_intersect(slot, {'row': row, 'col': col, 'direction': direction, 'length': len(word)}):
                continue

            # Find intersection positions
            intersection_pos_current, intersection_pos_other = self._get_intersection_positions(
                slot, {'row': row, 'col': col, 'direction': direction, 'length': len(word)}
            )

            if intersection_pos_current is None or intersection_pos_other is None:
                continue

            # Get the constraint letter from the intersecting word
            constraint_letter = word[intersection_pos_other]

            # Create pattern without this constraint
            pattern_list = list(pattern)
            pattern_without_constraint = pattern_list.copy()
            pattern_without_constraint[intersection_pos_current] = '?'
            pattern_without = ''.join(pattern_without_constraint)

            # Check if this constraint is eliminating all candidates
            min_score = self._get_min_score_for_length(slot['length'])
            candidates_without = self.pattern_matcher.find(pattern_without, min_score=0)  # Very lenient
            candidates_with = self.pattern_matcher.find(pattern, min_score=min_score)

            if len(candidates_without) > 0 and len(candidates_with) == 0:
                # This constraint is problematic - it's eliminating all candidates
                conflicts.add(slot_id)
                logger.debug(f"    Conflict detected: slot {slot_id} with letter '{constraint_letter}' at pos {intersection_pos_current}")

        logger.debug(f"  Analyzed conflicts for slot {(slot['row'], slot['col'], slot['direction'])}: found {len(conflicts)} conflicts")
        return conflicts

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """Check if two slots intersect."""
        # If same direction, they can't intersect (parallel)
        if slot1['direction'] == slot2['direction']:
            return False

        # Check if they overlap
        if slot1['direction'] == 'across':
            # slot1 is across (row fixed), slot2 is down (col fixed)
            # They intersect if slot1's row is in slot2's row range AND slot2's col is in slot1's col range
            across_row, across_col = slot1['row'], slot1['col']
            down_row, down_col = slot2['row'], slot2['col']

            return (down_col >= across_col and down_col < across_col + slot1['length'] and
                    across_row >= down_row and across_row < down_row + slot2['length'])
        else:
            # slot1 is down, slot2 is across
            return self._slots_intersect(slot2, slot1)

    def _get_intersection_positions(self, slot1: Dict, slot2: Dict) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the positions where two slots intersect.

        Returns:
            (position_in_slot1, position_in_slot2) or (None, None) if no intersection
        """
        if not self._slots_intersect(slot1, slot2):
            return (None, None)

        if slot1['direction'] == 'across':
            # slot1 is across, slot2 is down
            across_row, across_col = slot1['row'], slot1['col']
            down_row, down_col = slot2['row'], slot2['col']

            pos_in_across = down_col - across_col
            pos_in_down = across_row - down_row

            return (pos_in_across, pos_in_down)
        else:
            # slot1 is down, slot2 is across - swap and recurse
            pos2, pos1 = self._get_intersection_positions(slot2, slot1)
            return (pos1, pos2)

    def _backtrack_beam_states(self, beam: List[BeamState], depth: int = 1) -> List[BeamState]:
        """
        Perform true chronological backtracking by undoing recent slot assignments.

        Phase 4.5: This is REAL backtracking - undoes previous assignments
        to explore alternative paths, unlike fake backtracking that just
        tries more candidates for the same stuck slot.

        Args:
            beam: Current beam states
            depth: Number of slots to backtrack (undo)

        Returns:
            Beam with last 'depth' assignments removed, ready to retry
        """
        backtracked_beam = []

        for state in beam:
            if len(state.slot_assignments) < depth:
                # Can't backtrack this far, skip this state
                continue

            # Create new state with last 'depth' assignments removed
            new_state = state.clone()

            # Get last N assignments to remove (chronological order)
            sorted_assignments = sorted(
                state.slot_assignments.items(),
                key=lambda x: x  # Chronological order by slot_id
            )[-depth:]

            for slot_id, word in sorted_assignments:
                row, col, direction = slot_id
                word_length = len(word)

                # Remove word from grid
                new_state.grid.remove_word(row, col, word_length, direction)

                # Remove from tracking structures
                del new_state.slot_assignments[slot_id]
                new_state.used_words.discard(word)
                new_state.slots_filled -= 1

            backtracked_beam.append(new_state)

        logger.debug(f"  Backtracked {len(backtracked_beam)} states by depth={depth}")
        return backtracked_beam

    def _try_backtracking(self, beam: List[BeamState], slot: Dict) -> List[BeamState]:
        """
        Multi-level backtracking strategy with conflict analysis.

        Strategy progression:
        1. Try more candidates (relaxed constraints)
        2. Try with no score filter
        3. Conflict-directed backjumping (undo problematic assignments)
        4. Chronological backtracking (undo recent assignments)

        Returns:
            Expanded beam or empty list if all strategies fail
        """
        logger.debug("\nDEBUG: Trying backtracking strategies...")

        # Try 1: More candidates (2x)
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 2)
        if expanded:
            logger.debug("  ✓ Success with 2x candidates")
            return expanded

        # Try 2: Even more candidates (5x)
        logger.debug("  Trying 5x candidates...")
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 5)
        if expanded:
            logger.debug("  ✓ Success with 5x candidates")
            return expanded

        # Try 3: No score filter (accept any quality words)
        logger.debug("  Trying min_score=0...")
        old_min_score = self.min_score
        self.min_score = 0
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 10)
        self.min_score = old_min_score
        if expanded:
            logger.debug("  ✓ Success with no score filter")
            return expanded

        # Try 4: CONFLICT-DIRECTED BACKJUMPING (intelligent)
        # Analyze which filled slots are causing this failure and undo them
        logger.debug("  Analyzing conflicts for intelligent backjumping...")
        conflicts = self._analyze_slot_conflicts(beam[0], slot)

        if conflicts:
            logger.debug(f"  Found {len(conflicts)} conflicting slots, attempting backjump...")

            # Create backjumped beam by removing conflicting assignments
            backjumped_beam = []
            for state in beam:
                new_state = state.clone()

                # Remove all conflicting assignments
                for conflict_slot_id in conflicts:
                    if conflict_slot_id in new_state.slot_assignments:
                        word = new_state.slot_assignments[conflict_slot_id]
                        row, col, direction = conflict_slot_id
                        word_length = len(word)

                        # Remove word from grid
                        new_state.grid.remove_word(row, col, word_length, direction)

                        # Remove from tracking structures
                        del new_state.slot_assignments[conflict_slot_id]
                        new_state.used_words.discard(word)
                        new_state.slots_filled -= 1

                        logger.debug(f"    Removed conflicting slot {conflict_slot_id} (word={word})")

                backjumped_beam.append(new_state)

            # Try expanding from backjumped state
            expanded = self.beam_manager.expand_beam(backjumped_beam, slot, self.candidates_per_slot * 10)
            if expanded:
                logger.debug("  ✓ Success with conflict-directed backjumping")
                return expanded

        # Try 5: CHRONOLOGICAL BACKTRACKING - undo last assignment
        logger.debug("  Trying chronological backtracking (depth=1)...")
        backtracked_beam = self._backtrack_beam_states(beam, depth=1)
        if backtracked_beam:
            expanded = self.beam_manager.expand_beam(backtracked_beam, slot, self.candidates_per_slot * 10)
            if expanded:
                logger.debug("  ✓ Success with chronological backtracking (depth=1)")
                return expanded

        # Try 6: DEEPER CHRONOLOGICAL BACKTRACKING
        logger.debug("  Trying deeper chronological backtracking (depth=2)...")
        backtracked_beam = self._backtrack_beam_states(beam, depth=2)
        if backtracked_beam:
            expanded = self.beam_manager.expand_beam(backtracked_beam, slot, self.candidates_per_slot * 15)
            if expanded:
                logger.debug("  ✓ Success with chronological backtracking (depth=2)")
                return expanded

        # Try 7: VERY DEEP BACKTRACKING (last resort)
        logger.debug("  Trying very deep backtracking (depth=3)...")
        backtracked_beam = self._backtrack_beam_states(beam, depth=3)
        if backtracked_beam:
            expanded = self.beam_manager.expand_beam(backtracked_beam, slot, self.candidates_per_slot * 20)
            if expanded:
                logger.debug("  ✓ Success with deep backtracking (depth=3)")
                return expanded

        logger.debug("  ✗ All backtracking strategies failed")
        return []  # All backtracking strategies failed

    def _resume_fill(self, resume_state, timeout: int):
        """
        Resume beam search from saved state.

        Args:
            resume_state: BeamSearchState to resume from
            timeout: Maximum seconds to spend

        Returns:
            FillResult with best solution found
        """
        from ..state_manager import StateManager

        logger.info(f"Resuming beam search from iteration {resume_state.iterations}")

        # Restore configuration
        self.min_score = resume_state.min_score
        self.beam_width = resume_state.beam_width
        self.candidates_per_slot = resume_state.candidates_per_slot
        self.diversity_bonus = resume_state.diversity_bonus

        # Restore tracking state
        self.iterations = resume_state.iterations
        self.start_time = time.time()  # Fresh timeout

        # Restore failure tracking
        self.slot_attempt_history = {}
        for key_str, attempts in resume_state.slot_attempt_history.items():
            key_list = json.loads(key_str)
            beam_sig = key_list[0]
            slot_id = tuple(key_list[1])
            self.slot_attempt_history[(beam_sig, slot_id)] = attempts

        self.recently_failed = [tuple(slot_list) for slot_list in resume_state.recently_failed]

        # Restore theme entries
        self.theme_entries = {}
        for key_str, word in resume_state.theme_entries.items():
            slot_tuple = tuple(json.loads(key_str))
            self.theme_entries[slot_tuple] = word

        # Restore beam (deserialize BeamState objects)
        beam = [
            StateManager.deserialize_beam_state(beam_dict)
            for beam_dict in resume_state.beam
        ]

        # Restore filled_slots
        filled_slots = set(tuple(slot_list) for slot_list in resume_state.filled_slots)

        # Get all slots and restore metadata
        all_slots = resume_state.all_slots
        total_slots = resume_state.total_slots
        slot_idx = resume_state.slot_idx

        logger.info(f"Restored {len(beam)} beam states, {len(filled_slots)}/{total_slots} slots filled")

        # Continue the main beam search loop from where it paused
        while len(filled_slots) < total_slots:
            self.iterations += 1
            slot_idx += 1

            # Check for pause request (every 10 iterations for performance)
            if self.pause_controller and self.iterations % 10 == 0:
                if self.pause_controller.should_pause():
                    logger.info(f"Pause requested at iteration {self.iterations}")
                    # Save state before pausing
                    self._save_state_and_pause(
                        beam, filled_slots, slot_idx, all_slots, total_slots
                    )
                    # Return partial result with paused status
                    best_state = max(beam, key=lambda s: (s.slots_filled, s.score))
                    result = self._create_result(best_state, all_slots, total_slots, success=False)
                    result.paused = True  # Mark as paused
                    return result

            # Check timeout
            if time.time() - self.start_time > timeout:
                break

            # Select next slot (Dynamic MRV)
            unfilled_slots = [s for s in all_slots
                             if (s['row'], s['col'], s['direction']) not in filled_slots]

            if not unfilled_slots:
                break

            slot = self.slot_selector.select_next_slot(unfilled_slots, beam[0], recently_failed=self.recently_failed)
            if slot is None:
                break

            slot_id = (slot['row'], slot['col'], slot['direction'])
            filled_slots.add(slot_id)

            # Progress reporting with incremental grid updates
            if self.progress_reporter:
                progress = int((len(filled_slots) / total_slots) * 90) + 10
                self.progress_reporter.update(
                    progress,
                    f"Beam search (resumed): slot {len(filled_slots)}/{total_slots}",
                    'running',
                    {'grid': beam[0].grid.to_dict()['grid']}  # Send current grid state
                )

            # Expand beam
            expanded_beam = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot)

            # Backtracking if needed
            if not expanded_beam and slot_idx > 0:
                expanded_beam = self._try_backtracking(beam, slot)

            if not expanded_beam:
                # Track this failure to prevent thrashing on same (beam, slot) combination
                beam_sig = self._get_beam_signature(beam)
                attempt_key = (beam_sig, slot_id)

                # Increment attempt count for this specific (beam, slot) combination
                attempts = self.slot_attempt_history.get(attempt_key, 0) + 1
                self.slot_attempt_history[attempt_key] = attempts

                # Track in recently_failed list for MRV deprioritization
                if slot_id not in self.recently_failed:
                    self.recently_failed.insert(0, slot_id)
                    # Keep only last 5 failures
                    if len(self.recently_failed) > 5:
                        self.recently_failed.pop()

                logger.debug(f"\nWARNING: Beam expansion failed at slot {slot_id}")
                logger.debug(f"  Attempt {attempts}/{self.max_attempts_per_slot} for this (beam, slot) combination")
                logger.debug(f"  Recently failed slots: {self.recently_failed[:3]}")

                # If we haven't exhausted attempts for this combination, continue
                # MRV will now heavily penalize this slot and try alternatives
                if attempts < self.max_attempts_per_slot:
                    logger.debug(f"  Removing slot from filled_slots, MRV will deprioritize it (penalty={1000 * (len(self.recently_failed))})")
                    filled_slots.discard(slot_id)
                    continue

                # Attempts exhausted for this (beam, slot) - need proper backtracking
                logger.debug("  Max attempts reached for this slot, attempting backtracking...")

                # If no filled slots to backtrack from, we're stuck
                if len(filled_slots) == 0:
                    logger.debug("  No slots to backtrack from, grid may be impossible")
                    break

                # Proper CSP backtracking: undo last assignment(s)
                backtracked_beam = self._backtrack_beam_states(beam, depth=1)

                if not backtracked_beam:
                    logger.debug("  Backtracking failed, grid may be impossible")
                    break

                # Update beam to backtracked state
                beam = backtracked_beam

                # Remove the slot we just backtracked from filled_slots
                # (it's the most recently added slot to the backtracked state)
                if filled_slots:
                    # Find slots in beam that are no longer filled after backtracking
                    beam_filled_slots = set(beam[0].slot_assignments.keys())
                    removed_slots = filled_slots - beam_filled_slots
                    for removed_slot in removed_slots:
                        filled_slots.discard(removed_slot)
                        logger.debug(f"  Backtracked slot {removed_slot}")

                # Remove current failing slot from filled_slots too
                filled_slots.discard(slot_id)

                logger.debug(f"  Backtracking complete, now have {len(filled_slots)} filled slots")
                continue

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

    def _save_state_and_pause(
        self,
        beam: List[BeamState],
        filled_slots: Set,
        slot_idx: int,
        all_slots: List[Dict],
        total_slots: int
    ) -> None:
        """
        Save current beam search state to disk for pause/resume.

        Args:
            beam: Current beam states
            filled_slots: Set of filled slot IDs
            slot_idx: Current slot index
            all_slots: All slots in grid
            total_slots: Total slots count
        """
        if not self.task_id:
            logger.warning("Cannot save state: no task_id provided")
            return

        try:
            from ..state_manager import StateManager

            # Capture current state
            beam_search_state = StateManager.capture_beam_search_state(
                self, beam, filled_slots, slot_idx
            )

            # Create metadata
            metadata = {
                'min_score': self.min_score,
                'timeout': 300,  # Default timeout, will be overridden on resume
                'grid_size': [self.grid.size, self.grid.size],
                'total_slots': total_slots,
                'slots_filled': len(filled_slots),
                'iterations': self.iterations
            }

            # Save to disk
            state_manager = StateManager()
            file_path = state_manager.save_beam_search_state(
                task_id=self.task_id,
                beam_state=beam_search_state,
                metadata=metadata,
                compress=True
            )

            logger.info(f"Beam search state saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save beam search state: {e}", exc_info=True)

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
