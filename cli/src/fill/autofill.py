"""
CSP-based autofill engine for crossword grids.

Uses backtracking with heuristics:
- MCV (Most Constrained Variable): Fill hardest slots first
- LCV (Least Constraining Value): Choose words that preserve options
- AC-3 (Arc Consistency): Maintain domain consistency efficiently
- Forward Checking: Eliminate impossible candidates early
"""

import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ..core.grid import Grid
from .pattern_matcher import PatternMatcher
from .pause_controller import PauseController, PausedException
from .state_manager import CSPState, StateManager
from .trie_pattern_matcher import TriePatternMatcher
from .word_list import WordList


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
    paused: bool = False
    state_path: Optional[str] = None
    adaptations_applied: int = 0
    message: Optional[str] = None


class Autofill:
    """
    Constraint satisfaction solver for crossword grids.

    Uses backtracking with intelligent heuristics to fill crossword grids
    efficiently while maintaining crossword quality.
    """

    def __init__(
        self,
        grid: Grid,
        word_list: WordList,
        pattern_matcher: PatternMatcher = None,
        timeout: int = 300,
        min_score: int = 0,
        algorithm: str = "trie",
        progress_reporter=None,
        pause_controller: Optional[PauseController] = None,
        state_manager: Optional[StateManager] = None,
    ):
        """
        Initialize autofill solver.

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine (created if not provided)
            timeout: Maximum seconds to spend filling
            min_score: Minimum word score to consider
            algorithm: Pattern matching algorithm - 'regex' (classic) or 'trie' (fast)
            progress_reporter: Optional ProgressReporter for progress updates
            pause_controller: Optional PauseController for pause/resume support
            state_manager: Optional StateManager for state serialization
        """
        self.grid = grid
        self.word_list = word_list
        self.algorithm = algorithm
        self.progress_reporter = progress_reporter
        self.pause_controller = pause_controller
        self.state_manager = state_manager or StateManager()
        self.paused_state_path = None  # Set by _handle_pause when a state is saved
        self.wordlist_paths: List[str] = []  # Original wordlist file paths (for resume)

        # Create pattern matcher if not provided
        if pattern_matcher is None:
            if algorithm == "trie":
                self.pattern_matcher = TriePatternMatcher(word_list)
            else:
                self.pattern_matcher = PatternMatcher(word_list)
        else:
            self.pattern_matcher = pattern_matcher

        self.timeout = timeout
        self.min_score = min_score

        self.start_time = 0.0
        self.iterations = 0
        self.used_words = set()
        self.random_seed = None
        self.on_backtrack = None

        # Domain tracking and constraint graph (initialized on fill())
        self.domains: Dict[int, Set[str]] = {}  # slot_id -> set of valid words
        self.constraints: Dict[int, List[Tuple[int, int, int]]] = {}  # slot_id -> [(other_slot, my_pos, other_pos)]
        self.slot_list: List[Dict] = []  # All slots
        self.slot_id_map: Dict[Tuple, int] = {}  # (row, col, direction) -> slot_id
        self.last_progress_report = 0  # Track last reported progress percentage
        self.slots_sorted: List[Dict] = []
        self.locked_slots: Set[int] = set()

        # Letter frequency table for fast LCV heuristic
        # Structure: {word_length: {position: {letter: frequency}}}
        self.letter_frequency_table: Dict[int, Dict[int, Dict[str, int]]] = {}
        self._build_letter_frequency_table()

    def fill(
        self,
        timeout: Optional[int] = None,
        interactive: bool = False,
        use_mac: bool = True,
        random_seed: int = None,
        resume_state: Optional[CSPState] = None,
        task_id: Optional[str] = None,
    ) -> FillResult:
        """
        Fill grid using backtracking CSP.

        Args:
            timeout: Time limit in seconds
            interactive: Unused, kept for interface compatibility
            use_mac: If True, use MAC (Maintaining Arc Consistency) for better pruning
            random_seed: If provided, shuffle candidates for restart diversity
            resume_state: If provided, resume from this saved state
            task_id: Unique task ID for pause/resume (required if pause_controller provided)

        Returns:
            FillResult with success status and filled grid
        """
        self.start_time = time.time()

        # Honor an explicit per-call timeout (overrides constructor value)
        if timeout is not None:
            self.timeout = timeout

        # Default the task id from the pause controller so callers that only
        # wired a controller (e.g. AdaptiveAutofill) can still pause safely
        if task_id is None and self.pause_controller is not None:
            task_id = self.pause_controller.task_id

        # Resume from saved state if provided
        if resume_state is not None:
            return self._resume_fill(resume_state, task_id, use_mac)

        # Normal fill from scratch
        self.iterations = 0
        self.used_words = set()
        self.random_seed = random_seed

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
                iterations=0,
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
                iterations=0,
            )

        # Sort slots by constraint (MCV heuristic)
        slots = self._sort_slots_by_constraint(slots)
        self.slots_sorted = slots  # Store for potential pause/resume

        # Try to fill using backtracking (with or without MAC)
        paused = False
        try:
            if use_mac:
                success = self._backtrack_with_mac(slots, 0, task_id)
            else:
                success = self._backtrack(slots, 0)  # Original algorithm
        except TimeoutError:
            success = False
        except PausedException:
            # Paused - state already saved in _handle_pause
            success = False
            paused = True

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
            iterations=self.iterations,
            paused=paused,
            state_path=str(self.paused_state_path) if paused and getattr(self, "paused_state_path", None) else None,
        )

    def _resume_fill(self, resume_state: CSPState, task_id: Optional[str], use_mac: bool = True) -> FillResult:
        """
        Resume fill from saved state.

        Restores the saved grid and word assignments, unwinds any assignments
        that make remaining slots unfillable (a pause can land mid-branch on a
        contradictory partial assignment — the recursion stack above the saved
        frame is not serialized, so a pure "continue at index N" search could
        never backtrack out of a doomed branch), then continues the search
        over the remaining empty slots with the filled cells as constraints.

        Args:
            resume_state: Saved CSP state
            task_id: Task ID for continuing pause/resume
            use_mac: Whether to use MAC algorithm

        Returns:
            FillResult
        """
        # Restore state into this instance (grid, used_words, iterations, ...)
        self.state_manager.restore_to_autofill(self, resume_state)

        # Resume timing (fresh timeout)
        self.start_time = time.time()

        # Report progress against the original slot count
        total_slots = len(resume_state.slot_list) or len(self.grid.get_empty_slots())

        # Convert locked slots list to set
        self.locked_slots = set(resume_state.locked_slots)

        # Unwind assignments that left some remaining slot with zero
        # candidates, then rebuild the CSP over the current empty slots
        self._unwind_dead_ends()

        # Search loop: if the restored partial assignment turns out to be
        # unsatisfiable (the search exhausts without a timeout), strip the
        # words crossing the most constrained slots and try again. Each round
        # removes at least one restored word, so this terminates; once all
        # restored words are stripped it degenerates to a fresh fill.
        paused = False
        success = False
        while True:
            slots = self.grid.get_empty_slots()
            if not slots:
                success = True
                break

            self._initialize_csp(slots)
            consistent = self._ac3()

            if consistent:
                slots = self._sort_slots_by_constraint(slots)
                self.slots_sorted = slots

                try:
                    if use_mac:
                        success = self._backtrack_with_mac(slots, 0, task_id)
                    else:
                        success = self._backtrack(slots, 0)
                except TimeoutError:
                    success = False
                    break
                except PausedException:
                    success = False
                    paused = True
                    break

                if success:
                    break

            # Out of time — report the partial result honestly
            if time.time() - self.start_time > self.timeout:
                break

            # UNSAT position: strip filled words crossing the tightest slots
            if not self._strip_words_around_constrained_slots():
                break  # Nothing strippable left — give up

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
            iterations=self.iterations,
            paused=paused,
            state_path=str(self.paused_state_path) if paused and getattr(self, "paused_state_path", None) else None,
        )

    def _unwind_dead_ends(self, max_rounds: int = 10) -> int:
        """
        Remove restored word assignments that make remaining slots unfillable.

        After restoring a paused state, some empty slots may have zero
        candidates because the search was paused inside a contradictory
        branch. This strips filled crossing words (never locked cells) around
        such dead-end slots so the resumed search has room to move.

        Args:
            max_rounds: Safety bound on strip-and-recheck rounds

        Returns:
            Number of words removed
        """
        removed_count = 0

        for _ in range(max_rounds):
            empty_slots = self.grid.get_empty_slots()
            if not empty_slots:
                break

            # Build the CSP over the current empty slots and run arc
            # consistency: if it passes, the position is searchable
            self._initialize_csp(empty_slots)
            if self._ac3():
                break

            # AC-3 wiped out at least one domain — those slots are dead
            dead_slots = [slot for idx, slot in enumerate(empty_slots) if len(self.domains.get(idx, set())) == 0]

            if not dead_slots:
                break

            # Strip filled words crossing each dead slot
            stripped_this_round = False
            for dead in dead_slots:
                for word_slot in self.grid.get_word_slots():
                    filled_word = self.grid.get_pattern_for_slot(word_slot)
                    if "?" in filled_word:
                        continue  # Not (fully) filled
                    if not self._slots_intersect(dead, word_slot):
                        continue
                    self.grid.remove_word(
                        word_slot["row"],
                        word_slot["col"],
                        word_slot["length"],
                        word_slot["direction"],
                    )
                    self.used_words.discard(filled_word)
                    removed_count += 1
                    stripped_this_round = True

            if not stripped_this_round:
                break  # Nothing left to strip (e.g. everything locked)

        return removed_count

    def _strip_words_around_constrained_slots(self, max_targets: int = 3) -> int:
        """
        Strip filled words crossing the most constrained empty slots.

        Used when a resumed search proves the restored partial assignment
        unsatisfiable: freeing the crossings of the tightest slots gives the
        next search round room to move.

        Args:
            max_targets: How many of the most constrained slots to free up

        Returns:
            Number of words removed
        """
        empty_slots = self.grid.get_empty_slots()
        if not empty_slots:
            return 0

        # Rank empty slots by candidate count (cheap: capped count)
        ranked = []
        for slot in empty_slots:
            pattern = self.grid.get_pattern_for_slot(slot)
            count = len(self.pattern_matcher.find(pattern, min_score=self.min_score, max_results=50))
            ranked.append((count, slot))
        ranked.sort(key=lambda x: x[0])

        removed = 0
        for _count, target in ranked[:max_targets]:
            for word_slot in self.grid.get_word_slots():
                filled_word = self.grid.get_pattern_for_slot(word_slot)
                if "?" in filled_word:
                    continue
                if not self._slots_intersect(target, word_slot):
                    continue
                self.grid.remove_word(
                    word_slot["row"],
                    word_slot["col"],
                    word_slot["length"],
                    word_slot["direction"],
                )
                self.used_words.discard(filled_word)
                removed += 1

        return removed

    def fill_with_restarts(
        self,
        attempts: int = 3,
        timeout_per_attempt: int = 100,
        interactive: bool = False,
        use_mac: bool = True,
        task_id: Optional[str] = None,
    ) -> FillResult:
        """
        Fill grid with randomized restart strategy.

        Tries multiple attempts with different random seeds, returns best result.

        Args:
            attempts: Number of restart attempts
            timeout_per_attempt: Timeout for each individual attempt (seconds)
            interactive: If True, prompt user before each placement
            use_mac: If True, use MAC algorithm

        Returns:
            Best FillResult across all attempts
        """
        best_result = None
        original_timeout = self.timeout
        original_grid_state = self.grid.to_dict()

        for attempt in range(attempts):
            # Reset grid to original state
            if attempt > 0:
                self.grid = Grid.from_dict(original_grid_state)

            # Set timeout for this attempt
            self.timeout = timeout_per_attempt

            # Use different random seed for each attempt
            random_seed = attempt + 1 if attempt > 0 else None  # First attempt: no shuffle

            # Try filling with this seed
            try:
                result = self.fill(
                    interactive=interactive,
                    use_mac=use_mac,
                    random_seed=random_seed,
                    task_id=task_id,
                )

                # Track best result
                if best_result is None or result.slots_filled > best_result.slots_filled:
                    best_result = result
                    # If perfect solution, stop early
                    if result.success:
                        break

                # Paused: stop restarting immediately, propagate the pause
                if result.paused:
                    best_result = result
                    break

            except TimeoutError:
                # Attempt timed out, continue to next
                continue

        # Restore original timeout
        self.timeout = original_timeout

        # Restore best grid state
        if best_result:
            self.grid = best_result.grid

        return (
            best_result
            if best_result
            else FillResult(
                success=False,
                grid=self.grid,
                time_elapsed=attempts * timeout_per_attempt,
                slots_filled=0,
                total_slots=len(self.grid.get_empty_slots()),
                problematic_slots=self.grid.get_empty_slots(),
                iterations=0,
            )
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
            key = (slot["row"], slot["col"], slot["direction"])
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
                max_results=None,
            )

            # Apply stratified sampling if domain too large
            if len(candidates) > 10000:
                self.domains[idx] = self._stratified_sample(candidates, target_size=5000)
            else:
                self.domains[idx] = {word for word, score in candidates}

    def _stratified_sample(self, candidates: List[Tuple[str, int]], target_size: int = 5000) -> Set[str]:
        """
        Sample domain ensuring letter diversity across score ranges.

        Strategy:
        1. Divide candidates into score deciles
        2. Sample proportionally from each decile
        3. Ensure all 26 letters represented at each position

        Args:
            candidates: List of (word, score) tuples
            target_size: Target domain size

        Returns:
            Set of sampled words with good letter coverage
        """
        if len(candidates) <= target_size:
            return {word for word, score in candidates}

        # Group by score deciles
        sorted_cands = sorted(candidates, key=lambda x: x[1], reverse=True)
        decile_size = max(1, len(sorted_cands) // 10)

        sampled = set()
        per_decile = target_size // 10

        # Sample from each decile
        for i in range(10):
            start = i * decile_size
            end = start + decile_size if i < 9 else len(sorted_cands)
            decile = sorted_cands[start:end]

            if decile:
                sample_size = min(per_decile, len(decile))
                sample = random.sample(decile, sample_size)
                sampled.update(word for word, score in sample)

        # Verify letter coverage at each position
        if candidates:
            pattern_length = len(candidates[0][0])
            for pos in range(pattern_length):
                letters_at_pos = {word[pos] for word in sampled if pos < len(word)}
                missing = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") - letters_at_pos

                # Add highest-scored word with each missing letter
                if missing:
                    for letter in missing:
                        matching = [w for w, s in candidates if len(w) > pos and w[pos] == letter]
                        if matching:
                            sampled.add(matching[0])

        return sampled

    def _build_letter_frequency_table(self) -> None:
        """
        Build letter frequency table for fast LCV heuristic.

        Analyzes the word list to count letter frequency at each position
        for each word length. Used for estimating constraint impact.

        Structure: {word_length: {position: {letter: count}}}

        Example:
            {3: {0: {'A': 1500, 'B': 200, ...}, 1: {...}, 2: {...}}, ...}
        """
        # Initialize table for word lengths 3-21 (standard crossword range)
        for length in range(3, 22):
            self.letter_frequency_table[length] = {}
            for pos in range(length):
                self.letter_frequency_table[length][pos] = {chr(ord("A") + i): 0 for i in range(26)}

        # Count letter frequencies from word list
        for word_obj in self.word_list.words:
            word = word_obj.text.upper()
            length = len(word)

            # Skip if not in valid range
            if length < 3 or length > 21:
                continue

            # Count each letter at each position
            for pos, letter in enumerate(word):
                if letter.isalpha() and letter in self.letter_frequency_table[length][pos]:
                    self.letter_frequency_table[length][pos][letter] += 1

    def _lcv_score_fast(self, word: str, slot: Dict) -> float:
        """
        Fast LCV scoring using letter frequency heuristic.

        Estimates how constraining a word is by summing letter frequencies
        at crossing positions. Higher score = less constraining.

        Args:
            word: Candidate word to score
            slot: Slot to place word in

        Returns:
            LCV score (higher = less constraining, prefer this word)
        """
        score = 0.0
        word = word.upper()

        # Find slot ID for this slot
        slot_key = (slot["row"], slot["col"], slot["direction"])
        slot_id = self.slot_id_map.get(slot_key)

        if slot_id is None:
            # Slot not in constraint graph, return neutral score
            return 1000.0

        # Get all crossing constraints for this slot
        crossing_constraints = self.constraints.get(slot_id, [])

        for other_slot_id, my_pos, other_pos in crossing_constraints:
            # Get the crossing slot
            other_slot = self.slot_list[other_slot_id]
            other_length = other_slot["length"]

            # Get the letter at crossing position
            if my_pos >= len(word):
                continue  # Safety check

            crossing_letter = word[my_pos]

            # Look up frequency of this letter at other slot's position
            if other_length in self.letter_frequency_table:
                if other_pos in self.letter_frequency_table[other_length]:
                    frequency = self.letter_frequency_table[other_length][other_pos].get(crossing_letter, 0)
                    score += frequency

        # Normalize by number of crossings (or return 0 if no crossings)
        if len(crossing_constraints) > 0:
            score = score / len(crossing_constraints)
        else:
            score = 1000.0  # No crossings = not constraining

        return score

    def _lcv_score_accurate(self, word: str, slot: Dict) -> float:
        """
        Accurate LCV scoring via domain counting.

        Computes exact count of valid words for crossing slots after
        placing this candidate. More accurate but slower than fast heuristic.

        Args:
            word: Candidate word to score
            slot: Slot to place word in

        Returns:
            LCV score (higher = less constraining, prefer this word)
        """
        score = 0.0
        word = word.upper()

        # Find slot ID for this slot
        slot_key = (slot["row"], slot["col"], slot["direction"])
        slot_id = self.slot_id_map.get(slot_key)

        if slot_id is None:
            return 10000.0  # Neutral score

        # Get all crossing constraints
        crossing_constraints = self.constraints.get(slot_id, [])

        if len(crossing_constraints) == 0:
            return 10000.0  # No crossings = not constraining

        # For each crossing slot, count valid words after placing candidate
        for other_slot_id, my_pos, other_pos in crossing_constraints:
            other_slot = self.slot_list[other_slot_id]

            # Get current pattern for crossing slot
            current_pattern = self.grid.get_pattern_for_slot(other_slot)

            # Compute new pattern after placing our word
            if my_pos >= len(word) or other_pos >= len(current_pattern):
                continue  # Safety check

            crossing_letter = word[my_pos]
            new_pattern = list(current_pattern)
            new_pattern[other_pos] = crossing_letter
            new_pattern_str = "".join(new_pattern)

            # Count how many words match the new pattern
            matching_words = self.pattern_matcher.find(
                new_pattern_str,
                min_score=self.min_score,
                max_results=None,  # Count all matches
            )

            # Add count to score (more matches = less constraining)
            score += len(matching_words)

        # Average across crossings
        score = score / len(crossing_constraints)

        return score

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
        if slot1["direction"] == slot2["direction"]:
            return None

        # Determine across and down
        if slot1["direction"] == "across":
            across, down = slot1, slot2
        else:
            across, down = slot2, slot1

        # Check intersection
        across_row = across["row"]
        across_col_start = across["col"]
        across_col_end = across_col_start + across["length"]

        down_row_start = down["row"]
        down_row_end = down_row_start + down["length"]
        down_col = down["col"]

        # Does down column intersect across range?
        if across_col_start <= down_col < across_col_end:
            # Does across row intersect down range?
            if down_row_start <= across_row < down_row_end:
                # They intersect!
                if slot1["direction"] == "across":
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

    def _ac3_incremental(self, assigned_slot_id: int) -> bool:
        """
        Run AC-3 starting from a newly assigned slot (MAC).

        More efficient than full AC-3: only propagates constraints
        from the assigned slot outward.

        Args:
            assigned_slot_id: Slot that was just filled

        Returns:
            True if consistent, False if any domain becomes empty
        """
        # Initialize queue with arcs FROM assigned slot
        queue = deque()
        for other_id, pos1, pos2 in self.constraints.get(assigned_slot_id, []):
            queue.append((other_id, assigned_slot_id, pos2, pos1))

        # Standard AC-3 loop
        while queue:
            slot_id, other_id, pos1, pos2 = queue.popleft()

            if self._revise(slot_id, other_id, pos1, pos2):
                if len(self.domains[slot_id]) == 0:
                    return False  # Domain wipeout

                # Add affected arcs
                for neighbor_id, my_pos, neighbor_pos in self.constraints[slot_id]:
                    if neighbor_id != other_id:
                        queue.append((neighbor_id, slot_id, neighbor_pos, my_pos))

        return True

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

        # Report progress (every 5% to avoid flooding)
        if self.progress_reporter and len(slots) > 0:
            current_progress = int((current_index / len(slots)) * 100)
            if current_progress - self.last_progress_report >= 5:
                self.last_progress_report = current_progress
                filled_slots = sum(1 for s in slots[:current_index] if "?" not in self.grid.get_pattern_for_slot(s))
                self.progress_reporter.update(
                    current_progress,
                    f"Filling slots: {filled_slots}/{len(slots)} filled",
                    "running",
                    {"grid": self.grid.to_dict()["grid"]},
                )

        # Base case: all slots filled
        if current_index >= len(slots):
            return True

        # Get current slot
        slot = slots[current_index]

        # Skip if already filled
        pattern = self.grid.get_pattern_for_slot(slot)
        if "?" not in pattern:
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
            self.grid.place_word(word, slot["row"], slot["col"], slot["direction"])
            self.used_words.add(word)

            # Forward check
            if self._forward_check(slot):
                # Send incremental grid update
                if self.progress_reporter:
                    filled_count = sum(1 for s in slots if "?" not in self.grid.get_pattern_for_slot(s))
                    self.progress_reporter.update(
                        min(95, int((filled_count / len(slots)) * 100)),
                        f"Filling slots: {filled_count}/{len(slots)} filled",
                        "running",
                        {"grid": self.grid.to_dict()["grid"]},  # Send current grid state
                    )

                # Recurse
                if self._backtrack(slots, current_index + 1):
                    return True  # Success!

            # Backtrack
            self.grid.remove_word(slot["row"], slot["col"], slot["length"], slot["direction"])
            self.used_words.remove(word)

            if self.on_backtrack:
                slot_key = f"{slot['row']},{slot['col']},{slot['direction']}"
                self.on_backtrack(slot_key)

        # No candidate worked
        return False

    def _backtrack_with_mac(self, slots: List[Dict], current_index: int, task_id: Optional[str] = None) -> bool:
        """
        Backtracking with MAC (Maintaining Arc Consistency).

        Runs incremental AC-3 after each assignment to detect failures early.

        Args:
            slots: List of slots to fill (sorted by constraint)
            current_index: Current position in slots list
            task_id: Task ID for pause/resume support

        Returns:
            True if successfully filled, False if no solution

        Raises:
            TimeoutError: If timeout exceeded
            PausedException: If pause requested
        """
        self.iterations += 1

        # Check timeout every iteration (a time.time() call is cheap and slow
        # grids may only manage a few iterations per second, so a 100-iteration
        # granularity used to overrun the budget by tens of seconds)
        if time.time() - self.start_time > self.timeout:
            raise TimeoutError("Autofill timeout")

        # Check pause signal every 20 iterations (file stat is cheap but not free)
        if self.iterations % 20 == 0:
            if self.pause_controller and self.pause_controller.should_pause():
                self._handle_pause(current_index, task_id, len(slots))
                raise PausedException("Autofill paused by user")

        # Report progress
        if self.progress_reporter and len(slots) > 0:
            current_progress = int((current_index / len(slots)) * 100)
            if current_progress - self.last_progress_report >= 5:
                self.last_progress_report = current_progress
                filled_slots = sum(1 for s in slots[:current_index] if "?" not in self.grid.get_pattern_for_slot(s))
                self.progress_reporter.update(
                    current_progress,
                    f"Filling slots (MAC): {filled_slots}/{len(slots)} filled",
                    "running",
                    {"grid": self.grid.to_dict()["grid"]},
                )

        # Base case: all slots filled
        if current_index >= len(slots):
            return True

        # Get current slot
        slot = slots[current_index]

        # Skip if already filled
        pattern = self.grid.get_pattern_for_slot(slot)
        if "?" not in pattern:
            return self._backtrack_with_mac(slots, current_index + 1, task_id)

        # Get candidate words
        candidates = self._get_candidates(slot)

        if not candidates:
            return False

        # Apply LCV (Least Constraining Value) heuristic
        # Hybrid approach: Fast filtering + accurate ranking for top candidates
        if len(candidates) > 100:
            # Many candidates: Use fast LCV heuristic for initial filtering
            candidates_with_lcv = []
            for word, word_score in candidates:
                lcv_score = self._lcv_score_fast(word, slot)
                candidates_with_lcv.append((word, word_score, lcv_score))

            # Sort by LCV (descending), then word score (descending)
            candidates_with_lcv.sort(key=lambda x: (x[2], x[1]), reverse=True)

            # Take top 100 candidates
            top_candidates = candidates_with_lcv[:100]

            # Refine with accurate LCV for these top 100
            refined_candidates = []
            for word, word_score, fast_lcv in top_candidates:
                accurate_lcv = self._lcv_score_accurate(word, slot)
                refined_candidates.append((word, word_score, accurate_lcv))

            # Final sort by accurate LCV
            refined_candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
            candidates = [(word, score) for word, score, _ in refined_candidates]

        else:
            # Few candidates: Use accurate LCV directly
            candidates_with_lcv = []
            for word, word_score in candidates:
                lcv_score = self._lcv_score_accurate(word, slot)
                candidates_with_lcv.append((word, word_score, lcv_score))

            # Sort by LCV (descending), then word score (descending)
            candidates_with_lcv.sort(key=lambda x: (x[2], x[1]), reverse=True)
            candidates = [(word, score) for word, score, _ in candidates_with_lcv]

        # Randomized restart - shuffle candidates if seed provided
        if self.random_seed is not None:
            rng = random.Random(self.random_seed + current_index)  # Unique seed per slot
            rng.shuffle(candidates)

        # Try each candidate (now sorted by LCV - least constraining first, or shuffled)
        for word, score in candidates:
            if word in self.used_words:
                continue

            # Place word
            self.grid.place_word(word, slot["row"], slot["col"], slot["direction"])
            self.used_words.add(word)

            # Save domains (for backtracking)
            saved_domains = {k: v.copy() for k, v in self.domains.items()}

            # Run incremental AC-3 from this slot (KEY MAC STEP!)
            slot_id = self.slot_id_map.get((slot["row"], slot["col"], slot["direction"]))

            if slot_id is not None and self._ac3_incremental(slot_id):
                # AC-3 succeeded, send progress update
                if self.progress_reporter:
                    filled_count = sum(1 for s in slots if "?" not in self.grid.get_pattern_for_slot(s))
                    self.progress_reporter.update(
                        min(95, int((filled_count / len(slots)) * 100)),
                        f"Filling slots (MAC): {filled_count}/{len(slots)} filled",
                        "running",
                        {"grid": self.grid.to_dict()["grid"]},
                    )

                # Recurse
                if self._backtrack_with_mac(slots, current_index + 1, task_id):
                    return True

            # Backtrack: restore domains and remove word
            self.domains = saved_domains
            self.grid.remove_word(slot["row"], slot["col"], slot["length"], slot["direction"])
            self.used_words.remove(word)

            if self.on_backtrack:
                slot_key = f"{slot['row']},{slot['col']},{slot['direction']}"
                self.on_backtrack(slot_key)

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
            key = (slot["row"], slot["col"], slot["direction"])
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
            empty_count = pattern.count("?")

            # Prefer slots with fewer candidate words and more letters filled
            # Negative length for tie-breaking (prefer longer words)
            return (domain_size, empty_count, -slot["length"])

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
        candidates = self.pattern_matcher.find(pattern, min_score=self.min_score, max_results=1000)

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
        key = (slot["row"], slot["col"], slot["direction"])
        slot_id = self.slot_id_map.get(key)

        if slot_id is None:
            # Slot not in our tracking, fall back to basic check
            return True

        # Check each constrained slot
        for other_id, pos1, pos2 in self.constraints[slot_id]:
            # Check if any word in the domain is still valid
            pattern = self.grid.get_pattern_for_slot(self.slot_list[other_id])

            # Skip if fully filled
            if "?" not in pattern:
                continue

            # Check if domain has compatible words
            has_valid = False
            for word in self.domains[other_id]:
                if word in self.used_words:
                    continue
                # Quick pattern match
                matches = all(pattern[i] == "?" or pattern[i] == word[i] for i in range(len(pattern)))
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

        row, col = slot["row"], slot["col"]
        slot["length"]
        direction = slot["direction"]

        for other_slot in all_slots:
            # Skip same slot
            if other_slot["row"] == row and other_slot["col"] == col and other_slot["direction"] == direction:
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
        if slot1["direction"] == slot2["direction"]:
            return False

        # Determine which is across and which is down
        if slot1["direction"] == "across":
            across, down = slot1, slot2
        else:
            across, down = slot2, slot1

        # Check if they intersect
        # Across slot spans columns [across_col, across_col + across_len)
        # Down slot spans rows [down_row, down_row + down_len)
        # They intersect if down column is in across range AND across row is in down range

        across_row = across["row"]
        across_col_start = across["col"]
        across_col_end = across_col_start + across["length"]

        down_row_start = down["row"]
        down_row_end = down_row_start + down["length"]
        down_col = down["col"]

        # Check intersection
        if across_col_start <= down_col < across_col_end and down_row_start <= across_row < down_row_end:
            return True

        return False

    def _handle_pause(self, current_index: int, task_id: Optional[str], total_slots: int) -> None:
        """
        Handle pause request by saving current state.

        Args:
            current_index: Current backtracking position
            task_id: Task ID for state file naming
            total_slots: Total number of slots

        Raises:
            ValueError: If task_id not provided when needed
        """
        if not task_id:
            raise ValueError("task_id required for pause/resume")

        # Capture current state (positional args: signature is
        # capture_csp_state(autofill_instance, current_slot_index, locked_slots))
        csp_state = self.state_manager.capture_csp_state(self, current_index, self.locked_slots)

        # Calculate current stats
        remaining_slots = self.grid.get_empty_slots()
        slots_filled = total_slots - len(remaining_slots)

        # Save state with metadata (wordlist paths are recorded so `resume`
        # can reload the same wordlists without requiring -w)
        metadata = {
            "min_score": self.min_score,
            "timeout": self.timeout,
            "algorithm": self.algorithm,
            "grid_size": [self.grid.size, self.grid.size],
            "total_slots": total_slots,
            "slots_filled": slots_filled,
            "time_elapsed": time.time() - self.start_time,
            "wordlists": list(getattr(self, "wordlist_paths", []) or []),
        }

        state_path = self.state_manager.save_csp_state(task_id=task_id, csp_state=csp_state, metadata=metadata, compress=True)
        self.paused_state_path = state_path

        # The pause request has been consumed — remove the flag file so it
        # cannot accidentally pause a future run with the same task id.
        if self.pause_controller:
            self.pause_controller.clear_pause()

        # Report pause via progress reporter
        if self.progress_reporter:
            self.progress_reporter.update(
                int((slots_filled / total_slots) * 100),
                f"Paused: {slots_filled}/{total_slots} slots filled",
                "paused",
                {"state_path": str(state_path), "grid": self.grid.to_dict()["grid"]},
            )

    def __repr__(self) -> str:
        """String representation."""
        return f"Autofill(grid={self.grid.size}x{self.grid.size}, words={len(self.word_list)})"
