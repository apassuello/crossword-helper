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

            # CRITICAL: Skip theme-locked slots (can't be changed)
            culprit_slot = self._get_slot_by_id(culprit_slot_id, all_slots)
            if culprit_slot:
                # Check if slot has any locked cells (theme words)
                row, col, direction = culprit_slot_id
                has_locked_cells = False
                for i in range(culprit_slot['length']):
                    check_row = row + (i if direction == 'down' else 0)
                    check_col = col + (i if direction == 'across' else 0)
                    if (check_row, check_col) in self.grid.locked_cells:
                        has_locked_cells = True
                        break

                if has_locked_cells:
                    # Can't repair this slot - it's theme-locked
                    # Remove it from conflicts and try next iteration
                    no_improvement_count += 1
                    continue

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

        # CRITICAL FIX: Remove all invalid words before returning
        # This ensures we NEVER return gibberish to the user
        # Loop until no invalid words remain (clearing creates new invalid patterns)
        removed_count = 0
        max_cleanup_iterations = 10  # Prevent infinite loops

        for cleanup_iter in range(max_cleanup_iterations):
            # Find all invalid slots in current grid state
            slots_to_clear = []
            for slot in all_slots:
                pattern = self.grid.get_pattern_for_slot(slot)

                # Skip empty slots
                if '?' in pattern:
                    continue

                # Check if ALL cells in this slot are locked (can't modify anything)
                all_locked = True
                has_non_locked = False
                if slot['direction'] == 'across':
                    for i in range(slot['length']):
                        if (slot['row'], slot['col'] + i) not in self.grid.locked_cells:
                            all_locked = False
                            has_non_locked = True
                            break
                else:  # down
                    for i in range(slot['length']):
                        if (slot['row'] + i, slot['col']) not in self.grid.locked_cells:
                            all_locked = False
                            has_non_locked = True
                            break

                # Skip fully-locked words (nothing we can modify)
                if all_locked:
                    continue

                # Validate word exists in wordlist
                candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                word_exists = any(word == pattern for word, score in candidates)

                if not word_exists and has_non_locked:
                    # Invalid word with modifiable cells - mark for removal
                    slots_to_clear.append(slot)

            # If no invalid words found, we're done
            if not slots_to_clear:
                break

            # Clear invalid slots (but preserve locked cells)
            cells_cleared_this_iteration = 0
            for slot in slots_to_clear:
                # Clear only non-locked cells in the slot
                if slot['direction'] == 'across':
                    for i in range(slot['length']):
                        pos = (slot['row'], slot['col'] + i)
                        if pos not in self.grid.locked_cells:
                            self.grid.cells[pos[0], pos[1]] = 0  # Set to empty
                            cells_cleared_this_iteration += 1
                else:  # down
                    for i in range(slot['length']):
                        pos = (slot['row'] + i, slot['col'])
                        if pos not in self.grid.locked_cells:
                            self.grid.cells[pos[0], pos[1]] = 0  # Set to empty
                            cells_cleared_this_iteration += 1
                removed_count += 1

            # If no cells were actually cleared (all were locked), stop
            # This prevents infinite loops when invalid words are entirely locked
            if cells_cleared_this_iteration == 0:
                # Report that we found invalid words but couldn't remove them
                if self.progress_reporter and slots_to_clear:
                    self.progress_reporter.update(
                        90,
                        f"Cleanup: {len(slots_to_clear)} invalid words have all cells locked (theme intersections)"
                    )
                break

        # NOW count actually filled slots (after cleanup)
        filled_slots = sum(
            1 for slot in all_slots
            if '?' not in self.grid.get_pattern_for_slot(slot)
        )

        # Find problematic slots (empty or conflicting)
        problematic_slots = []
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' in pattern:
                # Slot not fully filled
                problematic_slots.append({
                    'slot': (slot['row'], slot['col'], slot['direction']),
                    'pattern': pattern,
                    'reason': 'unfilled'
                })

        # Success = no conflicts AND all slots filled with valid words
        # After cleanup, conflicts should be 0 if we removed all invalid words
        success = filled_slots == total_slots

        if self.progress_reporter:
            if success:
                self.progress_reporter.update(100, f"Complete! {filled_slots}/{total_slots} slots filled")
            else:
                cleanup_msg = f" (removed {removed_count} invalid)" if removed_count > 0 else ""
                self.progress_reporter.update(
                    90,
                    f"Partial fill: {filled_slots}/{total_slots} slots{cleanup_msg}, {len(problematic_slots)} unfilled"
                )

        return FillResult(
            success=success,
            grid=self.grid,
            time_elapsed=time_elapsed,
            slots_filled=filled_slots,
            total_slots=total_slots,
            problematic_slots=problematic_slots,
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
        Generate fill using multiple passes with increasing flexibility.

        Strategy:
        - Pass 1: Fill with gibberish check (strict — only place words that
          don't create invalid perpendicular patterns)
        - Pass 2+: Re-sort remaining empty slots (patterns changed from
          neighbors) and retry without gibberish check (the repair loop
          will fix crossing conflicts later)
        - Each pass re-reads patterns so it benefits from letters placed
          by previous passes.

        Args:
            empty_slots: Slots that need filling
            timeout: Time budget for initial fill
        """
        used_words = set()
        all_slots = self.grid.get_word_slots()
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:
                used_words.add(pattern)

        start_time = time.time()
        filled_count = 0
        max_passes = 5

        for pass_num in range(max_passes):
            if time.time() - start_time > timeout:
                break

            # Re-check which slots are still empty (patterns change between passes)
            remaining = [s for s in all_slots
                         if '?' in self.grid.get_pattern_for_slot(s)]
            if not remaining:
                break

            # Re-sort by constraint level (MRV — fewest candidates first)
            remaining = self._sort_slots_by_constraint(remaining)

            # First pass: strict (check gibberish). Later passes: relaxed.
            strict = (pass_num == 0)
            placed_this_pass = 0

            for slot in remaining:
                if time.time() - start_time > timeout:
                    break

                pattern = self.grid.get_pattern_for_slot(slot)
                if '?' not in pattern:
                    continue  # Already filled by a neighbor placement

                candidates = self.pattern_matcher.find(
                    pattern, min_score=self.min_score
                )

                placed = False
                for word, score in candidates:
                    if word in used_words:
                        continue

                    if strict and self._would_create_gibberish(word, slot, all_slots):
                        continue

                    try:
                        self.grid.place_word(
                            word, slot['row'], slot['col'], slot['direction']
                        )
                    except ValueError:
                        continue  # Conflicts with locked cell

                    used_words.add(word)
                    placed = True
                    filled_count += 1
                    placed_this_pass += 1
                    break

            if self.progress_reporter:
                total_remaining = sum(
                    1 for s in all_slots
                    if '?' in self.grid.get_pattern_for_slot(s)
                )
                self.progress_reporter.update(
                    15 + pass_num * 3,
                    f"Initial fill pass {pass_num+1}: {filled_count} filled, "
                    f"{total_remaining} remaining"
                )

            # If nothing was placed this pass, further passes won't help
            if placed_this_pass == 0:
                break

    def _find_conflicts(
        self,
        grid: Grid,
        slots: List[Dict]
    ) -> List[Conflict]:
        """
        Find all crossing conflicts AND invalid words in grid.

        CRITICAL FIX: Now validates BOTH:
        1. Crossing conflicts (letters mismatch at intersections)
        2. Word validity (word must exist in wordlist)

        A grid is ONLY valid if ALL words are in the wordlist AND
        all intersections match.

        Example:
            DRAMA (across) has 'A' at position 2
            TREND (down) has 'E' at position 2
            → Conflict: expected 'A', got 'E'

        Args:
            grid: Grid to check
            slots: All slots in grid

        Returns:
            List of conflicts (empty if grid valid)

        Complexity: O(slots² × intersection_checks + slots × word_validation)
        """
        conflicts = []

        # STEP 1: Check crossing mismatches (original logic)
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

        # STEP 2: NEW - Validate each filled word exists in wordlist
        # This prevents gibberish words like "TRICOTSME" that happen to
        # have matching crossings
        for slot in slots:
            pattern = grid.get_pattern_for_slot(slot)

            # Skip if slot has wildcards (not fully filled)
            if '?' in pattern:
                continue

            # Check if this word exists in our wordlist
            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
            word_exists = any(word == pattern for word, score in candidates)

            if not word_exists:
                # Word doesn't exist in wordlist - treat as a conflict
                # Create a pseudo-conflict to flag this slot for repair
                slot_id = (slot['row'], slot['col'], slot['direction'])
                conflicts.append(Conflict(
                    slot1_id=slot_id,
                    slot2_id=slot_id,  # Self-conflict
                    position1=0,
                    position2=0,
                    letter1=pattern[0] if pattern else '?',
                    letter2='?',  # Invalid word marker
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

        # Get alternative words that respect locked letters
        # Build a pattern with locked cells preserved as fixed letters
        repair_pattern = list('?' * slot['length'])
        for i in range(slot['length']):
            if slot['direction'] == 'across':
                pos = (slot['row'], slot['col'] + i)
            else:
                pos = (slot['row'] + i, slot['col'])
            if pos in self.grid.locked_cells:
                # Locked cell: must keep this letter
                cell_val = self.grid.cells[pos]
                if cell_val > 0:
                    repair_pattern[i] = chr(cell_val + ord('A') - 1)
        repair_pattern_str = ''.join(repair_pattern)

        candidates = self.pattern_matcher.find(
            repair_pattern_str,
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

            # CRITICAL: Skip if placing this word would create gibberish
            if self._would_create_gibberish(word, slot, all_slots):
                continue  # Don't even try - creates invalid intersections

            # Save current state
            original_pattern = current_pattern

            # Try placing this word (skip if conflicts with locked cells)
            try:
                grid.place_word(word, slot['row'], slot['col'], slot['direction'])
            except ValueError:
                continue  # Word conflicts with locked cell, skip

            # Count new conflicts
            new_conflicts = self._find_conflicts(grid, all_slots)
            new_conflicts_for_slot = [c for c in new_conflicts if c.involves_slot(slot_id)]
            new_count = len(new_conflicts_for_slot)

            # Check if better
            if new_count < best_count:
                best_word = word
                best_count = new_count

            # Restore original
            if '?' not in original_pattern:  # Pattern has no wildcards - it's a real word
                try:
                    grid.place_word(original_pattern, slot['row'], slot['col'], slot['direction'])
                except ValueError:
                    grid.remove_word(slot['row'], slot['col'], slot['length'], slot['direction'])
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

    def _would_create_gibberish(
        self,
        word: str,
        slot: Dict,
        all_slots: List[Dict]
    ) -> bool:
        """
        Check if placing this word would create gibberish at perpendicular intersections.

        This prevents placing words that would create invalid short words or non-words
        in perpendicular directions.

        Args:
            word: Word to test
            slot: Slot where word would be placed
            all_slots: All slots in grid

        Returns:
            True if placing word would create gibberish, False otherwise
        """
        # Temporarily place the word to test intersections
        original_cells = {}

        # Save original state and place word
        for i in range(len(word)):
            if slot['direction'] == 'across':
                pos = (slot['row'], slot['col'] + i)
            else:  # down
                pos = (slot['row'] + i, slot['col'])

            original_cells[pos] = self.grid.cells[pos]
            self.grid.cells[pos] = ord(word[i]) - ord('A') + 1

        # Check all perpendicular slots for gibberish
        creates_gibberish = False
        perpendicular_direction = 'down' if slot['direction'] == 'across' else 'across'

        for other_slot in all_slots:
            # Only check perpendicular slots
            if other_slot['direction'] != perpendicular_direction:
                continue

            # Check if this slot intersects with our word
            intersection = self._get_intersection(slot, other_slot)
            if intersection is None:
                continue

            # Get the pattern this perpendicular slot would have
            pattern = self.grid.get_pattern_for_slot(other_slot)

            # Skip if entirely empty (no constraint)
            if pattern == '?' * len(pattern):
                continue

            # Skip if this is a fully locked theme word (can't modify it anyway)
            all_locked = True
            for i in range(other_slot['length']):
                if other_slot['direction'] == 'across':
                    check_pos = (other_slot['row'], other_slot['col'] + i)
                else:
                    check_pos = (other_slot['row'] + i, other_slot['col'])
                if check_pos not in self.grid.locked_cells:
                    all_locked = False
                    break
            if all_locked:
                continue  # Can't modify fully locked words

            # Check if pattern is gibberish:
            # 1. Fully filled but not in wordlist
            # 2. Has invalid short filled segments (e.g., "RDB????" has invalid "RDB")
            if '?' not in pattern:
                # Fully filled - check if it's a valid word
                if len(pattern) < 3:
                    creates_gibberish = True
                    break

                # Check if word exists in wordlist
                candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                word_exists = any(w == pattern for w, s in candidates)
                if not word_exists:
                    creates_gibberish = True
                    break
            else:
                # Partially filled - check for invalid ISOLATED segments
                # Only validate segments that CANNOT be extended (surrounded by non-wildcards)
                # Example: "ABC??DEF???" has segments "ABC", "DEF"
                # - "ABC" can be extended (followed by ?) - DON'T validate
                # - If pattern was "ABC#DEF??", "ABC" cannot extend - VALIDATE

                # Split pattern by wildcards to get segments with context
                i = 0
                while i < len(pattern):
                    if pattern[i] == '?':
                        i += 1
                        continue

                    # Found start of a filled segment
                    segment_start = i
                    segment = ""
                    while i < len(pattern) and pattern[i] != '?':
                        segment += pattern[i]
                        i += 1

                    # Only validate if segment is 3+ letters AND cannot be extended
                    if len(segment) >= 3:
                        # Check if segment can be extended on the right
                        can_extend_right = i < len(pattern) and pattern[i] == '?'
                        # Check if segment can be extended on the left
                        can_extend_left = segment_start > 0 and pattern[segment_start - 1] == '?'

                        # Only validate isolated segments (cannot extend either direction)
                        if not can_extend_right and not can_extend_left:
                            # This segment is isolated - must be a valid word
                            candidates = self.pattern_matcher.find(segment, min_score=self.min_score)
                            word_exists = any(w == segment for w, s in candidates)
                            if not word_exists:
                                creates_gibberish = True
                                break

                if creates_gibberish:
                    break

        # Restore original state
        for pos, val in original_cells.items():
            self.grid.cells[pos] = val

        return creates_gibberish

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
