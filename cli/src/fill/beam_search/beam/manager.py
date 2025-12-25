"""
Beam management for beam search.

This module implements strategies for beam expansion, pruning,
and adaptive width adjustment.
"""

from typing import List, Tuple, Dict, Optional
from abc import ABC, abstractmethod
import logging

from ..state import BeamState
from ....core.grid import Grid

logger = logging.getLogger(__name__)


class BeamManagementStrategy(ABC):
    """Abstract base class for beam management strategies."""

    @abstractmethod
    def expand_beam(
        self,
        beam: List[BeamState],
        slot: Dict,
        candidates_per_slot: int
    ) -> List[BeamState]:
        """
        Expand beam by trying top-K candidates in each state.

        Returns:
            Expanded beam
        """
        pass

    @abstractmethod
    def prune_beam(
        self,
        beam: List[BeamState],
        beam_width: int
    ) -> List[BeamState]:
        """
        Prune beam to keep only top-K diverse states.

        Returns:
            Pruned beam
        """
        pass

    @abstractmethod
    def get_adaptive_beam_width(
        self,
        beam_states: List[BeamState],
        unfilled_slots: List[Dict],
        total_slots: int,
        slot: Dict
    ) -> int:
        """
        Calculate adaptive beam width based on search state.

        Returns:
            Adaptive beam width
        """
        pass


class BeamManager(BeamManagementStrategy):
    """
    Beam management for beam search.

    Implements beam expansion, pruning, and adaptive width strategies
    to control the search process.
    """

    def __init__(
        self,
        pattern_matcher,
        get_min_score_func,
        evaluate_viability_func,
        compute_score_func,
        is_quality_word_func,
        base_beam_width: int,
        value_ordering=None  # Phase 4.5: Added value ordering
    ):
        """
        Initialize beam manager.

        Args:
            pattern_matcher: Pattern matching utility
            get_min_score_func: Function to get minimum score for a given length
            evaluate_viability_func: Function to evaluate state viability
            compute_score_func: Function to compute state score
            is_quality_word_func: Function to check word quality
            base_beam_width: Base beam width
            value_ordering: Value ordering strategy (Phase 4.5)
        """
        self.pattern_matcher = pattern_matcher
        self.get_min_score = get_min_score_func
        self.evaluate_viability = evaluate_viability_func
        self.compute_score = compute_score_func
        self.is_quality_word = is_quality_word_func
        self.value_ordering = value_ordering  # Phase 4.5
        self.base_beam_width = base_beam_width
        self.debug_lcv = False
        self.debug_mac = False

    def expand_beam(
        self,
        beam: List[BeamState],
        slot: Dict,
        candidates_per_slot: int
    ) -> List[BeamState]:
        """
        Expand beam by trying top-K candidates in each state.

        Args:
            beam: Current beam (list of states)
            slot: Slot to fill next
            candidates_per_slot: How many words to try per state

        Returns:
            Expanded beam (potentially beam_width * candidates_per_slot states)

        Complexity: O(beam_width * candidates_per_slot * pattern_match_time)
        """
        from ...crosswordese import filter_crosswordese

        expanded = []

        # DEBUG: Track why expansion might fail
        total_skipped_duplicate = 0
        total_skipped_viability = 0
        total_added = 0

        # DIVERSITY STRATEGY: Stratified candidate selection with overlapping slices
        # Prevents beam collapse by ensuring each beam explores different combinations
        # while maintaining access to high-quality candidates
        #
        # Example with offset=2, candidates_per_slot=10:
        #   Beam 0: candidates[0:10]   = ALASKARANGE, ALMOSTTHERE, ALMOSTNEVER, ...
        #   Beam 1: candidates[2:12]   = ALMOSTNEVER, ALLTOGETHER, APPLICATION, ...
        #   Beam 2: candidates[4:14]   = APPLICATION, APPROPRIATE, ALTERNATIVES, ...
        #   x Overlapping ensures quality, offset ensures diversity
        offset_per_beam = 2  # Tunable: increase for more diversity, decrease for more quality overlap

        for beam_idx, state in enumerate(beam):
            # Get pattern for this slot in current state
            pattern = state.grid.get_pattern_for_slot(slot)

            # Skip if already filled
            if '?' not in pattern:
                expanded.append(state)
                continue

            # Use length-dependent quality threshold
            min_score = self.get_min_score(slot['length'])

            # Get ALL candidate words
            all_candidates = self.pattern_matcher.find(
                pattern,
                min_score=min_score
            )

            if len(all_candidates) == 0:
                # No candidates: this beam state is dead
                continue

            # CROSSWORDESE FILTER (Phase 2.1 - Research Gap #8):
            # Filter out unacceptable crosswordese based on slot length
            # - 3-4 letters: Crosswordese OK (glue words)
            # - 5-6 letters: Crosswordese penalized (score reduced 50%)
            # - 7+ letters: Crosswordese completely filtered (unacceptable)
            all_candidates = filter_crosswordese(all_candidates, slot['length'])

            if len(all_candidates) == 0:
                # No candidates after crosswordese filter: dead end
                continue

            # QUALITY FILTER: For long slots, reject likely gibberish
            if slot['length'] >= 7:
                quality_candidates = [
                    (word, score) for word, score in all_candidates
                    if self.is_quality_word(word)
                ]

                # Safety valve: only use quality filter if enough candidates remain
                if len(quality_candidates) >= 5:
                    all_candidates = quality_candidates

            # PHASE 4.5 FIX: Apply value ordering (was planned but never wired up!)
            if self.value_ordering:
                all_candidates = self.value_ordering.order_values(slot, all_candidates, state)
            # If no value ordering, use candidates as-is

            # STRATIFIED SAMPLING: Each beam gets overlapping slice from shuffled candidates
            # With 48k+ shuffled candidates, overlapping slices give diversity + coherence
            offset = beam_idx * offset_per_beam
            start_idx = offset
            end_idx = offset + candidates_per_slot
            candidates = all_candidates[start_idx:end_idx]

            # Fallback: If offset exceeds available candidates, wrap around
            if len(candidates) < candidates_per_slot and len(all_candidates) >= candidates_per_slot:
                candidates = all_candidates[:candidates_per_slot]

            # Try each candidate
            for word, word_score in candidates:
                # Skip if word already used
                if word in state.used_words:
                    total_skipped_duplicate += 1
                    continue

                # FIX #5 (Phase 4.3): CRITICAL - Validate word length matches slot length
                # This should never fail if pattern matching is correct, but add defensive check
                # to prevent partial placements that leave dots in grid
                if len(word) != slot['length']:
                    continue

                # Create new state
                new_state = state.clone()

                # Place word
                new_state.grid.place_word(
                    word,
                    slot['row'],
                    slot['col'],
                    slot['direction']
                )

                # Update metadata
                new_state.used_words.add(word)
                slot_id = (slot['row'], slot['col'], slot['direction'])
                new_state.slot_assignments[slot_id] = word

                # FIX #1 (Phase 4.2): Only increment slots_filled if slot is COMPLETELY filled
                # Previous bug: Counted every word placement, even if slot still had '?' wildcards
                # Correct: Only count when pattern has no '?' remaining
                # Note: No need to check for dots - get_pattern_for_slot() converts dots to '?'
                pattern = new_state.grid.get_pattern_for_slot(slot)
                if '?' not in pattern:
                    new_state.slots_filled += 1

                # Compute score
                new_state.score = self.compute_score(new_state, word_score)

                # Check viability with PREDICTIVE RISK ASSESSMENT
                is_viable, risk_penalty = self.evaluate_viability(new_state, slot)

                if is_viable:
                    # Apply risk penalty to score (discourages risky paths)
                    new_state.score *= risk_penalty
                    expanded.append(new_state)
                    total_added += 1
                else:
                    total_skipped_viability += 1

        # DEBUG: Show why expansion might have failed
        if not expanded:
            logger.debug(f"\nDEBUG: Expansion failed!")
            logger.debug(f"  Skipped (duplicate): {total_skipped_duplicate}")
            logger.debug(f"  Skipped (viability): {total_skipped_viability}")
            logger.debug(f"  Added: {total_added}")

        return expanded

    def prune_beam(
        self,
        beam: List[BeamState],
        beam_width: int
    ) -> List[BeamState]:
        """
        Prune beam to keep only top-K DIVERSE states.

        CRITICAL FIX: Explicitly remove duplicate states to prevent beam collapse.
        Two states are "duplicate" if they have same words in same slots.

        Process:
        1. Remove exact duplicates (same slot assignments)
        2. Sort by score (descending)
        3. Greedily select: pick best, then pick next that differs by e1 word
        4. Fill remaining slots with best available

        Args:
            beam: Expanded beam (many states)
            beam_width: Target size

        Returns:
            Pruned beam (diverse states, up to beam_width)

        Complexity: O(n log n) for sorting + O(nx) for diversity check
        """
        if len(beam) <= beam_width:
            return beam

        # Step 1: Remove exact duplicates (only if states have words placed)
        # For states with no words placed, skip deduplication (let score differentiate)
        has_words_placed = any(len(state.slot_assignments) > 0 for state in beam)

        if has_words_placed:
            unique_beam = []
            seen_signatures = set()

            for state in beam:
                # Create signature: frozenset of (slot_id, word) pairs
                signature = frozenset(state.slot_assignments.items())

                if signature not in seen_signatures:
                    unique_beam.append(state)
                    seen_signatures.add(signature)
        else:
            # All states are empty, keep all (differentiated by score)
            unique_beam = beam

        if len(unique_beam) <= beam_width:
            return unique_beam

        # Step 2: Sort by score (descending)
        unique_beam.sort(key=lambda s: s.score, reverse=True)

        # Step 3: Greedy diversity selection (only if states have words)
        if has_words_placed:
            selected = [unique_beam[0]]  # Always keep best

            for candidate in unique_beam[1:]:
                if len(selected) >= beam_width:
                    break

                # Check diversity: how many words differ from already selected?
                min_difference = min(
                    self._count_word_differences(candidate, s) for s in selected
                )

                # Only add if sufficiently different (at least 1 word different)
                if min_difference > 0:
                    selected.append(candidate)
        else:
            # No words placed yet, just take top-K by score
            selected = unique_beam[:beam_width]
            return selected

        # Step 4: If we didn't get enough diverse candidates, fill with best remaining
        # (Better to have some duplicates than incomplete beam)
        while len(selected) < beam_width and len(unique_beam) > len(selected):
            for state in unique_beam:
                if state not in selected:
                    selected.append(state)
                    if len(selected) >= beam_width:
                        break

        return selected

    def get_adaptive_beam_width(
        self,
        beam_states: List[BeamState],
        unfilled_slots: List[Dict],
        total_slots: int,
        slot: Dict
    ) -> int:
        """
        Smart adaptive beam width based on search state, not just depth.

        Key insights from research:
        - WIDEN when diversity is low (prevent collapse)
        - NARROW when few viable candidates exist (efficiency)
        - WIDEN in middle depths (fight convergence)

        Args:
            beam_states: Current beam of states
            unfilled_slots: Remaining unfilled slots
            total_slots: Total number of slots in grid
            slot: Current slot being filled

        Returns:
            Adaptive beam width (3-20)
        """
        # Calculate depth
        depth = 1.0 - (len(unfilled_slots) / total_slots)

        # Factor 1: Calculate diversity (variance in scores)
        if len(beam_states) > 1:
            scores = [s.score for s in beam_states]
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            # Normalize variance
            normalized_variance = variance / (mean_score ** 2 + 0.001)
        else:
            normalized_variance = 1.0

        # Low variance = risk of collapse, need MORE width
        if normalized_variance < 0.05:
            diversity_factor = 1.5  # INCREASE width to maintain diversity
        elif normalized_variance < 0.1:
            diversity_factor = 1.2
        else:
            diversity_factor = 1.0

        # Factor 2: Count viable candidates for current slot
        pattern = beam_states[0].grid.get_pattern_for_slot(slot) if beam_states else "?" * slot['length']
        min_score = self.get_min_score(slot['length'])
        candidates = self.pattern_matcher.find(pattern, min_score=min_score)
        viable_count = len(candidates)

        # Few candidates = can use narrower beam
        candidate_factor = min(1.0, viable_count / (self.base_beam_width * 2))
        if candidate_factor < 0.3:
            candidate_factor = 0.3  # Don't narrow too much

        # Factor 3: Smart depth adjustment (not simple narrowing!)
        if depth < 0.3:
            depth_factor = 1.0  # Full width early for exploration
        elif depth < 0.7:
            depth_factor = 1.2  # WIDER in middle (fight convergence!)
        else:
            depth_factor = 0.8  # Only mild narrowing near end

        # Calculate final width
        adaptive_width = int(self.base_beam_width * diversity_factor * candidate_factor * depth_factor)

        # Clamp between reasonable bounds
        adaptive_width = max(3, min(20, adaptive_width))

        return adaptive_width

    def _count_word_differences(self, state1: BeamState, state2: BeamState) -> int:
        """
        Count how many words differ between two states.

        Args:
            state1: First state
            state2: Second state

        Returns:
            Number of differing words (symmetric difference)
        """
        words1 = set(state1.used_words)
        words2 = set(state2.used_words)
        # Symmetric difference: words in one but not both
        return len(words1 ^ words2)
