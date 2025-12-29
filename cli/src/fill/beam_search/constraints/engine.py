"""
Constraint propagation engine for beam search.

This module implements MAC (Maintaining Arc Consistency) and other constraint
propagation techniques to prune invalid word choices early in the search.
"""

from typing import Dict, List, Tuple, Optional, Set
from abc import ABC, abstractmethod
import logging

from ..state import BeamState
from ....core.grid import Grid

logger = logging.getLogger(__name__)


class ConstraintPropagationStrategy(ABC):
    """Abstract base class for constraint propagation strategies."""

    @abstractmethod
    def propagate(self, slot: Dict, word: str, state: BeamState) -> Tuple[bool, List, Set]:
        """
        Propagate constraints after placing a word.

        Returns:
            Tuple of (success, reductions, conflicts)
        """


class MACConstraintEngine(ConstraintPropagationStrategy):
    """
    Maintaining Arc Consistency (MAC) constraint propagation engine.

    Implements forward checking and arc consistency to detect conflicts
    early and prune invalid choices from domains.
    """

    def __init__(self, pattern_matcher):
        """
        Initialize MAC engine.

        Args:
            pattern_matcher: Pattern matching utility for finding valid words
        """
        self.pattern_matcher = pattern_matcher
        self.slot_cache = {}  # Cache for slot lookups

    def propagate(self, slot: Dict, word: str, state: BeamState) -> Tuple[bool, List, Set]:
        """
        Apply MAC propagation after placing a word.

        Reduces domains of crossing slots based on new constraint.
        Detects conflicts early to avoid wasted search.

        Args:
            slot: Slot where word was placed
            word: Word that was placed
            state: Current beam state with domains

        Returns:
            Tuple of:
            - success: True if consistent, False if conflict detected
            - reductions: List of domain reductions applied
            - conflicts: Set of conflicting slot IDs
        """
        reductions = []
        conflicts = set()
        (slot['row'], slot['col'], slot['direction'])

        # Get all crossing slots
        crossing_slots = self._get_crossing_slots(slot, state.grid)

        for crossing_slot in crossing_slots:
            crossing_id = (crossing_slot['row'], crossing_slot['col'], crossing_slot['direction'])

            # Skip if already filled
            if crossing_id in state.slot_assignments:
                continue

            # Get intersection position
            intersection = self._get_crossing_position(slot, crossing_slot)
            if not intersection:
                continue

            slot_pos, crossing_pos = intersection
            crossing_letter = word[slot_pos]

            # Reduce domain of crossing slot
            if crossing_id in state.domains:
                original_domain = state.domains[crossing_id]
                reduced_domain = [
                    w for w in original_domain
                    if len(w) > crossing_pos and w[crossing_pos] == crossing_letter
                ]

                # Track reduction
                if len(reduced_domain) < len(original_domain):
                    reductions.append((crossing_id, original_domain, reduced_domain))
                    state.domains[crossing_id] = reduced_domain

                # Detect conflict
                if len(reduced_domain) == 0:
                    conflicts.add(crossing_id)
                    return False, reductions, conflicts

        return True, reductions, conflicts

    def revise_domain(
        self,
        slot_id: Tuple,
        other_slot_id: Tuple,
        pos1: int,
        pos2: int,
        domains: Dict,
        grid: Grid
    ) -> Tuple[bool, Set[str]]:
        """
        Revise domain of slot1 based on constraint with slot2.

        Removes values from domain of slot1 that have no support in slot2.

        Args:
            slot_id: ID of slot to revise
            other_slot_id: ID of constraining slot
            pos1: Position in slot1 that intersects
            pos2: Position in slot2 that intersects
            domains: Current domains
            grid: Current grid state

        Returns:
            Tuple of (was_revised, removed_values)
        """
        if slot_id not in domains or other_slot_id not in domains:
            return False, set()

        slot_domain = domains[slot_id]
        other_domain = domains[other_slot_id]
        removed_values = set()

        # Check each value in slot's domain
        for word in slot_domain[:]:  # Copy to allow modification
            # Get letter at intersection position
            if pos1 >= len(word):
                continue

            letter_at_pos = word[pos1]

            # Check if any word in other domain supports this letter
            has_support = any(
                pos2 < len(other_word) and other_word[pos2] == letter_at_pos
                for other_word in other_domain
            )

            # Remove if no support
            if not has_support:
                slot_domain.remove(word)
                removed_values.add(word)

        return len(removed_values) > 0, removed_values

    def _get_crossing_slots(self, slot: Dict, grid: Grid) -> List[Dict]:
        """
        Get all slots that cross the given slot.

        Args:
            slot: Reference slot
            grid: Current grid

        Returns:
            List of crossing slots
        """
        crossing = []
        all_slots = grid.get_word_slots()

        for other_slot in all_slots:
            if self._slots_intersect(slot, other_slot):
                crossing.append(other_slot)

        return crossing

    def _get_crossing_position(self, slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get the positions where two slots intersect.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            Tuple of (pos_in_slot1, pos_in_slot2) or None if no intersection
        """
        # Slots must be perpendicular to intersect
        if slot1['direction'] == slot2['direction']:
            return None

        # Determine which is across and which is down
        if slot1['direction'] == 'across':
            across_slot = slot1
            down_slot = slot2
            across_is_first = True
        else:
            across_slot = slot2
            down_slot = slot1
            across_is_first = False

        # Calculate intersection point
        across_row = across_slot['row']
        across_col = across_slot['col']
        down_row = down_slot['row']
        down_col = down_slot['col']

        # Check if they intersect
        if down_col < across_col or down_col >= across_col + across_slot['length']:
            return None  # Down slot doesn't cross across slot horizontally

        if across_row < down_row or across_row >= down_row + down_slot['length']:
            return None  # Across slot doesn't cross down slot vertically

        # Calculate positions within each word
        across_pos = down_col - across_col
        down_pos = across_row - down_row

        if across_is_first:
            return (across_pos, down_pos)
        else:
            return (down_pos, across_pos)

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two slots intersect.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            True if slots intersect, False otherwise
        """
        # Quick rejection: same slot
        if (slot1['row'] == slot2['row'] and
            slot1['col'] == slot2['col'] and
            slot1['direction'] == slot2['direction']):
            return False

        # Quick rejection: parallel slots can't intersect
        if slot1['direction'] == slot2['direction']:
            return False

        # Get slot ranges
        if slot1['direction'] == 'across':
            across_slot = slot1
            down_slot = slot2
        else:
            across_slot = slot2
            down_slot = slot1

        # Check if ranges overlap
        across_row = across_slot['row']
        across_col_start = across_slot['col']
        across_col_end = across_col_start + across_slot['length'] - 1

        down_col = down_slot['col']
        down_row_start = down_slot['row']
        down_row_end = down_row_start + down_slot['length'] - 1

        # Check intersection
        return (down_row_start <= across_row <= down_row_end and
                across_col_start <= down_col <= across_col_end)

    def get_slot_by_id(self, slot_id: Tuple, slots: List[Dict]) -> Optional[Dict]:
        """
        Get slot dictionary by its ID.

        Args:
            slot_id: Tuple of (row, col, direction)
            slots: List of all slots

        Returns:
            Slot dictionary or None if not found
        """
        # Check cache first
        if slot_id in self.slot_cache:
            return self.slot_cache[slot_id]

        # Search for slot
        for slot in slots:
            if (slot['row'] == slot_id[0] and
                slot['col'] == slot_id[1] and
                slot['direction'] == slot_id[2]):
                self.slot_cache[slot_id] = slot
                return slot

        return None


class ArcConsistencyChecker:
    """
    Utility class for checking arc consistency in CSP.

    Implements AC-3 algorithm and related consistency checks.
    """

    def __init__(self, constraint_engine: MACConstraintEngine):
        """
        Initialize arc consistency checker.

        Args:
            constraint_engine: Constraint engine for domain revision
        """
        self.constraint_engine = constraint_engine

    def check_consistency(self, state: BeamState) -> bool:
        """
        Check if current state is arc consistent.

        Args:
            state: Current beam state

        Returns:
            True if consistent, False if conflict detected
        """
        # Check that no domain is empty
        for slot_id, domain in state.domains.items():
            if len(domain) == 0:
                return False

        return True

    def enforce_arc_consistency(self, state: BeamState, constraints: Dict) -> bool:
        """
        Run AC-3 algorithm to enforce arc consistency.

        Args:
            state: Current beam state
            constraints: Constraint graph

        Returns:
            True if consistent, False if domain wipeout
        """
        from collections import deque

        # Initialize queue with all arcs
        queue = deque()
        for slot_id, related in constraints.items():
            for other_id, pos1, pos2 in related:
                queue.append((slot_id, other_id, pos1, pos2))

        # Process queue
        while queue:
            slot_id, other_id, pos1, pos2 = queue.popleft()

            # Revise domain
            was_revised, removed = self.constraint_engine.revise_domain(
                slot_id, other_id, pos1, pos2,
                state.domains, state.grid
            )

            if was_revised:
                # Check for domain wipeout
                if slot_id in state.domains and len(state.domains[slot_id]) == 0:
                    return False

                # Add affected arcs to queue
                if slot_id in constraints:
                    for neighbor_id, my_pos, neighbor_pos in constraints[slot_id]:
                        if neighbor_id != other_id:
                            queue.append((neighbor_id, slot_id, neighbor_pos, my_pos))

        return True
