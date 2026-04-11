"""
Slot selection strategies for beam search.

This module implements various strategies for selecting and ordering slots
during the crossword filling process, including MRV (Minimum Remaining Values)
and other heuristics.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple

from ....core.grid import Grid
from ..state import BeamState

logger = logging.getLogger(__name__)


class SlotSelectionStrategy(ABC):
    """Abstract base class for slot selection strategies."""

    @abstractmethod
    def select_next_slot(self, unfilled_slots: List[Dict], state: BeamState) -> Optional[Dict]:
        """Select the next slot to fill."""

    @abstractmethod
    def order_slots(self, slots: List[Dict], grid: Grid) -> List[Dict]:
        """Order slots by filling difficulty."""


class MRVSlotSelector(SlotSelectionStrategy):
    """
    Minimum Remaining Values (MRV) slot selection strategy.

    Selects slots with the fewest valid candidates first, as these are
    the most constrained and likely to fail if delayed.
    """

    def __init__(self, pattern_matcher, word_list, theme_entries: Optional[Dict] = None):
        """
        Initialize MRV selector.

        Args:
            pattern_matcher: Pattern matching utility
            word_list: Available word list
            theme_entries: Optional theme entries to prioritize
        """
        self.pattern_matcher = pattern_matcher
        self.word_list = word_list
        self.theme_entries = theme_entries or {}

    def select_next_slot(
        self,
        unfilled_slots: List[Dict],
        state: BeamState,
        recently_failed: Optional[List[Tuple]] = None,
    ) -> Optional[Dict]:
        """
        Select next slot using Dynamic MRV with intelligent tie-breaking.

        Strategy:
        1. Calculate domain size for each slot
        2. Prefer slots with smallest domain (MRV)
        3. Heavily penalize recently failed slots to prevent thrashing
        4. Tie-break by degree (number of unfilled crossings)
        5. Further tie-break by alternating direction

        Args:
            unfilled_slots: List of slots not yet filled
            state: Current beam state for domain evaluation
            recently_failed: Optional list of recently failed slot_ids (for deprioritization)

        Returns:
            Selected slot or None if no slots available
        """
        recently_failed = recently_failed or []
        if not unfilled_slots:
            return None

        candidates = []
        for slot in unfilled_slots:
            # Get current pattern for this slot
            pattern = state.grid.get_pattern_for_slot(slot)

            # Count valid candidates (domain size)
            min_score = self._get_min_score_for_length(slot["length"])
            valid_words = self.pattern_matcher.find(pattern, min_score=min_score)
            domain_size = len(valid_words)

            # Degree: Count unfilled crossing slots
            degree = 0
            all_slots = state.grid.get_word_slots()
            for other_slot in all_slots:
                if self._slots_intersect(slot, other_slot):
                    other_pattern = state.grid.get_pattern_for_slot(other_slot)
                    if "?" in other_pattern:  # Still has empty cells
                        degree += 1

            # Track candidate with metrics
            candidates.append(
                {
                    "slot": slot,
                    "domain_size": domain_size,
                    "degree": degree,
                    "direction": slot["direction"],
                    "length": slot["length"],
                }
            )

        # Sort by MRV heuristic with tie-breaking
        # Primary: domain size (ascending - smallest first)
        # Secondary: degree (descending - most constrained first)
        # Tertiary: prefer longer slots

        # Determine last filled direction for tie-breaking
        last_direction = None
        if state.slot_assignments:
            # Get the most recently filled slot's direction
            last_slot_key = list(state.slot_assignments.keys())[-1]
            last_direction = last_slot_key[2]

        def mrv_key(candidate):
            domain = candidate["domain_size"]
            degree = candidate["degree"]
            length = candidate["length"]
            direction = candidate["direction"]
            slot_id = (
                candidate["slot"]["row"],
                candidate["slot"]["col"],
                candidate["slot"]["direction"],
            )

            # Calculate failure penalty to prevent thrashing
            failure_penalty = 0

            # Heavy penalty for recently failed slots (prevents infinite retry loops)
            if slot_id in recently_failed:
                # Penalty based on how recently it failed (0-4 index)
                recency_index = recently_failed.index(slot_id)
                # Most recent failure gets highest penalty
                failure_penalty = 1000 * (len(recently_failed) - recency_index)
                logger.debug(f"    Slot {slot_id} has recent failure (recency={recency_index}), penalty={failure_penalty}")

            # Extremely high penalty for impossible slots (domain_size=0)
            # These should almost never be selected as they will always fail
            if domain == 0:
                failure_penalty += 10000
                logger.debug(f"    Slot {slot_id} has zero domain, adding 10000 penalty")

            # Prefer alternating directions for natural fill
            direction_bonus = 0
            if last_direction:
                if direction != last_direction:
                    direction_bonus = -0.1  # Small bonus for alternating

            # Primary key is domain + failure penalty (prevents selecting impossible/failed slots)
            return (
                domain + failure_penalty,  # Primary: domain + penalties
                -degree,  # Secondary: highest degree first
                -length,  # Tertiary: longest slots first
                direction_bonus,
            )  # Quaternary: alternate directions

        candidates.sort(key=mrv_key)

        selected = candidates[0]

        # Debug: Verify direction interleaving
        # Always show MRV selection for first 10 slots to verify interleaving
        if len(state.slot_assignments) <= 10:
            directions = [c["direction"] for c in candidates[:5]]
            domain_sizes = [c["domain_size"] for c in candidates[:5]]
            logger.debug(f"  MRV top 5: {list(zip(directions, domain_sizes))}")
            logger.debug(f"  → Selected: {selected['direction'].upper()} (domain={selected['domain_size']})")

        return selected["slot"]

    def order_slots(self, slots: List[Dict], grid: Grid) -> List[Dict]:
        """
        Sort slots by static constraint degree for initial ordering.

        Uses multiple heuristics:
        1. Domain size (ascending): Fewer candidates = more constrained
        2. Empty count (ascending): More letters filled = more constrained

        Args:
            slots: List of slots to order
            grid: Current grid state

        Returns:
            Ordered list of slots (most constrained first)
        """

        def constraint_key(slot: Dict):
            pattern = grid.get_pattern_for_slot(slot)

            # Get minimum score for this slot length
            min_score = self._get_min_score_for_length(slot["length"])

            # Count candidates (domain size)
            candidates = self.pattern_matcher.find(pattern, min_score=min_score, max_results=1000)  # Limit for performance
            domain_size = len(candidates)

            # Count empty cells
            empty_count = pattern.count("?")

            # Primary: domain size (fewer candidates = more constrained)
            # Secondary: empty count (more filled = more constrained)
            return (domain_size, empty_count)

        # Sort by constraint (most constrained first)
        sorted_slots = sorted(slots, key=constraint_key)
        return sorted_slots

    def order_by_secondary_constraint(self, slots: List[Dict], grid: Grid) -> List[Dict]:
        """
        Secondary ordering by crossing constraints.

        Prioritizes slots that cross with many other unfilled slots,
        as filling these provides more constraint propagation.

        Args:
            slots: List of slots to order
            grid: Current grid state

        Returns:
            Ordered list of slots
        """

        def crossing_key(slot: Dict):
            # Count number of crossing slots that are still unfilled
            crossing_count = 0
            for other_slot in slots:
                if slot != other_slot and self._slots_intersect(slot, other_slot):
                    other_pattern = grid.get_pattern_for_slot(other_slot)
                    if "?" in other_pattern:
                        crossing_count += 1

            # Higher crossing count = fill first (more constraint propagation)
            return -crossing_count

        return sorted(slots, key=crossing_key)

    def prioritize_theme_entries(self, slots: List[Dict]) -> Tuple[List[Dict], Set[str]]:
        """
        Separate and prioritize theme entry slots.

        Theme entries are typically:
        - The longest slots in the grid
        - Central to the puzzle's theme
        - Must be placed first to ensure quality

        Args:
            slots: All available slots

        Returns:
            Tuple of (prioritized_slots, theme_words)
        """
        if not self.theme_entries:
            return slots, set()

        theme_slots = []
        regular_slots = []
        theme_words = set()

        for slot in slots:
            slot_key = (slot["row"], slot["col"], slot["direction"])
            if slot_key in self.theme_entries:
                theme_slots.append(slot)
                theme_words.add(self.theme_entries[slot_key])
            else:
                regular_slots.append(slot)

        # Sort theme slots by length (longest first)
        theme_slots.sort(key=lambda s: -s["length"])

        # Return theme slots first, then regular slots
        return theme_slots + regular_slots, theme_words

    def _get_min_score_for_length(self, length: int) -> int:
        """
        Get minimum quality score threshold based on word length.

        Longer words should have higher quality standards.

        Args:
            length: Word length

        Returns:
            Minimum score threshold
        """
        if length <= 3:
            return 0  # Allow all 3-letter words (need flexibility)
        elif length <= 5:
            return 10  # Slightly filter 4-5 letter words
        elif length <= 7:
            return 20  # Moderate filter for medium words
        elif length <= 9:
            return 30  # Higher standards for longer words
        else:
            return 40  # Highest standards for 10+ letters

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two slots intersect.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            True if slots intersect, False otherwise
        """
        # Quick rejection: parallel slots can't intersect
        if slot1["direction"] == slot2["direction"]:
            return False

        # Get slot ranges
        if slot1["direction"] == "across":
            across_slot = slot1
            down_slot = slot2
        else:
            across_slot = slot2
            down_slot = slot1

        # Check if ranges overlap
        across_row = across_slot["row"]
        across_col_start = across_slot["col"]
        across_col_end = across_col_start + across_slot["length"] - 1

        down_col = down_slot["col"]
        down_row_start = down_slot["row"]
        down_row_end = down_row_start + down_slot["length"] - 1

        # Check intersection
        return down_row_start <= across_row <= down_row_end and across_col_start <= down_col <= across_col_end
