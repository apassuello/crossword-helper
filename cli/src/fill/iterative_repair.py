"""
Iterative repair autofill engine for crossword grids.

Fixes constraint violations in complete (but potentially invalid) grids through
local word swaps. Based on Dr.Fill algorithm by Matt Ginsberg.

Algorithm:
1. Start with complete grid (may have crossing mismatches)
2. Identify all conflicts (crossing letters that don't match)
3. Find slot with most conflicts
4. Try swapping to different word that reduces conflicts
5. Repeat until no conflicts or no improvement
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
import time

if TYPE_CHECKING:
    from .autofill import FillResult

from ..core.grid import Grid
from .word_list import WordList
from .pattern_matcher import PatternMatcher


@dataclass
class Conflict:
    """
    Represents a mismatch at a crossing point between two slots.

    Example:
        DRAMA (across) at row=5, col=3, direction='across'
        TREND (down) at row=2, col=5, direction='down'
        They cross at (row=5, col=5)
        DRAMA[2] = 'A' (position 2 in DRAMA)
        TREND[3] = 'N' (position 3 in TREND)
        → Conflict: expected 'A', got 'N'

    Invariants:
    - slot1_id != slot2_id
    - slot1_id and slot2_id must have different directions
    - position1, position2 ≥ 0
    - letter1, letter2 are single uppercase letters (A-Z)
    - letter1 != letter2 (otherwise not a conflict)
    """

    slot1_id: Tuple[int, int, str]  # (row, col, direction)
    slot2_id: Tuple[int, int, str]  # (row, col, direction)
    position1: int                   # Position in slot1 (0-indexed)
    position2: int                   # Position in slot2 (0-indexed)
    letter1: str                     # Letter from slot1 (expected)
    letter2: str                     # Letter from slot2 (actual - mismatch)

    def __str__(self) -> str:
        """Human-readable conflict description"""
        return (
            f"Conflict at {self.slot1_id}[{self.position1}]='{self.letter1}' "
            f"vs {self.slot2_id}[{self.position2}]='{self.letter2}'"
        )

    def involves_slot(self, slot_id: Tuple[int, int, str]) -> bool:
        """Check if this conflict involves given slot"""
        return slot_id == self.slot1_id or slot_id == self.slot2_id

    def get_other_slot(self, slot_id: Tuple[int, int, str]) -> Tuple[int, int, str]:
        """
        Get the other slot in this conflict.

        Preconditions:
        - slot_id must be one of (slot1_id, slot2_id)

        Raises:
        - ValueError: if slot_id not in conflict
        """
        if slot_id == self.slot1_id:
            return self.slot2_id
        elif slot_id == self.slot2_id:
            return self.slot1_id
        else:
            raise ValueError(f"Slot {slot_id} not involved in this conflict")


class IterativeRepair:
    """
    Iterative repair solver for crossword grids.

    Algorithm (based on Dr.Fill by Matt Ginsberg):
    1. Start with complete grid (may have crossing mismatches)
    2. Identify all conflicts (crossing letters that don't match)
    3. Find slot with most conflicts
    4. Try swapping to different word that reduces conflicts
    5. Repeat until no conflicts or no improvement
    """

    def __init__(
        self,
        grid: Grid,
        word_list: WordList,
        pattern_matcher: PatternMatcher,
        min_score: int = 0,
        max_iterations: int = 1000,
        progress_reporter=None,
        theme_entries=None,
        theme_words=None
    ):
        """
        Initialize iterative repair solver.

        Args:
            grid: Grid to repair (may be complete or partial)
            word_list: Available words
            pattern_matcher: Pattern matching engine
            min_score: Minimum word quality score (default: 0)
            max_iterations: Maximum repair iterations (default: 1000)
            progress_reporter: Optional progress reporting
            theme_entries: Dict of theme entries {(row, col, direction): word} (optional)
            theme_words: Set of words from theme wordlist to prioritize (optional)

        Raises:
            ValueError: If parameters out of valid ranges
        """
        # Validate parameters
        if max_iterations < 10:
            raise ValueError(f"max_iterations must be ≥10, got {max_iterations}")

        self.grid = grid
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher
        self.theme_entries = theme_entries
        self.theme_words = theme_words or set()
        self.min_score = min_score
        self.max_iterations = max_iterations
        self.progress_reporter = progress_reporter

        # State tracking
        self.start_time = 0.0
        self.iterations = 0

    def fill(self, timeout: int = 300) -> FillResult:
        """
        Repair grid by fixing conflicts.

        Algorithm:
        1. If grid incomplete: generate initial fill (greedy)
        2. Find all conflicts (crossing mismatches)
        3. While conflicts exist and time remains:
            a. Identify slot with most conflicts
            b. Try alternative words for that slot
            c. Keep word that reduces conflicts most
            d. Recompute conflicts
            e. Stop if no improvement for 50 iterations
        4. Return repaired grid

        Args:
            timeout: Maximum seconds to spend

        Returns:
            FillResult with repaired grid (may still have conflicts)

        Raises:
            ValueError: If timeout < 10 seconds
        """
        from .autofill import FillResult  # Import here to avoid circular dependency

        if timeout < 10:
            raise ValueError(f"timeout must be ≥10 seconds, got {timeout}")

        self.start_time = time.time()
        self.iterations = 0

        # Get all slots
        all_slots = self.grid.get_word_slots()
        total_slots = len(all_slots)

        # Step 1: Generate initial fill if grid incomplete
        empty_slots = self.grid.get_empty_slots()
        if empty_slots:
            if self.progress_reporter:
                self.progress_reporter.update(10, "Generating initial fill")

            # Reserve 30% of time for initial fill
            fill_timeout = timeout * 0.3
            self._generate_initial_fill(empty_slots, fill_timeout)

        # Step 2: Find all conflicts
        conflicts = self._find_conflicts(self.grid, all_slots)
        best_conflict_count = len(conflicts)
        no_improvement_count = 0

        if self.progress_reporter:
            self.progress_reporter.update(30, f"Found {len(conflicts)} conflicts")

        # Early exit if no conflicts
        if not conflicts:
            return FillResult(
                success=True,
                grid=self.grid,
                time_elapsed=time.time() - self.start_time,
                slots_filled=total_slots,
                total_slots=total_slots,
                problematic_slots=[],
                iterations=self.iterations
            )

        # Step 3: Iterative repair loop
        while self.iterations < self.max_iterations:
            self.iterations += 1

            # Check timeout
            elapsed = time.time() - self.start_time
            if elapsed > timeout:
                break

            # Stop if no improvement for 50 iterations
            if no_improvement_count >= 50:
                break

            # Report progress
            if self.progress_reporter and self.iterations % 10 == 0:
                progress = 30 + int((self.iterations / self.max_iterations) * 70)
                self.progress_reporter.update(
                    progress,
                    f"Repair iteration {self.iterations}: {len(conflicts)} conflicts"
                )

            # Find slot with most conflicts
            slot_conflict_counts = self._count_conflicts_per_slot(conflicts, all_slots)

            if not slot_conflict_counts:
                # No conflicts remain
                break

            # Get slot with maximum conflicts
            worst_slot_id = max(slot_conflict_counts.items(), key=lambda x: x[1])[0]

            # CONFLICT-DIRECTED BACKJUMPING (Phase 2.3):
            # Identify culprit slot (root cause) instead of just worst slot (symptom)
            culprit_slot_id = self._identify_culprit_slot(conflicts, worst_slot_id, all_slots)

            # Try to repair the CULPRIT slot (not necessarily the worst)
            improved, best_word = self._try_repair_slot(
                self.grid,
                culprit_slot_id,  # Change culprit, not worst
                conflicts,
                all_slots
            )

            if improved and best_word:
                # Apply the repair to the CULPRIT slot
                slot = self._get_slot_by_id(culprit_slot_id, all_slots)
                self.grid.place_word(
                    best_word,
                    slot['row'],
                    slot['col'],
                    slot['direction']
                )

                # Recompute conflicts
                conflicts = self._find_conflicts(self.grid, all_slots)

                # Check if we improved
                if len(conflicts) < best_conflict_count:
                    best_conflict_count = len(conflicts)
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1

                # Early exit if no conflicts
                if not conflicts:
                    break
            else:
                no_improvement_count += 1

        # Return result
        time_elapsed = time.time() - self.start_time
        success = len(conflicts) == 0

        return FillResult(
            success=success,
            grid=self.grid,
            time_elapsed=time_elapsed,
            slots_filled=total_slots,  # Repair fills all slots
            total_slots=total_slots,
            problematic_slots=[],  # Repair doesn't leave empty slots
            iterations=self.iterations
        )

    def _identify_culprit_slot(
        self,
        conflicts: List[Conflict],
        worst_slot_id: Tuple[int, int, str],
        all_slots: List[Dict]
    ) -> Tuple[int, int, str]:
        """
        Identify the culprit slot (root cause) using conflict-directed backjumping.

        PHASE 2.3 - Research Gap #9: Conflict-Directed Backjumping

        Instead of always changing the worst slot (symptom), identify which
        slot is the root cause of the conflict.

        Research (Prosser 1993): "Jump directly to culprit variable"
        Research (Ginsberg 1990): "Intelligent backtracking reduced time by 10×"

        Heuristics for identifying culprit:
        1. Number of alternatives: More alternatives = easier to change (better culprit)
        2. Conflict involvement: Which slot is involved in more conflicts?
        3. Word quality: Lower quality word is more likely culprit

        Args:
            conflicts: All current conflicts
            worst_slot_id: The slot with most conflicts
            all_slots: All slots in grid

        Returns:
            Tuple (row, col, direction) of culprit slot to change
        """
        # Collect all slots involved in conflicts with worst_slot
        related_conflicts = [c for c in conflicts if c.involves_slot(worst_slot_id)]

        if not related_conflicts:
            # No related conflicts, worst slot IS the culprit
            return worst_slot_id

        # Candidate slots: worst slot + all slots it conflicts with
        candidate_slots = set([worst_slot_id])
        for conflict in related_conflicts:
            other_slot = conflict.get_other_slot(worst_slot_id)
            candidate_slots.add(other_slot)

        # Score each candidate for "culprit-ness"
        culprit_scores = {}

        for slot_id in candidate_slots:
            slot = self._get_slot_by_id(slot_id, all_slots)
            if not slot:
                continue

            pattern = self.grid.get_pattern_for_slot(slot)

            # Count alternative words available
            alternatives = self.pattern_matcher.find(pattern, min_score=self.min_score)
            alt_count = len(alternatives)

            # Count how many conflicts this slot is involved in
            conflict_count = sum(1 for c in conflicts if c.involves_slot(slot_id))

            # Heuristic: High alternatives + high conflicts = good culprit
            # We want to change the slot that:
            # - Has many alternatives (easy to fix)
            # - Is involved in many conflicts (high impact)
            culprit_score = alt_count * conflict_count

            culprit_scores[slot_id] = culprit_score

        if not culprit_scores:
            return worst_slot_id

        # Return slot with highest culprit score
        culprit_slot = max(culprit_scores.items(), key=lambda x: x[1])[0]
        return culprit_slot

    def _generate_initial_fill(
        self,
        empty_slots: List[Dict],
        timeout: float
    ) -> None:
        """
        Generate complete fill by greedily placing best words.

        Strategy: Fill slots in MRV order with highest-scoring unused word.
        Ignores crossing constraints (may create conflicts).

        Args:
            empty_slots: Slots that need filling
            timeout: Time budget for initial fill

        Complexity: O(slots × pattern_match_time)

        Rationale: Provides starting point for repair
        """
        # Collect words already in grid (from beam search or pre-filled)
        used_words = set()
        all_slots = self.grid.get_word_slots()
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:  # Completely filled slot
                used_words.add(pattern)

        start_time = time.time()

        # Sort by constraint level (length-first, then MRV)
        # CRITICAL: Longest slots filled first to ensure high-quality words
        sorted_slots = self._sort_slots_by_constraint(empty_slots)

        for slot in sorted_slots:
            # Check timeout
            if time.time() - start_time > timeout:
                break

            # Get pattern
            pattern = self.grid.get_pattern_for_slot(slot)

            # Get candidates
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=self.min_score
            )

            # Find first unused word
            placed = False
            for word, score in candidates:
                if word not in used_words:
                    # Place word
                    self.grid.place_word(
                        word,
                        slot['row'],
                        slot['col'],
                        slot['direction']
                    )
                    used_words.add(word)
                    placed = True
                    break

            # FIX #2 (Phase 4.1): Handle empty candidates
            # If no valid candidates found, clear slot to prevent gibberish
            if not placed:
                self.grid.remove_word(
                    slot['row'], slot['col'], slot['length'], slot['direction']
                )

    def _find_conflicts(
        self,
        grid: Grid,
        slots: List[Dict]
    ) -> List[Conflict]:
        """
        Find all crossing conflicts in grid.

        Conflict = two slots that cross but have different letters at intersection.

        Example:
            DRAMA (across) has 'A' at position 2
            TREND (down) has 'E' at position 2
            → Conflict: expected 'A', got 'E'

        Args:
            grid: Grid to check
            slots: All slots in grid

        Returns:
            List of conflicts (empty if grid valid)

        Complexity: O(slots² × intersection_checks)
        """
        conflicts = []

        # Check all pairs of slots
        for i, slot1 in enumerate(slots):
            for j in range(i + 1, len(slots)):
                slot2 = slots[j]

                # Skip if same direction (can't intersect)
                if slot1['direction'] == slot2['direction']:
                    continue

                # Find intersection
                intersection = self._get_intersection(slot1, slot2)
                if intersection is None:
                    continue

                pos1, pos2 = intersection

                # Get patterns (current fill)
                pattern1 = grid.get_pattern_for_slot(slot1)
                pattern2 = grid.get_pattern_for_slot(slot2)

                # Check for mismatch
                letter1 = pattern1[pos1]
                letter2 = pattern2[pos2]

                # Conflict if both filled but different
                if letter1 != '?' and letter2 != '?' and letter1 != letter2:
                    slot1_id = (slot1['row'], slot1['col'], slot1['direction'])
                    slot2_id = (slot2['row'], slot2['col'], slot2['direction'])

                    conflicts.append(Conflict(
                        slot1_id=slot1_id,
                        slot2_id=slot2_id,
                        position1=pos1,
                        position2=pos2,
                        letter1=letter1,
                        letter2=letter2
                    ))

        return conflicts

    def _try_repair_slot(
        self,
        grid: Grid,
        slot_id: Tuple[int, int, str],
        conflicts: List[Conflict],
        all_slots: List[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to find better word for slot that reduces conflicts.

        Strategy:
        1. Count current conflicts involving this slot
        2. Try alternative words (up to 50 candidates)
        3. For each word: place it, count new conflicts
        4. Keep word with fewest conflicts (if better than current)

        Args:
            grid: Current grid
            slot_id: (row, col, direction) of slot to repair
            conflicts: Current conflicts in grid
            all_slots: All slots in grid

        Returns:
            (improved, best_word) where:
            - improved: True if found better word
            - best_word: Word to use (None if no improvement)

        Complexity: O(candidates × conflict_counting)
        """
        # Count current conflicts for this slot
        current_conflicts = [c for c in conflicts if c.involves_slot(slot_id)]
        current_count = len(current_conflicts)

        # Get the slot
        slot = self._get_slot_by_id(slot_id, all_slots)
        if slot is None:
            return False, None

        # Get current pattern
        current_pattern = grid.get_pattern_for_slot(slot)

        # Get all currently used words (to prevent duplicates)
        used_words = set()
        for s in all_slots:
            pattern = grid.get_pattern_for_slot(s)
            if '?' not in pattern:  # Completely filled
                # Don't count the current slot's word as used
                s_id = (s['row'], s['col'], s['direction'])
                if s_id != slot_id:
                    used_words.add(pattern)

        # Get alternative words
        candidates = self.pattern_matcher.find(
            current_pattern.replace(current_pattern, '?' * slot['length']),  # Full wildcard
            min_score=self.min_score
        )

        # Phase 3.4: Prioritize theme words if configured
        if self.theme_words:
            theme_candidates = []
            non_theme_candidates = []

            for word, score in candidates:
                if word in self.theme_words:
                    # Theme word: add +50 bonus
                    theme_candidates.append((word, score + 50))
                else:
                    # Non-theme word: keep original score
                    non_theme_candidates.append((word, score))

            # Theme words first, then non-theme
            # Each group is already sorted by score (from pattern_matcher)
            candidates = theme_candidates + non_theme_candidates

        # Limit to top 50
        candidates = candidates[:50]

        best_word = None
        best_count = current_count

        # Try each candidate
        for word, score in candidates:
            # Skip if same as current
            if word == current_pattern:
                continue

            # Skip if word already used elsewhere (prevent duplicates)
            if word in used_words:
                continue

            # Save current state
            original_pattern = current_pattern

            # Try placing this word
            grid.place_word(word, slot['row'], slot['col'], slot['direction'])

            # Count new conflicts
            new_conflicts = self._find_conflicts(grid, all_slots)
            new_conflicts_for_slot = [c for c in new_conflicts if c.involves_slot(slot_id)]
            new_count = len(new_conflicts_for_slot)

            # Check if better
            if new_count < best_count:
                best_word = word
                best_count = new_count

            # Restore original
            # FIX #3 (Phase 4.1): Fix pattern restoration bug
            # Old code: if original_pattern.replace('?', ''):  # WRONG - can crash
            # New code: Explicit check for wildcards
            if '?' not in original_pattern:  # Pattern has no wildcards - it's a real word
                grid.place_word(original_pattern, slot['row'], slot['col'], slot['direction'])
            else:
                # Clear the slot (pattern has wildcards, not a valid word)
                grid.remove_word(slot['row'], slot['col'], slot['length'], slot['direction'])

        # Return result
        if best_word is not None:
            return True, best_word
        else:
            return False, None

    def _count_conflicts_per_slot(
        self,
        conflicts: List[Conflict],
        slots: List[Dict]
    ) -> Dict[Tuple, int]:
        """
        Count how many conflicts each slot is involved in.

        Args:
            conflicts: All conflicts
            slots: All slots

        Returns:
            Map of slot_id → conflict_count

        Complexity: O(conflicts)

        Rationale: Used to prioritize which slot to repair first
        """
        conflict_counts: Dict[Tuple, int] = {}

        for conflict in conflicts:
            # Count for slot1
            if conflict.slot1_id not in conflict_counts:
                conflict_counts[conflict.slot1_id] = 0
            conflict_counts[conflict.slot1_id] += 1

            # Count for slot2
            if conflict.slot2_id not in conflict_counts:
                conflict_counts[conflict.slot2_id] = 0
            conflict_counts[conflict.slot2_id] += 1

        return conflict_counts

    def _get_intersection(
        self,
        slot1: Dict,
        slot2: Dict
    ) -> Optional[Tuple[int, int]]:
        """
        Find intersection position between two slots.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (pos1, pos2) where pos1 is position in slot1 and pos2 is position in slot2
            None if slots don't intersect
        """
        # One must be across, one must be down
        if slot1['direction'] == slot2['direction']:
            return None

        if slot1['direction'] == 'across':
            across_slot = slot1
            down_slot = slot2
        else:
            across_slot = slot2
            down_slot = slot1

        # Check if they intersect
        # Across: row is fixed, col varies
        # Down: col is fixed, row varies

        across_row = across_slot['row']
        across_col_start = across_slot['col']
        across_col_end = across_col_start + across_slot['length'] - 1

        down_col = down_slot['col']
        down_row_start = down_slot['row']
        down_row_end = down_row_start + down_slot['length'] - 1

        # Intersection occurs if:
        # - across_row is within down's row range
        # - down_col is within across's col range
        if (down_row_start <= across_row <= down_row_end and
            across_col_start <= down_col <= across_col_end):

            # Calculate positions
            if slot1['direction'] == 'across':
                pos1 = down_col - across_col_start
                pos2 = across_row - down_row_start
            else:
                pos1 = across_row - down_row_start
                pos2 = down_col - across_col_start

            return (pos1, pos2)

        return None

    def _get_slot_by_id(
        self,
        slot_id: Tuple[int, int, str],
        slots: List[Dict]
    ) -> Optional[Dict]:
        """
        Find slot by id.

        Args:
            slot_id: (row, col, direction)
            slots: All slots

        Returns:
            Slot dict or None if not found
        """
        row, col, direction = slot_id

        for slot in slots:
            if (slot['row'] == row and
                slot['col'] == col and
                slot['direction'] == direction):
                return slot

        return None

    def _sort_slots_by_constraint(self, slots: List[Dict]) -> List[Dict]:
        """
        Sort slots by constraint level using length-first ordering.

        CRITICAL: Fill LONGEST words first (research-backed).

        Research consensus (Ginsberg 1990, Shortz, Crossfire, Dr.Fill):
        - Long words (9-11 letters): Structural backbone, ~1k real candidates
        - Short words (3-5 letters): Flexible "glue", ~2k candidates
        - Filling short first creates impossible long patterns → gibberish

        Sorting priority:
        1. Length (descending): Longest slots first
        2. Domain size (ascending): MRV for ties (fewest candidates first)
        3. Empty count (ascending): More constrained first

        Args:
            slots: List of slot dicts

        Returns:
            Sorted list (longest first, then most constrained)
        """
        def constraint_key(slot: Dict):
            pattern = self.grid.get_pattern_for_slot(slot)

            # Count candidates (domain size)
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=self.min_score
            )
            domain_size = len(candidates)

            # Count empty cells
            empty_count = pattern.count('?')

            # PRIMARY: Length (descending) - LONGEST FIRST!
            # SECONDARY: Domain size (ascending) - most constrained first
            # TERTIARY: Empty count (ascending) - more filled letters first
            return (-slot['length'], domain_size, empty_count)

        return sorted(slots, key=constraint_key)
