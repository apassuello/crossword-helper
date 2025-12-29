"""
Diversity management for beam search.

This module implements strategies for maintaining diversity in the beam
to prevent beam collapse and avoid local optima.
"""

from typing import List, Tuple, Dict, Optional
from abc import ABC, abstractmethod
import logging

from ..state import BeamState

logger = logging.getLogger(__name__)


class DiversityStrategy(ABC):
    """Abstract base class for diversity management strategies."""

    @abstractmethod
    def diverse_beam_prune(
        self,
        expanded_beam: List[BeamState],
        slot: Dict,
        beam_width: int,
        num_groups: int = 4,
        diversity_lambda: float = 0.5
    ) -> List[BeamState]:
        """
        Select diverse states from expanded beam.

        Args:
            expanded_beam: All candidate states
            slot: Current slot being filled
            beam_width: Target beam size
            num_groups: Number of diversity groups
            diversity_lambda: Diversity weight

        Returns:
            Diverse subset of beam_width states
        """

    @abstractmethod
    def apply_diversity_bonus(self, beam: List[BeamState], diversity_bonus: float) -> List[BeamState]:
        """
        Apply bonus to states that differ from others in beam.

        Args:
            beam: Beam before scoring
            diversity_bonus: Diversity bonus multiplier

        Returns:
            Beam with updated scores (modified in-place)
        """


class DiversityManager(DiversityStrategy):
    """
    Diversity management for beam search.

    Implements Diverse Beam Search principles to prevent beam collapse
    and maintain exploration of different search paths.

    Reference: Vijayakumar et al. 2016 "Diverse Beam Search" (AAAI)
    """

    def __init__(self):
        """Initialize diversity manager."""

    def diverse_beam_prune(
        self,
        expanded_beam: List[BeamState],
        slot: Dict,
        beam_width: int,
        num_groups: int = 4,
        diversity_lambda: float = 0.5
    ) -> List[BeamState]:
        """
        Select diverse states from expanded beam using Diverse Beam Search principles.

        Instead of generating new states, this selects diverse states from
        an already-expanded beam to prevent collapse.

        Args:
            expanded_beam: All candidate states
            slot: Current slot being filled
            beam_width: Target beam size
            num_groups: Number of diversity groups
            diversity_lambda: Diversity weight

        Returns:
            Diverse subset of beam_width states
        """
        if len(expanded_beam) <= beam_width:
            return expanded_beam

        # Sort states by score first
        sorted_states = sorted(expanded_beam, key=lambda s: s.score, reverse=True)

        # Partition into diversity groups
        groups = []
        beams_per_group = max(1, beam_width // num_groups)

        for g in range(num_groups):
            group = []

            for state in sorted_states:
                if state in [s for grp in groups for s in grp]:
                    continue  # Already selected in previous group

                # Calculate diversity penalty against previous groups
                diversity_penalty = 0.0
                if groups:
                    for prev_group in groups:
                        for prev_state in prev_group:
                            # Measure state difference
                            diff = self.state_diversity_score(state, prev_state)
                            diversity_penalty += diff

                    # Normalize
                    num_prev_states = sum(len(g) for g in groups)
                    if num_prev_states > 0:
                        diversity_penalty /= num_prev_states

                # Augmented score
                augmented_score = state.score + diversity_lambda * diversity_penalty
                group.append((state, augmented_score))

            # Select top diverse candidates for this group
            group.sort(key=lambda x: -x[1])
            selected = [state for state, _ in group[:beams_per_group]]

            if selected:
                groups.append(selected)

        # Flatten groups
        result = []
        for group in groups:
            result.extend(group)

        # Debug output
        if len(result) > 0:
            logger.debug(f"  DEBUG DIVERSE PRUNE: Selected {len(result)} diverse states from {len(expanded_beam)} candidates")
            logger.debug(f"    Groups={num_groups}, Lambda={diversity_lambda}")

        return result[:beam_width]

    def state_diversity_score(self, state1: BeamState, state2: BeamState) -> float:
        """
        Calculate diversity score between two beam states.

        Measures how different two states are based on their word assignments.

        Args:
            state1: First state
            state2: Second state

        Returns:
            Diversity score (higher = more different)
        """
        # Count different word assignments
        all_slots = set(state1.slot_assignments.keys()) | set(state2.slot_assignments.keys())

        different_count = 0
        for slot_id in all_slots:
            word1 = state1.slot_assignments.get(slot_id, "")
            word2 = state2.slot_assignments.get(slot_id, "")
            if word1 != word2:
                different_count += 1

        # Normalize by total slots
        return different_count / max(1, len(all_slots))

    def diverse_beam_search(
        self,
        beam: List[BeamState],
        slot: Dict,
        candidates: List[Tuple[str, int]],
        beam_width: int,
        num_groups: int = 4,
        diversity_lambda: float = 0.5
    ) -> List[BeamState]:
        """
        Diverse Beam Search (Vijayakumar et al., 2016 AAAI).

        PHASE 4 - Critical Fix #1: Replace adaptive beam width with diversity mechanism.

        Research (Cohen et al. 2019 "Beam Search Curse"):
        - Adaptive narrowing (8->5->3->1) is NOT validated
        - Beam quality is "highly non-monotonic" - narrowing can worsen solutions
        - Instead, use constant width + diversity to prevent beam collapse

        Research (Vijayakumar et al. 2016 "Diverse Beam Search"):
        - 300% increase in distinct solutions
        - Better top-1 solutions through exploration/exploitation balance

        Args:
            beam: Current beam states
            slot: Slot being filled
            candidates: Word candidates with scores
            beam_width: Target beam width
            num_groups: Number of diversity groups (default 4)
            diversity_lambda: Diversity weight (0.5 = balanced)

        Returns:
            New diverse beam states (constant width)
        """
        if not beam or not candidates:
            return []

        groups = []
        beams_per_group = max(1, beam_width // num_groups)

        for g in range(num_groups):
            group_states = []

            for state in beam[:beams_per_group]:  # Take subset of beam for this group
                for word, score in candidates:
                    if word in state.used_words:
                        continue

                    # Calculate diversity penalty (Hamming distance to previous groups)
                    diversity_penalty = 0.0
                    if groups:
                        for prev_group in groups:
                            for prev_state in prev_group:
                                # Count differing letters at crossing positions
                                diff = self.hamming_distance_at_crossings(
                                    word, prev_state, slot
                                )
                                diversity_penalty += diff
                        # Normalize by number of previous states
                        num_prev_states = sum(len(g) for g in groups)
                        if num_prev_states > 0:
                            diversity_penalty /= num_prev_states

                    # Augmented score = quality + diversity bonus
                    augmented_score = score + diversity_lambda * diversity_penalty

                    # Create new state
                    new_state = state.clone()
                    new_state.grid.place_word(word, slot['row'], slot['col'], slot['direction'])
                    new_state.slots_filled += 1
                    new_state.score += augmented_score
                    new_state.used_words.add(word)
                    new_state.slot_assignments[(slot['row'], slot['col'], slot['direction'])] = word

                    group_states.append((new_state, augmented_score))

            # Select top candidates for this group
            group_states.sort(key=lambda x: -x[1])
            group = [state for state, _ in group_states[:beams_per_group]]

            if group:
                groups.append(group)

        # Flatten groups into single beam (maintain constant width)
        result = []
        for group in groups:
            result.extend(group)

        # DEBUG: Show diversity effect
        if result:
            logger.debug(f"  DEBUG DIVERSE BEAM: Generated {len(result)} diverse candidates from {num_groups} groups")
            logger.debug(f"    Diversity lambda={diversity_lambda} applied to prevent collapse")

        return result[:beam_width]  # Maintain constant beam width

    def hamming_distance_at_crossings(
        self, word: str, state: BeamState, slot: Dict
    ) -> int:
        """
        Count differing letters at intersection positions.

        Helper for Diverse Beam Search - measures diversity between
        word placement and existing state at crossing points.

        Args:
            word: Word to place
            state: Existing beam state
            slot: Slot where word would be placed

        Returns:
            Number of differing letters at crossings
        """
        diff_count = 0

        # Get all crossing slots for this slot
        for other_slot in state.grid.slots:
            if other_slot['direction'] != slot['direction']:
                # Check if they intersect
                intersection = self._get_slot_intersection(slot, other_slot)
                if intersection:
                    my_pos, their_pos = intersection

                    # Check if other slot is filled
                    other_id = (other_slot['row'], other_slot['col'], other_slot['direction'])
                    if other_id in state.slot_assignments:
                        other_word = state.slot_assignments[other_id]
                        # Count if letters differ
                        if my_pos < len(word) and their_pos < len(other_word):
                            if word[my_pos] != other_word[their_pos]:
                                diff_count += 1

        return diff_count

    def apply_diversity_bonus(
        self,
        beam: List[BeamState],
        diversity_bonus: float
    ) -> List[BeamState]:
        """
        Apply bonus to states that differ from others in beam.

        Diversity metric: Count of slots with different words
        Bonus formula: avg_difference x diversity_bonus

        Args:
            beam: Beam before scoring
            diversity_bonus: Diversity bonus multiplier

        Returns:
            Beam with updated scores (modified in-place)

        Complexity: O(beam_widthx x slots)

        Rationale: Encourages exploration of different search paths
        """
        if len(beam) <= 1:
            return beam

        for i, state_i in enumerate(beam):
            diversity_score = 0

            for j, state_j in enumerate(beam):
                if i == j:
                    continue

                # Count slots with different words
                diff_count = self.count_differences(state_i, state_j)
                diversity_score += diff_count

            # Average diversity across beam
            avg_diversity = diversity_score / (len(beam) - 1)

            # Apply bonus
            state_i.score += avg_diversity * diversity_bonus

        return beam

    def count_differences(
        self,
        state1: BeamState,
        state2: BeamState
    ) -> int:
        """
        Count number of slots with different words between two states.

        Args:
            state1: First state
            state2: Second state

        Returns:
            Number of differing slot assignments
        """
        diff_count = 0

        # Check all slots in state1
        for slot_id, word1 in state1.slot_assignments.items():
            word2 = state2.slot_assignments.get(slot_id)
            if word2 is None or word1 != word2:
                diff_count += 1

        # Check slots only in state2
        for slot_id in state2.slot_assignments:
            if slot_id not in state1.slot_assignments:
                diff_count += 1

        return diff_count

    def count_word_differences(self, state1: BeamState, state2: BeamState) -> int:
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

    def _get_slot_intersection(self, slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get intersection positions between two slots.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (slot1_position, slot2_position) if they intersect, None otherwise
        """
        if slot1['direction'] == slot2['direction']:
            return None  # Parallel slots don't intersect

        # Get cell coordinates for each slot
        cells1 = set()
        cells2 = set()

        if slot1['direction'] == 'across':
            for i in range(slot1['length']):
                cells1.add((slot1['row'], slot1['col'] + i, i))
        else:  # down
            for i in range(slot1['length']):
                cells1.add((slot1['row'] + i, slot1['col'], i))

        if slot2['direction'] == 'across':
            for i in range(slot2['length']):
                cells2.add((slot2['row'], slot2['col'] + i, i))
        else:  # down
            for i in range(slot2['length']):
                cells2.add((slot2['row'] + i, slot2['col'], i))

        # Find intersection
        for r1, c1, pos1 in cells1:
            for r2, c2, pos2 in cells2:
                if r1 == r2 and c1 == c2:
                    return (pos1, pos2)

        return None
