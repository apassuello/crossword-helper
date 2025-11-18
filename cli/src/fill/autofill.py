"""
CSP-based autofill engine for crossword grids.

Uses backtracking with heuristics:
- MCV (Most Constrained Variable): Fill hardest slots first
- LCV (Least Constraining Value): Choose words that preserve options
- Forward Checking: Eliminate impossible candidates early
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
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
        1. Fewest candidate words
        2. Most crossing slots already filled
        3. Longest length (for tie-breaking)

        Args:
            slots: List of slots

        Returns:
            Sorted list of slots
        """
        def constraint_key(slot):
            pattern = self.grid.get_pattern_for_slot(slot)

            # Count empty positions (wildcards)
            empty_count = pattern.count('?')

            # Count candidate words
            candidates = self.pattern_matcher.count_matches(pattern, self.min_score)

            # Prefer slots with more letters already filled (fewer wildcards)
            # and fewer candidate words
            # Negative length for tie-breaking (prefer longer words)
            return (candidates, empty_count, -slot['length'])

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

        Args:
            slot: Slot that was just filled

        Returns:
            True if placement is safe, False if creates dead end
        """
        # Get all slots
        all_slots = self.grid.get_empty_slots()

        # Find crossing slots
        crossing_slots = self._get_crossing_slots(slot, all_slots)

        # Check each crossing slot
        for crossing_slot in crossing_slots:
            pattern = self.grid.get_pattern_for_slot(crossing_slot)

            # Skip if fully filled
            if '?' not in pattern:
                continue

            # Check if any words match
            if not self.pattern_matcher.has_matches(pattern, self.min_score):
                # Dead end: no words fit crossing slot
                return False

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
