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
import random

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
        Repair grid by fixing conflicts using multi-restart strategy.

        Algorithm:
        1. Generate initial fill (greedy, with gibberish checking)
        2. Repair loop with tabu search
        3. Focused CSP on remaining conflict regions
        4. If conflicts remain and time allows, restart with randomized fill
        5. Keep best result across all restarts

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

        overall_start = time.time()

        # Get all slots
        all_slots = self.grid.get_word_slots()
        total_slots = len(all_slots)

        # Save original grid for restarts
        original_grid = self.grid.cells.copy()
        original_locked = set(self.grid.locked_cells)

        best_result = None
        best_grid = None
        max_restarts = max(1, min(5, timeout // 15))  # Scale with timeout

        for restart in range(max_restarts):
            elapsed = time.time() - overall_start
            if elapsed > timeout * 0.95:
                break

            # Restore original grid for restart
            if restart > 0:
                self.grid.cells[:] = original_grid
                self.grid.locked_cells = set(original_locked)

                if self.progress_reporter:
                    best_p = len(best_result.problematic_slots) if best_result else '?'
                    self.progress_reporter.update(
                        5, f"Restart {restart+1}/{max_restarts} (best: {best_p} problems)"
                    )

            # Time budget for this attempt
            remaining = timeout - (time.time() - overall_start)
            attempts_left = max_restarts - restart
            attempt_timeout = remaining / attempts_left

            result = self._single_fill_attempt(
                all_slots, total_slots, attempt_timeout, restart
            )

            # Track best result
            if best_result is None or len(result.problematic_slots) < len(best_result.problematic_slots):
                best_result = result
                best_grid = self.grid.cells.copy()

            # Perfect fill — stop
            if result.success:
                break

        # Restore best grid
        if best_result and best_grid is not None and not best_result.success:
            self.grid.cells[:] = best_grid

        return best_result

    def _single_fill_attempt(
        self,
        all_slots: List[Dict],
        total_slots: int,
        timeout: float,
        restart_num: int
    ) -> 'FillResult':
        """Run a single fill+repair+CSP attempt."""
        from .autofill import FillResult

        # Reset timing for this attempt
        self.start_time = time.time()
        self.iterations = 0

        # Step 1: Generate initial fill if grid incomplete
        empty_slots = self.grid.get_empty_slots()
        if empty_slots:
            if self.progress_reporter:
                self.progress_reporter.update(10, "Generating initial fill")

            # Reserve 25% of time for initial fill
            fill_timeout = timeout * 0.25
            self._generate_initial_fill(
                empty_slots, fill_timeout, randomize=(restart_num > 0)
            )

        # Step 2: Find all conflicts
        conflicts = self._find_conflicts(self.grid, all_slots)
        best_conflict_count = len(conflicts)
        no_improvement_count = 0

        if self.progress_reporter:
            self.progress_reporter.update(30, f"Found {len(conflicts)} conflicts")

        # Recount conflicts
        best_conflict_count = len(conflicts)
        no_improvement_count = 0

        # Early exit if no conflicts remain
        if not conflicts:
            filled_slots = sum(
                1 for slot in all_slots
                if '?' not in self.grid.get_pattern_for_slot(slot)
            )
            unfilled = [
                {'slot': (s['row'], s['col'], s['direction']),
                 'pattern': self.grid.get_pattern_for_slot(s),
                 'reason': 'unfilled'}
                for s in all_slots
                if '?' in self.grid.get_pattern_for_slot(s)
            ]
            success = filled_slots == total_slots

            if self.progress_reporter:
                if success:
                    self.progress_reporter.update(100, f"Complete! {filled_slots}/{total_slots} slots filled")
                else:
                    self.progress_reporter.update(90, f"Partial: {filled_slots}/{total_slots} slots filled")

            return FillResult(
                success=success,
                grid=self.grid,
                time_elapsed=time.time() - self.start_time,
                slots_filled=filled_slots,
                total_slots=total_slots,
                problematic_slots=unfilled,
                iterations=self.iterations
            )

        # Step 3: Iterative repair loop with tabu search + random restarts
        # Use timeout as the real termination condition, not patience.
        # When stuck, randomly perturb (strip a few slots) to escape local optima.
        # Tabu list prevents oscillation (same slot→word swap cycling).
        # Reserve 40% of time for focused CSP (Step 4)
        repair_budget = timeout * 0.6
        tried_slots = set()
        stall_count = 0
        restart_count = 0
        max_restarts = 10
        # Tabu list: maps (slot_id, word) → iteration when tabu expires
        tabu_list: Dict[Tuple, int] = {}
        tabu_tenure = max(5, int(len(all_slots) ** 0.5))  # √n slots
        # Track best grid seen during repair (sideways moves may worsen then improve)
        best_repair_grid = self.grid.cells.copy()
        best_repair_conflicts = best_conflict_count

        while True:
            self.iterations += 1

            # Check timeout — stop early to leave time for focused CSP
            elapsed = time.time() - self.start_time
            if elapsed > repair_budget:
                break

            if not conflicts:
                break

            # Report progress
            if self.progress_reporter and self.iterations % 10 == 0:
                progress = min(85, 30 + int((elapsed / timeout) * 55))
                self.progress_reporter.update(
                    progress,
                    f"Repair iteration {self.iterations}: {len(conflicts)} conflicts"
                )

            # Find slot with most conflicts
            slot_conflict_counts = self._count_conflicts_per_slot(conflicts, all_slots)

            if not slot_conflict_counts:
                break

            # Get slots sorted by conflict count (descending)
            sorted_slots = sorted(slot_conflict_counts.items(), key=lambda x: -x[1])

            # Pick the worst slot we haven't tried recently
            culprit_slot_id = None
            for slot_id, count in sorted_slots:
                candidate = self._identify_culprit_slot(conflicts, slot_id, all_slots)

                # Skip theme-locked slots
                cslot = self._get_slot_by_id(candidate, all_slots)
                if cslot:
                    row, col, direction = candidate
                    has_locked = any(
                        (row + (i if direction == 'down' else 0),
                         col + (i if direction == 'across' else 0)) in self.grid.locked_cells
                        for i in range(cslot['length'])
                    )
                    if has_locked:
                        continue

                if candidate not in tried_slots:
                    culprit_slot_id = candidate
                    break

            if culprit_slot_id is None:
                # All slots tried — try random perturbation to escape local optimum
                tried_slots.clear()
                stall_count += 1

                if stall_count >= 3 and restart_count < max_restarts:
                    # Random perturbation: strip 2-4 conflicting slots and their neighbors
                    conflict_slots = list(slot_conflict_counts.keys())
                    if conflict_slots:
                        n_strip = min(len(conflict_slots), random.randint(2, 4))
                        to_strip = random.sample(conflict_slots, n_strip)
                        for sid in to_strip:
                            slot = self._get_slot_by_id(sid, all_slots)
                            if not slot:
                                continue
                            for i in range(slot['length']):
                                if slot['direction'] == 'across':
                                    pos = (slot['row'], slot['col'] + i)
                                else:
                                    pos = (slot['row'] + i, slot['col'])
                                if pos not in self.grid.locked_cells:
                                    self.grid.cells[pos] = 0

                        # Re-fill stripped slots
                        refill_slots = self._sort_slots_by_constraint(
                            [s for s in all_slots if '?' in self.grid.get_pattern_for_slot(s)]
                        )
                        used_words = set()
                        for s in all_slots:
                            p = self.grid.get_pattern_for_slot(s)
                            if '?' not in p:
                                used_words.add(p)

                        for slot in refill_slots:
                            pattern = self.grid.get_pattern_for_slot(slot)
                            if '?' not in pattern:
                                continue
                            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                            for word, score in candidates:
                                if word not in used_words:
                                    try:
                                        self.grid.place_word(
                                            word, slot['row'], slot['col'], slot['direction']
                                        )
                                        used_words.add(word)
                                        break
                                    except ValueError:
                                        continue

                        conflicts = self._find_conflicts(self.grid, all_slots)
                        if len(conflicts) < best_conflict_count:
                            best_conflict_count = len(conflicts)
                        stall_count = 0
                        restart_count += 1
                continue

            tried_slots.add(culprit_slot_id)

            # Try to repair the culprit slot (with tabu list)
            improved, best_word = self._try_repair_slot(
                self.grid,
                culprit_slot_id,
                conflicts,
                all_slots,
                tabu_list=tabu_list,
                current_iteration=self.iterations,
                best_conflict_count=best_conflict_count
            )

            if improved and best_word:
                # Record old word as tabu (don't swap back for tabu_tenure iterations)
                slot = self._get_slot_by_id(culprit_slot_id, all_slots)
                old_word = self.grid.get_pattern_for_slot(slot)
                tabu_list[(culprit_slot_id, old_word)] = self.iterations + tabu_tenure

                self.grid.place_word(
                    best_word,
                    slot['row'],
                    slot['col'],
                    slot['direction']
                )

                # Recompute conflicts
                conflicts = self._find_conflicts(self.grid, all_slots)
                tried_slots.clear()
                stall_count = 0

                if len(conflicts) < best_conflict_count:
                    best_conflict_count = len(conflicts)
                    no_improvement_count = 0
                if len(conflicts) < best_repair_conflicts:
                    best_repair_conflicts = len(conflicts)
                    best_repair_grid = self.grid.cells.copy()

                if not conflicts:
                    break
            else:
                no_improvement_count += 1

        # Restore best grid seen during repair (sideways moves may have worsened it)
        if best_repair_conflicts < len(self._find_conflicts(self.grid, all_slots)):
            self.grid.cells[:] = best_repair_grid
            conflicts = self._find_conflicts(self.grid, all_slots)

        # Step 4: Pairwise conflict resolution
        # For each invalid word, strip it and its worst crossing, then backtrack
        # just those 2 slots. Small enough for reliable backtracking.
        remaining_time = timeout - (time.time() - self.start_time)
        if remaining_time > 2:
            current_conflicts = self._find_conflicts(self.grid, all_slots)
            # Get unique invalid word slots (self-conflicts)
            invalid_slots = []
            for c in current_conflicts:
                if c.slot1_id == c.slot2_id and c.slot1_id not in [s for s, _ in invalid_slots]:
                    # Find a crossing that's also conflicting
                    crossing_id = None
                    slot = self._get_slot_by_id(c.slot1_id, all_slots)
                    if slot:
                        for other in all_slots:
                            if other['direction'] == slot['direction']:
                                continue
                            if self._get_intersection(slot, other) is not None:
                                other_id = (other['row'], other['col'], other['direction'])
                                # Prefer crossing slots that are also invalid
                                other_p = self.grid.get_pattern_for_slot(other)
                                if '?' not in other_p:
                                    other_matches = self.pattern_matcher.find(other_p, min_score=self.min_score)
                                    if not any(w == other_p for w, s in other_matches):
                                        crossing_id = other_id
                                        break
                        if crossing_id is None:
                            # No invalid crossing — just pick first crossing
                            for other in all_slots:
                                if other['direction'] == slot['direction']:
                                    continue
                                if self._get_intersection(slot, other) is not None:
                                    crossing_id = (other['row'], other['col'], other['direction'])
                                    break
                    invalid_slots.append((c.slot1_id, crossing_id))

            random.shuffle(invalid_slots)

            if self.progress_reporter:
                self.progress_reporter.update(
                    85, f"Pairwise CSP: {len(invalid_slots)} conflicts"
                )

            for pair_idx, (slot_id, crossing_id) in enumerate(invalid_slots):
                elapsed = time.time() - self.start_time
                if elapsed > timeout - 1:
                    break

                saved_grid = self.grid.cells.copy()
                pre_count = len(self._find_conflicts(self.grid, all_slots))

                # Strip both slots
                pair_ids = {slot_id}
                if crossing_id:
                    pair_ids.add(crossing_id)

                for sid in pair_ids:
                    slot = self._get_slot_by_id(sid, all_slots)
                    if not slot:
                        continue
                    for i in range(slot['length']):
                        if slot['direction'] == 'across':
                            pos = (slot['row'], slot['col'] + i)
                        else:
                            pos = (slot['row'] + i, slot['col'])
                        if pos not in self.grid.locked_cells:
                            self.grid.cells[pos] = 0

                # Build region slots and used words
                region_slots = []
                for sid in pair_ids:
                    s = self._get_slot_by_id(sid, all_slots)
                    if s:
                        region_slots.append(s)
                region_slots = self._sort_slots_by_constraint(region_slots)

                used_words = set()
                for s in all_slots:
                    sid2 = (s['row'], s['col'], s['direction'])
                    if sid2 not in pair_ids:
                        p = self.grid.get_pattern_for_slot(s)
                        if '?' not in p:
                            used_words.add(p)

                bt_time = min(5.0, timeout - (time.time() - self.start_time))
                solved = self._backtrack_region(
                    region_slots, 0, used_words, all_slots,
                    time.time(), bt_time
                )

                if not solved:
                    # Greedy refill
                    for slot in region_slots:
                        pattern = self.grid.get_pattern_for_slot(slot)
                        if '?' not in pattern:
                            continue
                        candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                        for word, score in candidates:
                            if word not in used_words:
                                try:
                                    self.grid.place_word(
                                        word, slot['row'], slot['col'], slot['direction']
                                    )
                                    used_words.add(word)
                                    break
                                except ValueError:
                                    continue

                post_count = len(self._find_conflicts(self.grid, all_slots))
                if post_count >= pre_count:
                    self.grid.cells[:] = saved_grid
                elif post_count == 0:
                    break

        # Step 5: Final fill — try remaining empty slots with gibberish check
        remaining = [s for s in all_slots if '?' in self.grid.get_pattern_for_slot(s)]
        if remaining:
            used_words = set()
            for s in all_slots:
                p = self.grid.get_pattern_for_slot(s)
                if '?' not in p:
                    used_words.add(p)

            for slot in remaining:
                pattern = self.grid.get_pattern_for_slot(slot)
                if '?' not in pattern:
                    continue
                candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                for word, score in candidates:
                    if word not in used_words:
                        if self._would_create_gibberish(word, slot, all_slots):
                            continue
                        try:
                            self.grid.place_word(
                                word, slot['row'], slot['col'], slot['direction']
                            )
                            used_words.add(word)
                            break
                        except ValueError:
                            continue

        # Return result
        time_elapsed = time.time() - self.start_time

        # Count filled slots
        filled_slots = sum(
            1 for slot in all_slots
            if '?' not in self.grid.get_pattern_for_slot(slot)
        )

        # Final conflict check — verify all words are valid
        final_conflicts = self._find_conflicts(self.grid, all_slots)

        # Find problematic slots (empty, conflicting, or invalid)
        problematic_slots = []
        conflict_slot_ids = set()
        for c in final_conflicts:
            conflict_slot_ids.add(c.slot1_id)
            if c.slot2_id != c.slot1_id:
                conflict_slot_ids.add(c.slot2_id)

        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            slot_id = (slot['row'], slot['col'], slot['direction'])
            if '?' in pattern:
                problematic_slots.append({
                    'slot': slot_id,
                    'pattern': pattern,
                    'reason': 'unfilled'
                })
            elif slot_id in conflict_slot_ids:
                problematic_slots.append({
                    'slot': slot_id,
                    'pattern': pattern,
                    'reason': 'invalid_word'
                })

        # Success = all slots filled AND no conflicts (including invalid words)
        success = filled_slots == total_slots and len(final_conflicts) == 0

        if self.progress_reporter:
            if success:
                self.progress_reporter.update(100, f"Complete! {filled_slots}/{total_slots} slots filled")
            else:
                self.progress_reporter.update(
                    90,
                    f"Partial fill: {filled_slots}/{total_slots} slots, {len(problematic_slots)} unfilled"
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
        timeout: float,
        randomize: bool = False
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
            randomize: If True, shuffle top candidates on all passes (for restarts)
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

                # Shuffle candidates to diversify fills:
                # - On restart attempts: always shuffle (all passes)
                # - Normal: only shuffle on passes 2+
                if (randomize or pass_num > 0) and len(candidates) > 5:
                    top = list(candidates[:20])
                    random.shuffle(top)
                    candidates = top + list(candidates[20:])

                placed = False
                for word, score in candidates:
                    if word in used_words:
                        continue

                    # Pass 1: strict gibberish check (min 2 filled letters)
                    # Pass 2+: skip gibberish check (repair loop fixes conflicts)
                    if pass_num == 0 and self._would_create_gibberish(
                        word, slot, all_slots, min_filled=2
                    ):
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

        # STEP 2: Flag invalid words (filled but not in wordlist) as pseudo-conflicts
        # Swapping these triggers cascading improvements in crossing slots
        for slot in slots:
            pattern = grid.get_pattern_for_slot(slot)
            if '?' in pattern:
                continue  # Not fully filled
            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
            word_exists = any(word == pattern for word, score in candidates)
            if not word_exists:
                slot_id = (slot['row'], slot['col'], slot['direction'])
                conflicts.append(Conflict(
                    slot1_id=slot_id,
                    slot2_id=slot_id,
                    position1=0,
                    position2=0,
                    letter1=pattern[0] if pattern else '?',
                    letter2='?',
                ))

        # STEP 3: Flag unfillable partially-filled slots as pseudo-conflicts
        # Only for slots where crossing letters create an impossible pattern
        # (not slots unfillable due to wordlist lacking words of that length)
        for slot in slots:
            pattern = grid.get_pattern_for_slot(slot)
            if '?' not in pattern:
                continue
            if pattern == '?' * len(pattern):
                continue  # Fully empty — not constrained by crossings

            # Check if ANY word of this length exists
            wildcard = '?' * len(pattern)
            if not self.pattern_matcher.find(wildcard, min_score=self.min_score):
                continue  # No words of this length in wordlist — not a crossing issue

            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
            if not candidates:
                slot_id = (slot['row'], slot['col'], slot['direction'])
                for other in slots:
                    if other['direction'] == slot['direction']:
                        continue
                    intersection = self._get_intersection(slot, other)
                    if intersection is None:
                        continue
                    pos_in_slot, pos_in_other = intersection
                    if pattern[pos_in_slot] != '?':
                        other_id = (other['row'], other['col'], other['direction'])
                        conflicts.append(Conflict(
                            slot1_id=slot_id,
                            slot2_id=other_id,
                            position1=pos_in_slot,
                            position2=pos_in_other,
                            letter1=pattern[pos_in_slot],
                            letter2='?',
                        ))
                        break

        return conflicts

    def _try_repair_slot(
        self,
        grid: Grid,
        slot_id: Tuple[int, int, str],
        conflicts: List[Conflict],
        all_slots: List[Dict],
        tabu_list: Optional[Dict[Tuple, int]] = None,
        current_iteration: int = 0,
        best_conflict_count: int = 999
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to find better word for slot that reduces conflicts.

        Uses tabu search: skips (slot, word) pairs that are tabu (recently
        swapped away from), UNLESS the word achieves a new best conflict count
        (aspiration criterion).

        Args:
            grid: Current grid
            slot_id: (row, col, direction) of slot to repair
            conflicts: Current conflicts in grid
            all_slots: All slots in grid
            tabu_list: Maps (slot_id, word) → expiry iteration
            current_iteration: Current repair iteration number
            best_conflict_count: Best conflict count seen so far (for aspiration)

        Returns:
            (improved, best_word) where:
            - improved: True if found better word
            - best_word: Word to use (None if no improvement)

        Complexity: O(candidates × conflict_counting)
        """
        # Count current TOTAL conflicts (for global optimization)
        current_count = len(conflicts)

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

        # Limit to top 100 (more candidates = better chance of finding valid swaps)
        candidates = candidates[:100]

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

            # Save cell values before placing (to restore exactly)
            saved_cells = {}
            for i in range(slot['length']):
                if slot['direction'] == 'across':
                    pos = (slot['row'], slot['col'] + i)
                else:
                    pos = (slot['row'] + i, slot['col'])
                saved_cells[pos] = grid.cells[pos]

            # Try placing this word (skip if conflicts with locked cells)
            try:
                grid.place_word(word, slot['row'], slot['col'], slot['direction'])
            except ValueError:
                continue  # Word conflicts with locked cell, skip

            # Count new TOTAL conflicts
            new_conflicts = self._find_conflicts(grid, all_slots)
            new_count = len(new_conflicts)

            # Tabu check
            is_tabu = (
                tabu_list is not None
                and (slot_id, word) in tabu_list
                and tabu_list[(slot_id, word)] > current_iteration
            )
            if is_tabu and new_count >= best_conflict_count:
                for pos, val in saved_cells.items():
                    grid.cells[pos] = val
                continue

            # Accept if strictly better
            if new_count < best_count:
                best_word = word
                best_count = new_count
            elif new_count == current_count and best_word is None and random.random() < 0.3:
                # Accept sideways move with 30% probability (shifts conflicts)
                best_word = word
                best_count = new_count

            # Restore original cell values exactly
            for pos, val in saved_cells.items():
                grid.cells[pos] = val

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

    def _backtrack_region(
        self,
        region_slots: List[Dict],
        index: int,
        used_words: set,
        all_slots: List[Dict],
        start_time: float,
        timeout: float
    ) -> bool:
        """
        Backtracking CSP solver for a small region of the grid.

        Fills region_slots using backtracking with forward checking.
        Checks that placed words don't create invalid perpendicular patterns.

        Args:
            region_slots: Slots in the region to fill (sorted by constraint)
            index: Current position in region_slots
            used_words: Words already used in non-region slots
            all_slots: All slots in the grid (for intersection checking)
            start_time: When this backtracking attempt started
            timeout: Maximum seconds for this attempt

        Returns:
            True if region successfully filled, False otherwise
        """
        if time.time() - start_time > timeout:
            return False

        if index >= len(region_slots):
            return True  # All region slots filled

        slot = region_slots[index]
        pattern = self.grid.get_pattern_for_slot(slot)

        if '?' not in pattern:
            # Already filled (by a crossing word placement)
            return self._backtrack_region(
                region_slots, index + 1, used_words, all_slots,
                start_time, timeout
            )

        candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)

        # Limit candidates for speed
        # Limit candidates — fewer = faster backtracking, more = better solutions
        candidates = candidates[:100]

        for word, score in candidates:
            if word in used_words:
                continue

            # Check perpendicular constraints: would this create an impossible
            # pattern in any crossing slot?
            creates_dead_end = False
            perp_dir = 'down' if slot['direction'] == 'across' else 'across'

            # Temporarily place word
            saved_cells = {}
            for i in range(len(word)):
                if slot['direction'] == 'across':
                    pos = (slot['row'], slot['col'] + i)
                else:
                    pos = (slot['row'] + i, slot['col'])
                saved_cells[pos] = self.grid.cells[pos]
                self.grid.cells[pos] = ord(word[i]) - ord('A') + 1

            # Check crossing slots
            for other_slot in all_slots:
                if other_slot['direction'] != perp_dir:
                    continue
                if self._get_intersection(slot, other_slot) is None:
                    continue

                other_pattern = self.grid.get_pattern_for_slot(other_slot)
                if '?' not in other_pattern:
                    # Fully filled — must be valid
                    match = self.pattern_matcher.find(other_pattern, min_score=self.min_score)
                    if not any(w == other_pattern for w, s in match):
                        creates_dead_end = True
                        break
                else:
                    # Partially filled — must have at least one candidate
                    filled = sum(1 for c in other_pattern if c != '?')
                    if filled >= 2:
                        match = self.pattern_matcher.find(other_pattern, min_score=self.min_score)
                        # Filter out used words
                        available = [w for w, s in match if w not in used_words]
                        if not available:
                            creates_dead_end = True
                            break

            if creates_dead_end:
                # Restore and try next candidate
                for pos, val in saved_cells.items():
                    self.grid.cells[pos] = val
                continue

            # Word looks viable — recurse
            used_words.add(word)
            if self._backtrack_region(
                region_slots, index + 1, used_words, all_slots,
                start_time, timeout
            ):
                return True

            # Backtrack: remove word
            used_words.discard(word)
            for pos, val in saved_cells.items():
                self.grid.cells[pos] = val

        return False

    def _would_create_gibberish(
        self,
        word: str,
        slot: Dict,
        all_slots: List[Dict],
        min_filled: int = 2
    ) -> bool:
        """
        Check if placing this word would create gibberish at perpendicular intersections.

        This prevents placing words that would create invalid short words or non-words
        in perpendicular directions.

        Args:
            word: Word to test
            slot: Slot where word would be placed
            all_slots: All slots in grid
            min_filled: Minimum number of filled letters in a perpendicular pattern
                       before checking for candidates. Lower = stricter check.

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
            # 1. Fully filled but not in wordlist → always reject
            # 2. Partially filled: only reject if majority filled and no matches
            #    (checking too early is too restrictive and prevents progress)
            if '?' not in pattern:
                # Fully filled - must be a valid word
                if len(pattern) < 3:
                    creates_gibberish = True
                    break

                candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                word_exists = any(w == pattern for w, s in candidates)
                if not word_exists:
                    creates_gibberish = True
                    break
            else:
                # Partially filled — check if at least one candidate exists
                filled_count = sum(1 for c in pattern if c != '?')
                if filled_count >= min_filled:
                    candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                    if not candidates:
                        creates_gibberish = True
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

    def _backtrack_unfillable(
        self,
        unfillable_slots: List[Dict],
        all_slots: List[Dict],
        timeout: float
    ) -> None:
        """
        Fix unfillable slots by replacing crossing words that create impossible patterns.

        For each unfillable slot:
        1. Find which crossing words contribute letters to the impossible pattern
        2. Try replacing each crossing word with an alternative
        3. After replacement, try to fill the previously-unfillable slot
        4. If it works, keep the change. If not, restore and try next crossing word.
        """
        used_words = set()
        for s in all_slots:
            p = self.grid.get_pattern_for_slot(s)
            if '?' not in p:
                used_words.add(p)

        for unfillable in unfillable_slots:
            if time.time() - self.start_time > timeout * 0.8:
                break

            pattern = self.grid.get_pattern_for_slot(unfillable)
            if '?' not in pattern:
                continue  # Already filled by a previous backtrack

            # Find crossing slots that contribute filled letters to this slot
            crossing_slots = []
            for other in all_slots:
                if other['direction'] == unfillable['direction']:
                    continue
                intersection = self._get_intersection(unfillable, other)
                if intersection is None:
                    continue
                pos_in_unfillable, pos_in_other = intersection
                # Only care about positions that ARE filled (not '?')
                if pattern[pos_in_unfillable] != '?':
                    other_pattern = self.grid.get_pattern_for_slot(other)
                    if '?' not in other_pattern:
                        crossing_slots.append((other, pos_in_unfillable, pos_in_other))

            # Try replacing each crossing word
            fixed = False
            for crossing, pos_in_target, pos_in_crossing in crossing_slots:
                if fixed:
                    break
                if time.time() - self.start_time > timeout * 0.8:
                    break

                crossing_id = (crossing['row'], crossing['col'], crossing['direction'])

                # Skip locked slots
                has_locked = False
                for i in range(crossing['length']):
                    if crossing['direction'] == 'across':
                        pos = (crossing['row'], crossing['col'] + i)
                    else:
                        pos = (crossing['row'] + i, crossing['col'])
                    if pos in self.grid.locked_cells:
                        has_locked = True
                        break
                if has_locked:
                    continue

                # Save state of crossing slot cells
                saved = {}
                for i in range(crossing['length']):
                    if crossing['direction'] == 'across':
                        pos = (crossing['row'], crossing['col'] + i)
                    else:
                        pos = (crossing['row'] + i, crossing['col'])
                    saved[pos] = self.grid.cells[pos]

                old_word = self.grid.get_pattern_for_slot(crossing)

                # Get alternative words for the crossing slot
                # Use full wildcard to get more candidates
                repair_pattern = list('?' * crossing['length'])
                for i in range(crossing['length']):
                    if crossing['direction'] == 'across':
                        pos = (crossing['row'], crossing['col'] + i)
                    else:
                        pos = (crossing['row'] + i, crossing['col'])
                    if pos in self.grid.locked_cells:
                        cell_val = self.grid.cells[pos]
                        if cell_val > 0:
                            repair_pattern[i] = chr(cell_val + ord('A') - 1)

                # But keep letters from OTHER crossings (not the unfillable one)
                for other2 in all_slots:
                    if other2['direction'] == crossing['direction']:
                        continue
                    if other2 is unfillable:
                        continue  # Skip — this is the one we want to change
                    inter = self._get_intersection(crossing, other2)
                    if inter is None:
                        continue
                    pos_in_c, pos_in_o = inter
                    other_p = self.grid.get_pattern_for_slot(other2)
                    if '?' not in other_p:
                        # This crossing is constrained by other2
                        repair_pattern[pos_in_c] = other_p[pos_in_o]

                repair_str = ''.join(repair_pattern)
                candidates = self.pattern_matcher.find(repair_str, min_score=self.min_score)

                for alt_word, score in candidates[:30]:
                    if alt_word == old_word:
                        continue
                    if alt_word in used_words:
                        continue

                    # Place alternative crossing word
                    try:
                        self.grid.place_word(
                            alt_word, crossing['row'], crossing['col'], crossing['direction']
                        )
                    except ValueError:
                        continue

                    # Check if unfillable slot now has candidates
                    new_pattern = self.grid.get_pattern_for_slot(unfillable)
                    new_candidates = self.pattern_matcher.find(new_pattern, min_score=self.min_score)
                    fillable_candidates = [
                        (w, s) for w, s in new_candidates if w not in used_words and w != alt_word
                    ]

                    if fillable_candidates:
                        # Before accepting: check we didn't create NEW unfillable slots
                        # by changing this crossing word
                        creates_new_problem = False
                        for check_slot in all_slots:
                            if check_slot is unfillable:
                                continue
                            cp = self.grid.get_pattern_for_slot(check_slot)
                            if '?' not in cp:
                                continue
                            # This slot has wildcards — check it's still fillable
                            check_cands = self.pattern_matcher.find(cp, min_score=self.min_score)
                            if not check_cands:
                                creates_new_problem = True
                                break

                        if creates_new_problem:
                            # Restore and try next candidate
                            for pos, val in saved.items():
                                self.grid.cells[pos] = val
                            continue

                        # Fill the previously-unfillable slot
                        fill_word = fillable_candidates[0][0]
                        try:
                            self.grid.place_word(
                                fill_word, unfillable['row'], unfillable['col'],
                                unfillable['direction']
                            )
                            # Success! Update used_words
                            used_words.discard(old_word)
                            used_words.add(alt_word)
                            used_words.add(fill_word)
                            fixed = True
                            break
                        except ValueError:
                            pass

                    # Restore crossing slot
                    for pos, val in saved.items():
                        self.grid.cells[pos] = val

                if not fixed:
                    # Make sure state is restored if we never found a fix
                    for pos, val in saved.items():
                        self.grid.cells[pos] = val

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
