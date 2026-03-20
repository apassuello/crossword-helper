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
        theme_words=None,
        all_valid_words: set = None
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
            all_valid_words: Set of ALL valid words across all wordlists (for validation only)

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
        self.all_valid_words = all_valid_words or set()

        # State tracking
        self.start_time = 0.0
        self.iterations = 0
        self._last_snapshot_time = 0.0

    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid against all available wordlists, theme words, and theme entries."""
        if self.all_valid_words and word in self.all_valid_words:
            return True
        if self.theme_words and word in self.theme_words:
            return True
        if self.theme_entries and word in {w.upper() for w in self.theme_entries.values()}:
            return True
        return False

    def _emit_grid_snapshot(self, progress: int, message: str, force: bool = False) -> None:
        """Emit current grid state for live UI updates. Rate-limited to every 2s."""
        if not self.progress_reporter:
            return
        now = time.time()
        if not force and now - self._last_snapshot_time < 2.0:
            return
        self._last_snapshot_time = now
        grid_data = self.grid.to_dict()["grid"]
        self.progress_reporter.update(progress, message, data={'grid': grid_data})

    def fill(self, timeout: int = 300) -> FillResult:
        """
        Fill grid using region-based backtracking with multi-restart.

        Strategy:
        1. Keep existing valid fill intact
        2. Try to fill empty slots directly
        3. For dead-end slots (0 candidates), identify connected conflict regions
        4. Strip and refill each region using backtracking CSP
        5. Multiple restarts with randomization

        Args:
            timeout: Maximum seconds to spend

        Returns:
            FillResult with filled grid

        Raises:
            ValueError: If timeout < 10 seconds
        """
        from .autofill import FillResult

        if timeout < 10:
            raise ValueError(f"timeout must be ≥10 seconds, got {timeout}")

        overall_start = time.time()
        all_slots = self.grid.get_word_slots()
        total_slots = len(all_slots)

        # Save original grid
        original_grid = self.grid.cells.copy()
        original_locked = set(self.grid.locked_cells)

        # Build intersection cache
        self._intersection_cache = {}
        for i, s1 in enumerate(all_slots):
            s1_id = (s1['row'], s1['col'], s1['direction'])
            for j in range(i + 1, len(all_slots)):
                s2 = all_slots[j]
                s2_id = (s2['row'], s2['col'], s2['direction'])
                inter = self._get_intersection(s1, s2)
                if inter is not None:
                    self._intersection_cache[(s1_id, s2_id)] = inter
                    self._intersection_cache[(s2_id, s1_id)] = (inter[1], inter[0])

        best_result = None
        best_grid = None
        max_restarts = max(1, min(10, timeout // 15))

        for restart in range(max_restarts):
            elapsed = time.time() - overall_start
            if elapsed > timeout * 0.95:
                break

            # On restart: if we have a good result (>80% filled), don't wipe —
            # continue from best grid to preserve user-visible progress
            if restart == 0:
                pass  # First attempt: use grid as-is
            elif best_result and best_result.slots_filled > total_slots * 0.8:
                # Good progress — restart from best, don't wipe
                self.grid.cells[:] = best_grid
                self.grid.locked_cells = set(original_locked)
            else:
                # Poor progress — restart from scratch
                self.grid.cells[:] = original_grid
                self.grid.locked_cells = set(original_locked)

            if self.progress_reporter:
                if restart == 0:
                    self.progress_reporter.update(5, "Analyzing grid")
                else:
                    best_p = len(best_result.problematic_slots) if best_result else '?'
                    self._emit_grid_snapshot(
                        5, f"Restart {restart+1}/{max_restarts} (best: {best_p} problems)",
                        force=True
                    )

            remaining = timeout - (time.time() - overall_start)
            attempts_left = max_restarts - restart
            attempt_timeout = remaining / attempts_left

            result = self._region_fill_attempt(
                all_slots, total_slots, attempt_timeout,
                randomize=(restart > 0), restart_num=restart
            )

            if best_result is None or len(result.problematic_slots) < len(best_result.problematic_slots):
                best_result = result
                best_grid = self.grid.cells.copy()

            if result.success:
                break

        if best_result and best_grid is not None:
            self.grid.cells[:] = best_grid

        return best_result

    def _region_fill_attempt(
        self,
        all_slots: List[Dict],
        total_slots: int,
        timeout: float,
        randomize: bool = False,
        restart_num: int = 0
    ) -> 'FillResult':
        """
        Fill attempt using region-based strategy:
        1. Find dead-end empty slots (0 candidates due to crossing constraints)
        2. Identify which non-locked crossing words cause the dead ends
        3. Strip those crossing words + the dead-end slots → "conflict region"
        4. Backtrack-fill the entire conflict region
        5. Fill remaining easy empty slots greedily
        """
        from .autofill import FillResult

        self.start_time = time.time()
        self.iterations = 0

        # Step 1: Find dead-end slots and their blocking crossings
        dead_end_slots, blocking_words = self._find_dead_ends_and_blockers(all_slots)

        if self.progress_reporter:
            empty_count = sum(1 for s in all_slots if '?' in self.grid.get_pattern_for_slot(s))
            self.progress_reporter.update(
                10, f"{empty_count} empty slots, {len(dead_end_slots)} dead ends, "
                    f"{len(blocking_words)} blocking words"
            )

        # Step 2: Strip blocking words (non-locked crossing words that cause dead ends)
        stripped_slot_ids = set()
        for slot_id in blocking_words:
            slot = self._get_slot_by_id(slot_id, all_slots)
            if not slot:
                continue
            stripped_slot_ids.add(slot_id)
            for i in range(slot['length']):
                if slot['direction'] == 'across':
                    pos = (slot['row'], slot['col'] + i)
                else:
                    pos = (slot['row'] + i, slot['col'])
                if pos not in self.grid.locked_cells:
                    self.grid.cells[pos] = 0

        if self.progress_reporter:
            self.progress_reporter.update(15, f"Stripped {len(stripped_slot_ids)} blocking words")

        # Step 3: Collect all slots that need filling (empty + stripped)
        slots_to_fill = []
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' in pattern:
                slots_to_fill.append(slot)

        if not slots_to_fill:
            return self._build_result(all_slots, total_slots)

        # Step 4: Fill using CSP backtracking with dynamic MRV
        used_words = set()
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:
                used_words.add(pattern)

        csp_timeout = timeout * 0.85
        solved = self._csp_backtrack(
            slots_to_fill, 0, used_words, all_slots, csp_timeout, randomize
        )

        if not solved:
            # Step 5: Multi-pass greedy fill (strict → relaxed)
            self._multi_pass_greedy_fill(all_slots, timeout * 0.15, randomize)

        # Step 6: Repair loop — swap invalid words for valid ones
        remaining_time = timeout - (time.time() - self.start_time)
        if remaining_time > 2:
            self._repair_invalid_words(all_slots, remaining_time, randomize)

        return self._build_result(all_slots, total_slots)

    def _multi_pass_greedy_fill(
        self, all_slots: List[Dict], timeout: float, randomize: bool
    ) -> None:
        """Fill empty slots greedily: strict pass (gibberish check), then relaxed."""
        start = time.time()

        for pass_num in range(3):
            if time.time() - start > timeout:
                break

            remaining = [s for s in all_slots if '?' in self.grid.get_pattern_for_slot(s)]
            if not remaining:
                break

            if self.progress_reporter:
                self._emit_grid_snapshot(
                    60 + pass_num * 8, f"Greedy pass {pass_num+1}: {len(remaining)} slots left"
                )

            remaining = self._sort_slots_by_constraint(remaining)
            used_words = set()
            for s in all_slots:
                p = self.grid.get_pattern_for_slot(s)
                if '?' not in p:
                    used_words.add(p)

            placed = 0
            for slot in remaining:
                pattern = self.grid.get_pattern_for_slot(slot)
                if '?' not in pattern:
                    continue

                candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
                if randomize and len(candidates) > 5:
                    top = list(candidates[:20])
                    random.shuffle(top)
                    candidates = top + list(candidates[20:])

                for word, score in candidates:
                    if word in used_words:
                        continue
                    # Pass 0: strict gibberish check
                    if pass_num == 0 and self._would_create_gibberish(
                        word, slot, all_slots, min_filled=2
                    ):
                        continue
                    try:
                        self.grid.place_word(word, slot['row'], slot['col'], slot['direction'])
                        used_words.add(word)
                        placed += 1
                        break
                    except ValueError:
                        continue

            if placed == 0:
                break

    def _repair_invalid_words(
        self, all_slots: List[Dict], timeout: float, randomize: bool
    ) -> None:
        """Swap invalid words for valid alternatives that reduce total conflicts."""
        repair_start = time.time()
        conflicts = self._find_conflicts(self.grid, all_slots)
        if not conflicts:
            return

        best_conflict_count = len(conflicts)
        best_grid = self.grid.cells.copy()
        tabu_list: Dict[Tuple, int] = {}
        tabu_tenure = max(5, int(len(all_slots) ** 0.5))
        tried_slots = set()
        iteration = 0

        if self.progress_reporter:
            self.progress_reporter.update(80, f"Repairing {len(conflicts)} invalid words")

        while conflicts:
            iteration += 1
            if time.time() - repair_start > timeout:
                break

            slot_counts = self._count_conflicts_per_slot(conflicts, all_slots)
            if not slot_counts:
                break

            sorted_slots = sorted(slot_counts.items(), key=lambda x: -x[1])

            culprit = None
            for slot_id, count in sorted_slots:
                candidate = self._identify_culprit_slot(conflicts, slot_id, all_slots)
                cslot = self._get_slot_by_id(candidate, all_slots)
                if cslot and self._slot_fully_locked(cslot):
                    continue
                if candidate not in tried_slots:
                    culprit = candidate
                    break

            if culprit is None:
                tried_slots.clear()
                continue

            tried_slots.add(culprit)

            improved, best_word = self._try_repair_slot(
                self.grid, culprit, conflicts, all_slots,
                tabu_list=tabu_list, current_iteration=iteration,
                best_conflict_count=best_conflict_count
            )

            if improved and best_word:
                slot = self._get_slot_by_id(culprit, all_slots)
                old_word = self.grid.get_pattern_for_slot(slot)
                tabu_list[(culprit, old_word)] = iteration + tabu_tenure
                self.grid.place_word(best_word, slot['row'], slot['col'], slot['direction'])
                conflicts = self._find_conflicts(self.grid, all_slots)
                tried_slots.clear()
                if len(conflicts) < best_conflict_count:
                    best_conflict_count = len(conflicts)
                    best_grid = self.grid.cells.copy()
                self._emit_grid_snapshot(
                    85, f"Repairing: {len(conflicts)} conflicts left"
                )
                if not conflicts:
                    break

        # Restore best seen
        if best_conflict_count < len(self._find_conflicts(self.grid, all_slots)):
            self.grid.cells[:] = best_grid

    def _find_dead_ends_and_blockers(
        self, all_slots: List[Dict]
    ) -> Tuple[List[Dict], set]:
        """
        Find empty slots with 0 candidates, the non-locked crossing words
        that cause them, AND neighbors of those blockers (to expand the
        cleared region for better backtracking).

        Returns:
            (dead_end_slots, blocking_word_slot_ids)
        """
        dead_ends = []
        direct_blockers = set()

        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:
                continue

            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
            if candidates:
                continue

            dead_ends.append(slot)
            slot_id = (slot['row'], slot['col'], slot['direction'])

            for other in all_slots:
                if other['direction'] == slot['direction']:
                    continue
                other_id = (other['row'], other['col'], other['direction'])
                cache_key = (slot_id, other_id)
                if cache_key not in self._intersection_cache:
                    continue

                pos_in_slot, pos_in_other = self._intersection_cache[cache_key]
                if pattern[pos_in_slot] != '?':
                    if not self._slot_fully_locked(other):
                        direct_blockers.add(other_id)

        # Expand: also strip words that cross the blockers (neighbors)
        # This gives backtracking more room to find solutions
        all_blockers = set(direct_blockers)
        for blocker_id in direct_blockers:
            blocker = self._get_slot_by_id(blocker_id, all_slots)
            if not blocker:
                continue
            for other in all_slots:
                if other['direction'] == blocker['direction']:
                    continue
                other_id = (other['row'], other['col'], other['direction'])
                cache_key = (blocker_id, other_id)
                if cache_key not in self._intersection_cache:
                    continue
                if not self._slot_fully_locked(other):
                    other_pattern = self.grid.get_pattern_for_slot(other)
                    if '?' not in other_pattern:  # Only strip filled words
                        all_blockers.add(other_id)

        return dead_ends, all_blockers

    def _slot_fully_locked(self, slot: Dict) -> bool:
        """Check if ALL cells of a slot are locked."""
        for i in range(slot['length']):
            if slot['direction'] == 'across':
                pos = (slot['row'], slot['col'] + i)
            else:
                pos = (slot['row'] + i, slot['col'])
            if pos not in self.grid.locked_cells:
                return False
        return True

    def _csp_backtrack(
        self,
        slots: List[Dict],
        index: int,
        used_words: set,
        all_slots: List[Dict],
        timeout: float,
        randomize: bool
    ) -> bool:
        """
        Recursive backtracking with dynamic variable ordering (MRV).

        Picks the unfilled slot with fewest (but >0) candidates. Skips slots
        with 0 candidates — they may become fillable after crossing slots are
        filled. Returns False only when ALL unfilled slots have 0 candidates.
        """
        self.iterations += 1

        if time.time() - self.start_time > timeout:
            return False

        # Dynamic MRV: find unfilled slot with fewest candidates (>0)
        best_slot = None
        best_candidates = None
        best_count = float('inf')
        has_unfilled = False
        has_zero_candidate = False

        for slot in slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            if '?' not in pattern:
                continue
            has_unfilled = True

            candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
            available = [(w, s) for w, s in candidates if w not in used_words]

            # Filter locked cell conflicts
            valid = []
            for w, s in available[:200]:  # Cap iteration for speed
                ok = True
                for i in range(len(w)):
                    if slot['direction'] == 'across':
                        pos = (slot['row'], slot['col'] + i)
                    else:
                        pos = (slot['row'] + i, slot['col'])
                    if pos in self.grid.locked_cells:
                        cell_val = self.grid.cells[pos]
                        if cell_val > 0 and chr(cell_val + ord('A') - 1) != w[i]:
                            ok = False
                            break
                if ok:
                    valid.append((w, s))

            if len(valid) == 0:
                has_zero_candidate = True
                continue  # Skip for now — may become fillable later

            if len(valid) < best_count:
                best_count = len(valid)
                best_slot = slot
                best_candidates = valid

        if not has_unfilled:
            return True  # All slots filled

        if best_slot is None:
            return False  # All remaining unfilled slots have 0 candidates

        slot = best_slot
        candidates = best_candidates

        # Prioritize theme words
        if self.theme_words:
            theme_cands = [(w, s + 50) for w, s in candidates if w in self.theme_words]
            non_theme = [(w, s) for w, s in candidates if w not in self.theme_words]
            candidates = theme_cands + non_theme

        # Limit candidates
        candidates = candidates[:150]

        if randomize and len(candidates) > 3:
            top_n = min(30, len(candidates))
            top = list(candidates[:top_n])
            random.shuffle(top)
            candidates = top + list(candidates[top_n:])

        # Report progress
        if self.progress_reporter and self.iterations % 500 == 0:
            filled = sum(1 for s in all_slots if '?' not in self.grid.get_pattern_for_slot(s))
            progress = min(90, 15 + int(70 * filled / len(all_slots)))
            self._emit_grid_snapshot(
                progress, f"Filling: {filled}/{len(all_slots)} slots ({self.iterations} steps)"
            )

        for word, score in candidates:
            saved_cells = {}
            for i in range(slot['length']):
                if slot['direction'] == 'across':
                    pos = (slot['row'], slot['col'] + i)
                else:
                    pos = (slot['row'] + i, slot['col'])
                saved_cells[pos] = self.grid.cells[pos]

            try:
                self.grid.place_word(word, slot['row'], slot['col'], slot['direction'])
            except ValueError:
                continue

            if self._forward_check(slot, all_slots, used_words | {word}):
                used_words.add(word)
                if self._csp_backtrack(
                    slots, 0, used_words, all_slots, timeout, randomize
                ):
                    return True
                used_words.discard(word)

            for pos, val in saved_cells.items():
                self.grid.cells[pos] = val

        return False

    def _forward_check(
        self,
        placed_slot: Dict,
        all_slots: List[Dict],
        used_words: set
    ) -> bool:
        """Check that all crossing slots still have at least one viable candidate."""
        placed_id = (placed_slot['row'], placed_slot['col'], placed_slot['direction'])
        perp_dir = 'down' if placed_slot['direction'] == 'across' else 'across'

        for other in all_slots:
            if other['direction'] != perp_dir:
                continue

            other_id = (other['row'], other['col'], other['direction'])
            cache_key = (placed_id, other_id)
            if cache_key not in self._intersection_cache:
                continue

            pattern = self.grid.get_pattern_for_slot(other)

            if '?' not in pattern:
                # Fully filled — must be valid word
                cands = self.pattern_matcher.find(pattern, min_score=self.min_score)
                if not any(w == pattern for w, s in cands):
                    return False
                continue

            # Partially filled — must have at least one available candidate
            filled_count = sum(1 for c in pattern if c != '?')
            if filled_count >= 2:
                cands = self.pattern_matcher.find(pattern, min_score=self.min_score)
                available = any(w not in used_words for w, s in cands)
                if not available:
                    return False

        return True

    def _slot_has_locked_cells(self, slot: Dict) -> bool:
        """Check if a slot contains any locked cells."""
        for i in range(slot['length']):
            if slot['direction'] == 'across':
                pos = (slot['row'], slot['col'] + i)
            else:
                pos = (slot['row'] + i, slot['col'])
            if pos in self.grid.locked_cells:
                return True
        return False

    def _build_result(self, all_slots: List[Dict], total_slots: int) -> 'FillResult':
        """Build FillResult from current grid state."""
        from .autofill import FillResult

        time_elapsed = time.time() - self.start_time
        filled_slots = sum(
            1 for slot in all_slots
            if '?' not in self.grid.get_pattern_for_slot(slot)
        )

        final_conflicts = self._find_conflicts(self.grid, all_slots)
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
                    'slot': slot_id, 'pattern': pattern, 'reason': 'unfilled'
                })
            elif slot_id in conflict_slot_ids:
                problematic_slots.append({
                    'slot': slot_id, 'pattern': pattern, 'reason': 'invalid_word'
                })

        success = filled_slots == total_slots and len(final_conflicts) == 0

        if self.progress_reporter:
            if success:
                self.progress_reporter.update(100, f"Complete! {filled_slots}/{total_slots} slots filled")
            else:
                self.progress_reporter.update(
                    90, f"Partial: {filled_slots}/{total_slots} slots, {len(problematic_slots)} problems"
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
            if self._is_valid_word(pattern):
                continue
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

                if self._is_valid_word(pattern):
                    continue

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

    def cleanup_grid(self) -> 'FillResult':
        """
        Remove invalid words from the grid while preserving letters that
        belong to valid crossing words.

        For each filled slot:
        1. Check if the word is valid (exists in any wordlist)
        2. If invalid, check each letter position:
           - If the crossing word at that position IS valid, keep the letter
           - Otherwise, clear it to empty
        3. Return a clean grid with only valid words + partial fills

        This is meant to be called AFTER fill() completes (or partially completes).
        """
        from .autofill import FillResult

        all_slots = self.grid.get_word_slots()
        total_slots = len(all_slots)

        # Build intersection cache if not already built
        if not hasattr(self, '_intersection_cache') or not self._intersection_cache:
            self._intersection_cache = {}
            for i, s1 in enumerate(all_slots):
                s1_id = (s1['row'], s1['col'], s1['direction'])
                for j in range(i + 1, len(all_slots)):
                    s2 = all_slots[j]
                    s2_id = (s2['row'], s2['col'], s2['direction'])
                    inter = self._get_intersection(s1, s2)
                    if inter is not None:
                        self._intersection_cache[(s1_id, s2_id)] = inter
                        self._intersection_cache[(s2_id, s1_id)] = (inter[1], inter[0])

        # Step 1: Identify valid and invalid words
        valid_slots = set()   # slot_ids with valid words
        invalid_slots = set() # slot_ids with invalid words

        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            slot_id = (slot['row'], slot['col'], slot['direction'])
            if '?' in pattern:
                continue  # Not fully filled, skip
            if self._is_valid_word(pattern):
                valid_slots.add(slot_id)
            else:
                invalid_slots.add(slot_id)

        if not invalid_slots:
            # Nothing to clean up
            if self.progress_reporter:
                self.progress_reporter.update(100, "Cleanup: all words valid")
            return self._build_cleanup_result(all_slots, total_slots, 0)

        if self.progress_reporter:
            self.progress_reporter.update(
                90, f"Cleanup: removing {len(invalid_slots)} invalid words"
            )

        # Step 2: For each invalid slot, clear letters NOT shared with valid crossings
        removed_count = 0
        for slot_id in invalid_slots:
            slot = self._get_slot_by_id(slot_id, all_slots)
            if not slot:
                continue

            removed_count += 1
            for i in range(slot['length']):
                if slot['direction'] == 'across':
                    pos = (slot['row'], slot['col'] + i)
                else:
                    pos = (slot['row'] + i, slot['col'])

                # Don't clear locked cells (theme words)
                if pos in self.grid.locked_cells:
                    continue

                # Check if this letter is part of a valid crossing word
                keep_letter = False
                for other_slot in all_slots:
                    if other_slot['direction'] == slot['direction']:
                        continue
                    other_id = (other_slot['row'], other_slot['col'], other_slot['direction'])
                    if other_id not in valid_slots:
                        continue
                    # Check if this position is in the crossing slot
                    for j in range(other_slot['length']):
                        if other_slot['direction'] == 'across':
                            other_pos = (other_slot['row'], other_slot['col'] + j)
                        else:
                            other_pos = (other_slot['row'] + j, other_slot['col'])
                        if other_pos == pos:
                            keep_letter = True
                            break
                    if keep_letter:
                        break

                if not keep_letter:
                    self.grid.cells[pos] = 0  # Clear to empty

        if self.progress_reporter:
            self._emit_grid_snapshot(
                100,
                f"Cleanup done: removed {removed_count} invalid words, "
                f"kept {len(valid_slots)} valid words",
                force=True
            )

        return self._build_cleanup_result(all_slots, total_slots, removed_count)

    def _build_cleanup_result(
        self, all_slots: List[Dict], total_slots: int, removed_count: int
    ) -> 'FillResult':
        """Build FillResult after cleanup pass."""
        from .autofill import FillResult

        filled_slots = sum(
            1 for slot in all_slots
            if '?' not in self.grid.get_pattern_for_slot(slot)
        )

        # After cleanup, remaining filled words should all be valid
        problematic_slots = []
        for slot in all_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            slot_id = (slot['row'], slot['col'], slot['direction'])
            if '?' in pattern and pattern != '?' * len(pattern):
                # Partially filled (leftover from cleanup)
                problematic_slots.append({
                    'slot': slot_id, 'pattern': pattern, 'reason': 'partial'
                })

        success = filled_slots == total_slots and len(problematic_slots) == 0

        return FillResult(
            success=success,
            grid=self.grid,
            time_elapsed=0.0,
            slots_filled=filled_slots,
            total_slots=total_slots,
            problematic_slots=problematic_slots,
            iterations=0
        )
