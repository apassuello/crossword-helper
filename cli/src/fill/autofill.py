"""
CSP-based autofill engine for crossword grids.

Uses backtracking with heuristics:
- MCV (Most Constrained Variable): Fill hardest slots first
- LCV (Least Constraining Value): Choose words that preserve options
- AC-3 (Arc Consistency): Maintain domain consistency efficiently
- Forward Checking: Eliminate impossible candidates early
"""

from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
from collections import deque
import time
from ..core.grid import Grid
from .word_list import WordList
from .pattern_matcher import PatternMatcher


@dataclass
class FillResult:
    """Result of autofill attempt."""
    success: bool
    grid: Grid
    time_elapsed: float
    slots_filled: int
    total_slots: int
    problematic_slots: List[Dict]
    iterations: int


class Autofill:
    """
    Constraint satisfaction solver for crossword grids.

    Uses backtracking with intelligent heuristics to fill crossword grids
    efficiently while maintaining crossword quality.
    """

    def __init__(self,
                 grid: Grid,
                 word_list: WordList,
                 pattern_matcher: PatternMatcher = None,
                 timeout: int = 300,
                 min_score: int = 30):
        """
        Initialize autofill solver.

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine (created if not provided)
            timeout: Maximum seconds to spend filling
            min_score: Minimum word score to consider
        """
        self.grid = grid
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher or PatternMatcher(word_list)
        self.timeout = timeout
        self.min_score = min_score

        self.start_time = 0.0
        self.iterations = 0
        self.used_words = set()

        # Domain tracking and constraint graph (initialized on fill())
        self.domains: Dict[int, Set[str]] = {}  # slot_id -> set of valid words
        self.constraints: Dict[int, List[Tuple[int, int, int]]] = {}  # slot_id -> [(other_slot, my_pos, other_pos)]
        self.slot_list: List[Dict] = []  # All slots
        self.slot_id_map: Dict[Tuple, int] = {}  # (row, col, direction) -> slot_id

    def fill(self, interactive: bool = False) -> FillResult:
        """
        Fill grid using backtracking CSP.

        Args:
            interactive: If True, prompt user before each placement (not implemented)

        Returns:
            FillResult with success status and filled grid
        """
        self.start_time = time.time()
        self.iterations = 0
        self.used_words = set()

        # Get unfilled slots
        slots = self.grid.get_empty_slots()
        total_slots = len(slots)

        if total_slots == 0:
            # Grid already filled
            return FillResult(
                success=True,
                grid=self.grid,
                time_elapsed=0.0,
                slots_filled=0,
                total_slots=0,
                problematic_slots=[],
                iterations=0
            )

        # Initialize constraint graph and domains
        self._initialize_csp(slots)

        # Apply initial arc consistency
        if not self._ac3():
            # Grid is unsolvable
            return FillResult(
                success=False,
                grid=self.grid,
                time_elapsed=time.time() - self.start_time,
                slots_filled=0,
                total_slots=total_slots,
                problematic_slots=slots,
                iterations=0
            )

        # Sort slots by constraint (MCV heuristic)
        slots = self._sort_slots_by_constraint(slots)

        # Try to fill using backtracking
        try:
            success = self._backtrack(slots, 0)
        except TimeoutError:
            success = False

        time_elapsed = time.time() - self.start_time

        # Calculate results
        remaining_slots = self.grid.get_empty_slots()
        slots_filled = total_slots - len(remaining_slots)

        return FillResult(
            success=success,
            grid=self.grid,
            time_elapsed=time_elapsed,
            slots_filled=slots_filled,
            total_slots=total_slots,
            problematic_slots=remaining_slots if not success else [],
            iterations=self.iterations
        )

    def _initialize_csp(self, slots: List[Dict]) -> None:
        """
        Initialize constraint graph and domains for CSP.

        Builds:
        - Constraint graph mapping slots to their intersecting slots
        - Initial domains (valid words) for each slot

        Args:
            slots: All slots to fill
        """
        self.slot_list = slots
        self.slot_id_map = {}
        self.constraints = {}
        self.domains = {}

        # Create slot ID mapping
        for idx, slot in enumerate(slots):
            key = (slot['row'], slot['col'], slot['direction'])
            self.slot_id_map[key] = idx

        # Build constraint graph
        for i, slot1 in enumerate(slots):
            self.constraints[i] = []

            for j, slot2 in enumerate(slots):
                if i == j:
                    continue

                # Check intersection
                intersection = self._get_intersection(slot1, slot2)
                if intersection:
                    pos1, pos2 = intersection
                    self.constraints[i].append((j, pos1, pos2))

        # Initialize domains
        for idx, slot in enumerate(slots):
            pattern = self.grid.get_pattern_for_slot(slot)
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=self.min_score,
                max_results=1000  # Larger domain initially
            )
            self.domains[idx] = {word for word, score in candidates}

    def _get_intersection(self, slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get intersection position between two slots.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (pos1, pos2) if they intersect, where pos1 is position in slot1
            and pos2 is position in slot2. None if no intersection.
        """
        # Must be different directions
        if slot1['direction'] == slot2['direction']:
            return None

        # Determine across and down
        if slot1['direction'] == 'across':
            across, down = slot1, slot2
        else:
            across, down = slot2, slot1

        # Check intersection
        across_row = across['row']
        across_col_start = across['col']
        across_col_end = across_col_start + across['length']

        down_row_start = down['row']
        down_row_end = down_row_start + down['length']
        down_col = down['col']

        # Does down column intersect across range?
        if across_col_start <= down_col < across_col_end:
            # Does across row intersect down range?
            if down_row_start <= across_row < down_row_end:
                # They intersect!
                if slot1['direction'] == 'across':
                    pos1 = down_col - across_col_start
                    pos2 = across_row - down_row_start
                else:
                    pos1 = across_row - down_row_start
                    pos2 = down_col - across_col_start
                return (pos1, pos2)

        return None

    def _ac3(self) -> bool:
        """
        AC-3 arc consistency algorithm.

        Maintains arc consistency by eliminating values from domains
        that cannot satisfy constraints.

        Returns:
            True if consistent, False if any domain becomes empty
        """
        # Initialize queue with all arcs
        queue = deque()
        for slot_id in self.constraints:
            for other_id, pos1, pos2 in self.constraints[slot_id]:
                queue.append((slot_id, other_id, pos1, pos2))

        # Process arcs
        while queue:
            slot_id, other_id, pos1, pos2 = queue.popleft()

            if self._revise(slot_id, other_id, pos1, pos2):
                # Domain was reduced
                if len(self.domains[slot_id]) == 0:
                    return False  # Unsolvable

                # Add arcs from neighbors to queue
                for neighbor_id, my_pos, neighbor_pos in self.constraints[slot_id]:
                    if neighbor_id != other_id:
                        queue.append((neighbor_id, slot_id, neighbor_pos, my_pos))

        return True

    def _revise(self, slot_id: int, other_id: int, pos1: int, pos2: int) -> bool:
        """
        Revise domain of slot_id based on constraint with other_id.

        Args:
            slot_id: Slot to revise
            other_id: Constraining slot
            pos1: Position in slot_id that must match
            pos2: Position in other_id that must match

        Returns:
            True if domain was revised (values removed)
        """
        revised = False
        words_to_remove = []

        for word in self.domains[slot_id]:
            # Check if this word is compatible with any word in other domain
            has_compatible = False

            for other_word in self.domains[other_id]:
                # Check if letters match at intersection
                if word[pos1] == other_word[pos2]:
                    has_compatible = True
                    break

            if not has_compatible:
                words_to_remove.append(word)
                revised = True

        # Remove incompatible words
        for word in words_to_remove:
            self.domains[slot_id].discard(word)

        return revised

    def _backtrack(self, slots: List[Dict], current_index: int) -> bool:
        """
        Recursive backtracking algorithm.

        Args:
            slots: List of slots to fill (sorted by constraint)
            current_index: Current position in slots list

        Returns:
            True if successfully filled, False if no solution
        """
        self.iterations += 1

        # Check timeout
        if time.time() - self.start_time > self.timeout:
            raise TimeoutError("Autofill timeout")

        # Check every 1000 iterations for timeout
        if self.iterations % 1000 == 0:
            if time.time() - self.start_time > self.timeout:
                raise TimeoutError("Autofill timeout")

        # Base case: all slots filled
        if current_index >= len(slots):
            return True

        # Get current slot
        slot = slots[current_index]

        # Skip if already filled
        pattern = self.grid.get_pattern_for_slot(slot)
        if '?' not in pattern:
            # Slot already filled, move to next
            return self._backtrack(slots, current_index + 1)

        # Get candidate words (LCV heuristic)
        candidates = self._get_candidates(slot)

        if not candidates:
            # No valid words for this slot
            return False

        # Try each candidate
        for word, score in candidates:
            # Skip if word already used
            if word in self.used_words:
                continue

            # Place word
            self.grid.place_word(
                word,
                slot['row'],
                slot['col'],
                slot['direction']
            )
            self.used_words.add(word)

            # Forward check
            if self._forward_check(slot):
                # Recurse
                if self._backtrack(slots, current_index + 1):
                    return True  # Success!

            # Backtrack
            self.grid.remove_word(
                slot['row'],
                slot['col'],
                slot['length'],
                slot['direction']
            )
            self.used_words.remove(word)

        # No candidate worked
        return False

    def _sort_slots_by_constraint(self, slots: List[Dict]) -> List[Dict]:
        """
        Sort slots by constraint level (MCV heuristic).

        Most constrained slots first:
        1. Fewest candidate words (from domain)
        2. Most crossing slots already filled
        3. Longest length (for tie-breaking)

        Args:
            slots: List of slots

        Returns:
            Sorted list of slots
        """
        def constraint_key(slot):
            # Get domain size
            key = (slot['row'], slot['col'], slot['direction'])
            slot_id = self.slot_id_map.get(key)

            if slot_id is not None and slot_id in self.domains:
                # Use pre-computed domain size
                domain_size = len(self.domains[slot_id])
            else:
                # Fallback to pattern matching
                pattern = self.grid.get_pattern_for_slot(slot)
                domain_size = self.pattern_matcher.count_matches(pattern, self.min_score)

            # Count empty positions (wildcards)
            pattern = self.grid.get_pattern_for_slot(slot)
            empty_count = pattern.count('?')

            # Prefer slots with fewer candidate words and more letters filled
            # Negative length for tie-breaking (prefer longer words)
            return (domain_size, empty_count, -slot['length'])

        return sorted(slots, key=constraint_key)

    def _get_candidates(self, slot: Dict) -> List[Tuple[str, int]]:
        """
        Get candidate words for slot.

        Args:
            slot: Slot to fill

        Returns:
            List of (word, score) tuples, sorted by score descending
        """
        pattern = self.grid.get_pattern_for_slot(slot)

        # Get matching words
        candidates = self.pattern_matcher.find(
            pattern,
            min_score=self.min_score,
            max_results=100
        )

        return candidates

    def _forward_check(self, slot: Dict) -> bool:
        """
        Check if placing word eliminates all options for any crossing slot.

        Uses domain-based checking for efficiency - only validates against
        pre-computed constraint graph instead of checking all slots.

        Args:
            slot: Slot that was just filled

        Returns:
            True if placement is safe, False if creates dead end
        """
        # Get slot ID
        key = (slot['row'], slot['col'], slot['direction'])
        slot_id = self.slot_id_map.get(key)

        if slot_id is None:
            # Slot not in our tracking, fall back to basic check
            return True

        # Check each constrained slot
        for other_id, pos1, pos2 in self.constraints[slot_id]:
            # Check if any word in the domain is still valid
            pattern = self.grid.get_pattern_for_slot(self.slot_list[other_id])

            # Skip if fully filled
            if '?' not in pattern:
                continue

            # Check if domain has compatible words
            has_valid = False
            for word in self.domains[other_id]:
                if word in self.used_words:
                    continue
                # Quick pattern match
                matches = all(
                    pattern[i] == '?' or pattern[i] == word[i]
                    for i in range(len(pattern))
                )
                if matches:
                    has_valid = True
                    break

            if not has_valid:
                return False  # Dead end

        return True

    def _get_crossing_slots(self, slot: Dict, all_slots: List[Dict]) -> List[Dict]:
        """
        Find slots that cross the given slot.

        Args:
            slot: Slot to check
            all_slots: All slots in grid

        Returns:
            List of slots that intersect with given slot
        """
        crossing = []

        row, col = slot['row'], slot['col']
        length = slot['length']
        direction = slot['direction']

        for other_slot in all_slots:
            # Skip same slot
            if (other_slot['row'] == row and
                other_slot['col'] == col and
                other_slot['direction'] == direction):
                continue

            # Check if they intersect
            if self._slots_intersect(slot, other_slot):
                crossing.append(other_slot)

        return crossing

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two slots intersect.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            True if slots cross each other
        """
        # Slots must be in different directions to intersect
        if slot1['direction'] == slot2['direction']:
            return False

        # Determine which is across and which is down
        if slot1['direction'] == 'across':
            across, down = slot1, slot2
        else:
            across, down = slot2, slot1

        # Check if they intersect
        # Across slot spans columns [across_col, across_col + across_len)
        # Down slot spans rows [down_row, down_row + down_len)
        # They intersect if down column is in across range AND across row is in down range

        across_row = across['row']
        across_col_start = across['col']
        across_col_end = across_col_start + across['length']

        down_row_start = down['row']
        down_row_end = down_row_start + down['length']
        down_col = down['col']

        # Check intersection
        if (across_col_start <= down_col < across_col_end and
            down_row_start <= across_row < down_row_end):
            return True

        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"Autofill(grid={self.grid.size}x{self.grid.size}, words={len(self.word_list)})"
