"""
Diversity management for beam search.

This module implements strategies for maintaining diversity in the beam
to prevent beam collapse and avoid local optima.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List

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
        diversity_lambda: float = 0.5,
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
        diversity_lambda: float = 0.5,
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

    def count_differences(self, state1: BeamState, state2: BeamState) -> int:
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
