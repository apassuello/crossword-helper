"""
Value ordering strategies for beam search.

This module implements various strategies for ordering candidate words,
including LCV (Least Constraining Value) and quality-based ordering.
"""

from typing import List, Tuple, Dict, Optional
from abc import ABC, abstractmethod
import random
import logging

from ..state import BeamState
from ....core.grid import Grid

logger = logging.getLogger(__name__)


class ValueOrderingStrategy(ABC):
    """Abstract base class for value ordering strategies."""

    @abstractmethod
    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Order candidate values for a slot.

        Args:
            slot: Slot to fill
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Ordered list of (word, score) tuples
        """
        pass


class LCVValueOrdering(ValueOrderingStrategy):
    """
    Least Constraining Value (LCV) ordering strategy.

    Orders words by how many options they leave for crossing slots,
    preferring words that preserve the most flexibility.
    """

    def __init__(self, pattern_matcher, min_score_func):
        """
        Initialize LCV ordering.

        Args:
            pattern_matcher: Pattern matching utility
            min_score_func: Function to get min score for a given length
        """
        self.pattern_matcher = pattern_matcher
        self.get_min_score = min_score_func
        self.lcv_cache = {}  # Cache for LCV calculations

    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Order candidates by Least Constraining Value heuristic.

        For each candidate word:
        1. Temporarily place it
        2. Count remaining options for crossing slots
        3. Prefer words that leave more options

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Ordered list of candidates
        """
        if not candidates:
            return candidates

        # Get crossing slots for this slot
        crossing_slots = self._get_crossing_slots(slot, state.grid)
        if not crossing_slots:
            # No crossings - order by quality score only
            return sorted(candidates, key=lambda x: -x[1])

        lcv_scored = []
        for word, quality_score in candidates:
            # Skip already used words
            if word in state.used_words:
                continue

            # Calculate constraint impact
            total_remaining = 0
            for crossing in crossing_slots:
                # Skip already filled slots
                crossing_id = (crossing['row'], crossing['col'], crossing['direction'])
                if crossing_id in state.slot_assignments:
                    continue

                # Temporarily place word and get pattern
                state.grid.place_word(word, slot['row'], slot['col'], slot['direction'])
                pattern = state.grid.get_pattern_for_slot(crossing)
                state.grid.remove_word(slot['row'], slot['col'], slot['length'], slot['direction'])

                # Count how many words would be eliminated
                min_score = self.get_min_score(crossing['length'])
                crossing_candidates = self.pattern_matcher.find(pattern, min_score=min_score)

                # Filter out used words
                available = [w for w, s in crossing_candidates if w not in state.used_words]
                total_remaining += len(available)

            # Higher total_remaining = less constraining = better
            lcv_scored.append((word, quality_score, total_remaining))

        # Sort by LCV (most remaining options first), then by quality
        lcv_scored.sort(key=lambda x: (-x[2], -x[1]))

        return [(word, score) for word, score, _ in lcv_scored]

    def _get_crossing_slots(self, slot: Dict, grid: Grid) -> List[Dict]:
        """Get all slots that cross the given slot."""
        crossing = []
        all_slots = grid.get_word_slots()

        for other_slot in all_slots:
            if self._slots_intersect(slot, other_slot):
                crossing.append(other_slot)

        return crossing

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """Check if two slots intersect."""
        if slot1['direction'] == slot2['direction']:
            return False

        if slot1['direction'] == 'across':
            across_slot = slot1
            down_slot = slot2
        else:
            across_slot = slot2
            down_slot = slot1

        across_row = across_slot['row']
        across_col_start = across_slot['col']
        across_col_end = across_col_start + across_slot['length'] - 1

        down_col = down_slot['col']
        down_row_start = down_slot['row']
        down_row_end = down_row_start + down_slot['length'] - 1

        return (down_row_start <= across_row <= down_row_end and
                across_col_start <= down_col <= across_col_end)


class StratifiedValueOrdering(ValueOrderingStrategy):
    """
    Stratified shuffling strategy to prevent alphabetical bias.

    Groups candidates by quality tiers and shuffles within each tier
    to avoid beam collapse from alphabetical ordering.
    """

    def __init__(self, tier_size: int = 5):
        """
        Initialize stratified ordering.

        Args:
            tier_size: Number of candidates per quality tier
        """
        self.tier_size = tier_size

    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Apply stratified shuffling to candidates.

        Groups candidates into quality tiers and shuffles within each tier
        to prevent alphabetical bias while preserving quality ordering.

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Stratified and shuffled candidates
        """
        if len(candidates) <= self.tier_size:
            # Small list - just shuffle
            shuffled = candidates.copy()
            random.shuffle(shuffled)
            return shuffled

        # Sort by quality first
        sorted_candidates = sorted(candidates, key=lambda x: -x[1])

        # Group into tiers
        tiers = []
        for i in range(0, len(sorted_candidates), self.tier_size):
            tier = sorted_candidates[i:i + self.tier_size]
            random.shuffle(tier)  # Shuffle within tier
            tiers.append(tier)

        # Flatten tiers back to single list
        result = []
        for tier in tiers:
            result.extend(tier)

        return result


class CompositeValueOrdering(ValueOrderingStrategy):
    """
    Composite strategy that combines multiple ordering strategies.

    Allows chaining strategies like LCV followed by stratified shuffling.
    """

    def __init__(self, strategies: List[ValueOrderingStrategy]):
        """
        Initialize composite ordering.

        Args:
            strategies: List of strategies to apply in order
        """
        self.strategies = strategies

    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Apply multiple ordering strategies in sequence.

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Candidates ordered by all strategies
        """
        result = candidates
        for strategy in self.strategies:
            result = strategy.order_values(slot, result, state)
        return result


class QualityValueOrdering(ValueOrderingStrategy):
    """
    Simple quality-based ordering strategy.

    Orders candidates by their quality scores, with optional
    filtering of low-quality words.
    """

    def __init__(self, min_quality: int = 0):
        """
        Initialize quality ordering.

        Args:
            min_quality: Minimum quality threshold
        """
        self.min_quality = min_quality

    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Order candidates by quality score.

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Candidates ordered by quality (highest first)
        """
        # Filter by minimum quality
        filtered = [(w, s) for w, s in candidates if s >= self.min_quality]

        # Sort by quality score (descending)
        return sorted(filtered, key=lambda x: -x[1])


class ThresholdDiverseOrdering(ValueOrderingStrategy):
    """
    Threshold-based ordering with temperature for exploration.

    Phase 4.5: Research-validated approach from Stanford crossword paper.

    Algorithm:
    1. Set quality threshold (e.g., score >= 50)
    2. Filter candidates above threshold
    3. If too few, adaptively lower threshold
    4. Within threshold group, order by LCV (if available)
    5. Add temperature-based randomization for exploration
    6. Preserve top candidates for exploitation

    This balances exploration (trying diverse words) with exploitation
    (preferring high-quality words).

    Based on:
    - Stanford crossword research (temperature=0.9, p-sampling=0.9)
    - Diverse Beam Search paper (Vijayakumar et al. 2016)
    """

    def __init__(self, threshold: int = 50, temperature: float = 0.3):
        """
        Initialize threshold-diverse ordering.

        Args:
            threshold: Minimum quality score to consider (default 50)
            temperature: Randomization factor 0-1 (0=greedy, 1=fully random)
                        Default 0.3 provides gentle exploration
        """
        self.threshold = threshold
        self.temperature = temperature

    def order_values(self, slot: Dict, candidates: List[Tuple[str, int]], state: BeamState) -> List[Tuple[str, int]]:
        """
        Order candidates by threshold + diversity.

        Algorithm:
        1. Filter to candidates above threshold
        2. If too few, gradually lower threshold (adaptive)
        3. Sort by quality within threshold group
        4. Preserve top 20% for exploitation
        5. Shuffle remaining with temperature for exploration

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Ordered candidates balancing quality and diversity
        """
        if not candidates:
            return candidates

        # Adaptive threshold lowering when stuck
        current_threshold = self.threshold
        filtered = [(w, s) for w, s in candidates if s >= current_threshold]

        # Lower threshold if too few candidates (adaptive)
        while len(filtered) < 5 and current_threshold > 0:
            current_threshold -= 10
            filtered = [(w, s) for w, s in candidates if s >= current_threshold]

        if len(filtered) < 2:
            # Very few candidates, use all
            filtered = candidates

        # Sort by quality
        sorted_candidates = sorted(filtered, key=lambda x: -x[1])

        if self.temperature == 0:
            # Greedy: no randomization
            return sorted_candidates

        # Exploitation: Keep top 20% as-is (preserve best options)
        top_k = max(1, len(sorted_candidates) // 5)
        top_candidates = sorted_candidates[:top_k]
        rest_candidates = sorted_candidates[top_k:]

        # Exploration: Shuffle remaining with temperature
        if self.temperature >= 1.0:
            # Full randomization
            random.shuffle(rest_candidates)
        elif self.temperature > 0:
            # Weighted shuffle based on temperature
            # Higher temperature = more shuffling
            for i in range(len(rest_candidates)):
                if random.random() < self.temperature:
                    # Swap with random position
                    j = random.randint(i, len(rest_candidates) - 1)
                    rest_candidates[i], rest_candidates[j] = rest_candidates[j], rest_candidates[i]

        return top_candidates + rest_candidates