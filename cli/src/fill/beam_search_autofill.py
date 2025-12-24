"""
Beam search autofill engine for crossword grids.

Maintains multiple parallel solutions (beam) to explore diverse search paths
and avoid local optima that plague single-path backtracking approaches.
"""

from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass, field
import time
from ..core.grid import Grid
from .word_list import WordList
from .pattern_matcher import PatternMatcher


@dataclass
class BeamState:
    """
    Represents one partial solution in the beam.

    Immutable snapshot of a crossword solution state with metadata for scoring.

    Invariants:
    - 0 ≤ slots_filled ≤ total_slots
    - length(used_words) == slots_filled
    - 0.0 ≤ score ≤ 100.0
    - All words in used_words exist in grid
    """

    grid: Grid                                          # Current grid state
    slots_filled: int                                   # Number of slots filled so far
    total_slots: int                                    # Total slots in grid
    score: float                                        # Quality score (0.0-100.0)
    used_words: Set[str] = field(default_factory=set)  # Words placed (prevent duplicates)
    slot_assignments: Dict[Tuple[int, int, str], str] = field(default_factory=dict)  # slot → word

    def completion_rate(self) -> float:
        """Return fraction of slots filled (0.0-1.0)"""
        return self.slots_filled / self.total_slots if self.total_slots > 0 else 0.0

    def clone(self) -> 'BeamState':
        """
        Create deep copy of this state.

        Postconditions:
        - Returned state is independent (modifications don't affect original)
        - Grid is cloned (not reference)
        - used_words is copied (not reference)
        """
        return BeamState(
            grid=self.grid.clone(),  # CRITICAL: deep copy
            slots_filled=self.slots_filled,
            total_slots=self.total_slots,
            score=self.score,
            used_words=self.used_words.copy(),  # CRITICAL: copy set
            slot_assignments=self.slot_assignments.copy()
        )

    def __eq__(self, other: 'BeamState') -> bool:
        """
        Check equality (for testing).

        Two states are equal if they have same grid contents and used words.
        """
        if not isinstance(other, BeamState):
            return False
        return (
            self.grid.to_dict() == other.grid.to_dict() and
            self.used_words == other.used_words
        )

    def __hash__(self) -> int:
        """
        Hash for set/dict storage (for testing).

        WARNING: Expensive operation, use sparingly.
        """
        grid_dict = self.grid.to_dict()
        return hash((
            tuple(tuple(row) for row in grid_dict['grid']),
            frozenset(self.used_words)
        ))


class BeamSearchAutofill:
    """
    Beam search solver for crossword grids.

    Maintains beam_width parallel partial solutions and extends them
    greedily without backtracking. Natural diversity prevents getting
    stuck in local optima.

    Algorithm:
    1. Initialize beam with beam_width empty grids
    2. For each slot (in MRV order):
        a. Expand: Try top-K words in each beam state
        b. Prune: Keep only top beam_width states
        c. Check: Stop if any state is complete
    3. Return best state (most slots filled)
    """

    def __init__(
        self,
        grid: Grid,
        word_list: WordList,
        pattern_matcher: PatternMatcher,
        beam_width: int = 5,
        candidates_per_slot: int = 10,
        min_score: int = 0,
        diversity_bonus: float = 0.1,
        progress_reporter=None
    ):
        """
        Initialize beam search solver.

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine (trie or regex)
            beam_width: Number of parallel solutions (default: 5)
            candidates_per_slot: Top-K words to try per slot (default: 10)
            min_score: Minimum word quality score (default: 0)
            diversity_bonus: Bonus for diverse beams 0.0-1.0 (default: 0.1)
            progress_reporter: Optional progress reporting

        Raises:
            ValueError: If parameters out of valid ranges
        """
        # Validate parameters
        if beam_width < 1 or beam_width > 20:
            raise ValueError(f"beam_width must be 1-20, got {beam_width}")
        if candidates_per_slot < 1 or candidates_per_slot > 100:
            raise ValueError(f"candidates_per_slot must be 1-100, got {candidates_per_slot}")
        if min_score < 0 or min_score > 100:
            raise ValueError(f"min_score must be 0-100, got {min_score}")
        if diversity_bonus < 0.0 or diversity_bonus > 1.0:
            raise ValueError(f"diversity_bonus must be 0.0-1.0, got {diversity_bonus}")

        self.grid = grid
        self.word_list = word_list
        self.pattern_matcher = pattern_matcher
        self.beam_width = beam_width
        self.candidates_per_slot = candidates_per_slot
        self.min_score = min_score
        self.diversity_bonus = diversity_bonus
        self.progress_reporter = progress_reporter

        # State tracking
        self.start_time = 0.0
        self.iterations = 0

    def fill(self, timeout: int = 300) -> 'FillResult':
        """
        Fill grid using beam search.

        Algorithm:
        1. Initialize beam with beam_width empty grids
        2. For each slot (in MRV order):
            a. Expand: Try top-K words in each beam state
            b. Prune: Keep only top beam_width states
            c. Check: Stop if any state is complete
        3. Return best state (most slots filled)

        Args:
            timeout: Maximum seconds to spend

        Returns:
            FillResult with best solution found (may be partial)

        Raises:
            ValueError: If timeout < 10 seconds
        """
        from .autofill import FillResult  # Import here to avoid circular dependency

        if timeout < 10:
            raise ValueError(f"timeout must be ≥10 seconds, got {timeout}")

        self.start_time = time.time()
        self.iterations = 0

        # Get all empty slots
        all_slots = self.grid.get_empty_slots()
        total_slots = len(all_slots)

        # Early exit if already complete
        if total_slots == 0:
            return FillResult(
                success=True,
                grid=self.grid,
                time_elapsed=0.0,
                slots_filled=0,
                total_slots=0,
                problematic_slots=[],
                iterations=0
            )

        # Sort slots by constraint level (length-first, then MRV)
        # CRITICAL: Longest slots filled first to ensure high-quality words
        sorted_slots = self._sort_slots_by_constraint(all_slots)

        # Initialize beam with beam_width copies of initial state
        initial_state = BeamState(
            grid=self.grid.clone(),
            slots_filled=0,
            total_slots=total_slots,
            score=0.0,
            used_words=set(),
            slot_assignments={}
        )
        beam = [initial_state.clone() for _ in range(self.beam_width)]

        # DEBUG: Print first 5 slots to verify length-first sorting
        print("\nDEBUG: First 5 slots (should be longest first):")
        for i, slot in enumerate(sorted_slots[:5]):
            print(f"  Slot {i+1}: length={slot['length']}, pos=({slot['row']},{slot['col']}), dir={slot['direction']}")

        # Main beam search loop
        for slot_idx, slot in enumerate(sorted_slots):
            self.iterations += 1

            # Check timeout
            elapsed = time.time() - self.start_time
            if elapsed > timeout:
                break

            # DEBUG: Print what's being filled (first 3 slots only to avoid spam)
            if slot_idx < 3:
                print(f"\nDEBUG: Filling slot {slot_idx+1}/{total_slots}: length={slot['length']}, pos=({slot['row']},{slot['col']}), dir={slot['direction']}")

            # Report progress
            if self.progress_reporter:
                progress = int((slot_idx / total_slots) * 90) + 10  # 10-100%
                self.progress_reporter.update(
                    progress,
                    f"Beam search: slot {slot_idx + 1}/{total_slots}"
                )

            # Expand beam
            expanded_beam = self._expand_beam(beam, slot, self.candidates_per_slot)

            # BACKTRACKING: If expansion fails, try with more candidates
            if not expanded_beam and slot_idx > 0:
                print(f"\nDEBUG: Beam expansion failed at slot {slot_idx+1}. Trying backtracking...")

                # Try expanding with 2x more candidates
                expanded_beam = self._expand_beam(beam, slot, self.candidates_per_slot * 2)

                # If still failing, try 5x more candidates
                if not expanded_beam:
                    print(f"  Retry with 5x candidates...")
                    expanded_beam = self._expand_beam(beam, slot, self.candidates_per_slot * 5)

                # If still failing, try with NO score filter (min_score=0 temporarily)
                if not expanded_beam:
                    print(f"  Retry with min_score=0...")
                    old_min_score = self.min_score
                    self.min_score = 0
                    expanded_beam = self._expand_beam(beam, slot, self.candidates_per_slot * 10)
                    self.min_score = old_min_score

            # Final fallback: exit if truly no options
            if not expanded_beam:
                print(f"\nDEBUG: Beam expansion returned empty at slot {slot_idx+1} even after backtracking! Exiting early.")
                break

            # Apply diversity bonus
            if self.diversity_bonus > 0:
                expanded_beam = self._apply_diversity_bonus(expanded_beam)

            # Prune beam
            beam = self._prune_beam(expanded_beam, self.beam_width)

            # Check for complete solution
            complete_states = [s for s in beam if s.slots_filled == total_slots]
            if complete_states:
                print(f"\nDEBUG: Found complete solution at slot {slot_idx+1}!")
                best_complete = max(complete_states, key=lambda s: s.score)
                time_elapsed = time.time() - self.start_time

                return FillResult(
                    success=True,
                    grid=best_complete.grid,
                    time_elapsed=time_elapsed,
                    slots_filled=best_complete.slots_filled,
                    total_slots=total_slots,
                    problematic_slots=[],
                    iterations=self.iterations
                )

        # Return best partial solution
        best_state = max(beam, key=lambda s: (s.slots_filled, s.score))
        time_elapsed = time.time() - self.start_time

        # Find problematic slots (unfilled)
        problematic_slots = []
        for slot in all_slots:
            slot_id = (slot['row'], slot['col'], slot['direction'])
            if slot_id not in best_state.slot_assignments:
                problematic_slots.append(slot)

        return FillResult(
            success=False,
            grid=best_state.grid,
            time_elapsed=time_elapsed,
            slots_filled=best_state.slots_filled,
            total_slots=total_slots,
            problematic_slots=problematic_slots,
            iterations=self.iterations
        )

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

    def _is_quality_word(self, word: str) -> bool:
        """
        Check if word is likely real (not gibberish).

        Uses linguistic heuristics to filter obvious gibberish:
        1. Vowel ratio (~40% in English)
        2. No excessive letter repetition
        3. No excessive consonant clusters
        4. Q followed by U (standard pattern)

        Args:
            word: Word to check (uppercase)

        Returns:
            True if word passes quality checks, False if likely gibberish

        Rationale:
            Prevents patterns like QZXRTPL, AAAAAN, NNRRRN from appearing
            in filled grids. Conservative heuristics to avoid false positives.
        """
        word = word.upper()
        length = len(word)

        # Heuristic 1: Vowel ratio (English typically 35-45%)
        vowels = sum(1 for c in word if c in 'AEIOUY')
        vowel_ratio = vowels / length if length > 0 else 0

        # Too consonant-heavy or vowel-heavy is suspicious
        if vowel_ratio < 0.20 or vowel_ratio > 0.65:
            return False

        # Heuristic 2: Repeated letters
        # "AAA" might be OK, "AAAA" is very suspicious
        import itertools
        max_repeats = max((len(list(g)) for k, g in itertools.groupby(word)), default=1)
        if max_repeats > 3:
            return False

        # Heuristic 3: Consonant clusters
        # English rarely has 5+ consonants in a row (e.g., "QZXRTPL")
        consonants = 'BCDFGHJKLMNPQRSTVWXZ'
        consonant_run = 0
        max_consonant_run = 0

        for c in word:
            if c in consonants:
                consonant_run += 1
                max_consonant_run = max(max_consonant_run, consonant_run)
            else:
                consonant_run = 0

        if max_consonant_run > 5:
            return False

        # Heuristic 4: Q not followed by U (rare in English)
        if 'Q' in word and length > 6:  # Stricter for long words
            q_index = word.index('Q')
            if q_index + 1 < len(word) and word[q_index + 1] != 'U':
                # QI, QAT are valid short words, but QZXR... is not
                return False

        return True

    def _expand_beam(
        self,
        beam: List[BeamState],
        slot: Dict,
        candidates_per_slot: int
    ) -> List[BeamState]:
        """
        Expand beam by trying top-K candidates in each state.

        Args:
            beam: Current beam (list of states)
            slot: Slot to fill next
            candidates_per_slot: How many words to try per state

        Returns:
            Expanded beam (potentially beam_width × candidates_per_slot states)

        Complexity: O(beam_width × candidates_per_slot × pattern_match_time)
        """
        expanded = []

        # DEBUG: Track why expansion might fail
        total_skipped_duplicate = 0
        total_skipped_viability = 0
        total_added = 0

        # DIVERSITY STRATEGY: Stratified candidate selection with overlapping slices
        # Prevents beam collapse by ensuring each beam explores different combinations
        # while maintaining access to high-quality candidates
        #
        # Example with offset=2, candidates_per_slot=10:
        #   Beam 0: candidates[0:10]   = ALASKARANGE, ALMOSTTHERE, ALMOSTNEVER, ...
        #   Beam 1: candidates[2:12]   = ALMOSTNEVER, ALLTOGETHER, APPLICATION, ...
        #   Beam 2: candidates[4:14]   = APPLICATION, APPROPRIATE, ALTERNATIVES, ...
        #   → Overlapping ensures quality, offset ensures diversity
        offset_per_beam = 2  # Tunable: increase for more diversity, decrease for more quality overlap

        for beam_idx, state in enumerate(beam):
            # Get pattern for this slot in current state
            pattern = state.grid.get_pattern_for_slot(slot)

            # Skip if already filled
            if '?' not in pattern:
                expanded.append(state)
                continue

            # Get ALL candidate words
            all_candidates = self.pattern_matcher.find(
                pattern,
                min_score=self.min_score
            )

            if len(all_candidates) == 0:
                # No candidates: this beam state is dead
                continue

            # (Debug output removed for performance)

            # QUALITY FILTER: For long slots, reject likely gibberish
            if slot['length'] >= 7:
                quality_candidates = [
                    (word, score) for word, score in all_candidates
                    if self._is_quality_word(word)
                ]

                # Safety valve: only use quality filter if enough candidates remain
                if len(quality_candidates) >= 5:
                    all_candidates = quality_candidates

            # SHUFFLE WITHIN SCORE TIERS: Break alphabetical bias while preserving quality
            # Problem: Candidates are sorted by score, then alphabetically within same score
            # Solution: Shuffle within each score group to get diverse letters at same quality level
            from collections import defaultdict
            import random

            # Group by score
            by_score = defaultdict(list)
            for word, score in all_candidates:
                by_score[score].append((word, score))

            # Shuffle within each score group (deterministic seed)
            slot_seed = slot['row'] * 100 + slot['col'] * 10 + (1 if slot['direction'] == 'across' else 0)
            for score in by_score:
                random.Random(slot_seed + score).shuffle(by_score[score])

            # Flatten back: high scores first, but shuffled within each score
            shuffled_candidates = []
            for score in sorted(by_score.keys(), reverse=True):
                shuffled_candidates.extend(by_score[score])

            # Now use shuffled candidates for stratified beam sampling
            all_candidates = shuffled_candidates

            # (Verbose debug output removed)

            # STRATIFIED SAMPLING: Each beam gets overlapping slice from shuffled candidates
            # With 48k+ shuffled candidates, overlapping slices give diversity + coherence
            offset = beam_idx * offset_per_beam
            start_idx = offset
            end_idx = offset + candidates_per_slot
            candidates = all_candidates[start_idx:end_idx]

            # Fallback: If offset exceeds available candidates, wrap around
            if len(candidates) < candidates_per_slot and len(all_candidates) >= candidates_per_slot:
                candidates = all_candidates[:candidates_per_slot]

            # Try each candidate
            for word, word_score in candidates:
                # Skip if word already used
                if word in state.used_words:
                    total_skipped_duplicate += 1
                    continue

                # Create new state
                new_state = state.clone()

                # Place word
                new_state.grid.place_word(
                    word,
                    slot['row'],
                    slot['col'],
                    slot['direction']
                )

                # Update metadata
                new_state.slots_filled += 1
                new_state.used_words.add(word)
                slot_id = (slot['row'], slot['col'], slot['direction'])
                new_state.slot_assignments[slot_id] = word

                # Compute score
                new_state.score = self._compute_score(new_state, word_score)

                # Check viability (no dead ends)
                # Pass the slot we just filled so viability check only examines intersecting slots
                if self._is_viable_state(new_state, slot):
                    expanded.append(new_state)
                    total_added += 1
                else:
                    total_skipped_viability += 1

        # DEBUG: Show why expansion might have failed
        if not expanded:
            print(f"\nDEBUG: Expansion failed!")
            print(f"  Skipped (duplicate): {total_skipped_duplicate}")
            print(f"  Skipped (viability): {total_skipped_viability}")
            print(f"  Added: {total_added}")

        return expanded

    def _prune_beam(
        self,
        beam: List[BeamState],
        beam_width: int
    ) -> List[BeamState]:
        """
        Prune beam to keep only top-K DIVERSE states.

        CRITICAL FIX: Explicitly remove duplicate states to prevent beam collapse.
        Two states are "duplicate" if they have same words in same slots.

        Process:
        1. Remove exact duplicates (same slot assignments)
        2. Sort by score (descending)
        3. Greedily select: pick best, then pick next that differs by ≥1 word
        4. Fill remaining slots with best available

        Args:
            beam: Expanded beam (many states)
            beam_width: Target size

        Returns:
            Pruned beam (diverse states, up to beam_width)

        Complexity: O(n log n) for sorting + O(n²) for diversity check
        """
        if len(beam) <= beam_width:
            return beam

        # Step 1: Remove exact duplicates (only if states have words placed)
        # For states with no words placed, skip deduplication (let score differentiate)
        has_words_placed = any(len(state.slot_assignments) > 0 for state in beam)

        if has_words_placed:
            unique_beam = []
            seen_signatures = set()

            for state in beam:
                # Create signature: frozenset of (slot_id, word) pairs
                signature = frozenset(state.slot_assignments.items())

                if signature not in seen_signatures:
                    unique_beam.append(state)
                    seen_signatures.add(signature)
        else:
            # All states are empty, keep all (differentiated by score)
            unique_beam = beam

        if len(unique_beam) <= beam_width:
            return unique_beam

        # Step 2: Sort by score (descending)
        unique_beam.sort(key=lambda s: s.score, reverse=True)

        # Step 3: Greedy diversity selection (only if states have words)
        if has_words_placed:
            selected = [unique_beam[0]]  # Always keep best

            for candidate in unique_beam[1:]:
                if len(selected) >= beam_width:
                    break

                # Check diversity: how many words differ from already selected?
                min_difference = min(
                    self._count_word_differences(candidate, s) for s in selected
                )

                # Only add if sufficiently different (at least 1 word different)
                if min_difference > 0:
                    selected.append(candidate)
        else:
            # No words placed yet, just take top-K by score
            selected = unique_beam[:beam_width]
            return selected

        # Step 4: If we didn't get enough diverse candidates, fill with best remaining
        # (Better to have some duplicates than incomplete beam)
        while len(selected) < beam_width and len(unique_beam) > len(selected):
            for state in unique_beam:
                if state not in selected:
                    selected.append(state)
                    if len(selected) >= beam_width:
                        break

        return selected

    def _count_word_differences(self, state1: BeamState, state2: BeamState) -> int:
        """Count how many words differ between two states."""
        words1 = set(state1.used_words)
        words2 = set(state2.used_words)
        # Symmetric difference: words in one but not both
        return len(words1 ^ words2)

    def _get_intersecting_slots(self, grid: Grid, reference_slot: Dict) -> List[Dict]:
        """
        Get slots that intersect with reference_slot.

        Only checks slots that share at least one cell with reference_slot.
        This is much more efficient than checking all slots.

        Args:
            grid: Current grid
            reference_slot: Slot to find intersections for

        Returns:
            List of slots that intersect with reference_slot
        """
        if reference_slot is None:
            # No reference slot - check all slots (fallback)
            return grid.get_empty_slots()

        intersecting = []
        all_slots = grid.get_empty_slots()

        for slot in all_slots:
            # Skip same slot
            if (slot['row'] == reference_slot['row'] and
                slot['col'] == reference_slot['col'] and
                slot['direction'] == reference_slot['direction']):
                continue

            # Check if they intersect
            if self._slots_intersect(reference_slot, slot):
                intersecting.append(slot)

        return intersecting

    def _slots_intersect(self, slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two slots share at least one cell.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            True if slots intersect, False otherwise
        """
        # Same direction can't intersect
        if slot1['direction'] == slot2['direction']:
            return False

        # Get cell positions for each slot
        def get_positions(slot):
            positions = []
            if slot['direction'] == 'across':
                for i in range(slot['length']):
                    positions.append((slot['row'], slot['col'] + i))
            else:  # down
                for i in range(slot['length']):
                    positions.append((slot['row'] + i, slot['col']))
            return set(positions)

        pos1 = get_positions(slot1)
        pos2 = get_positions(slot2)

        # Check for any common positions
        return bool(pos1 & pos2)

    def _is_viable_state(self, state: BeamState, last_filled_slot: Dict = None) -> bool:
        """
        Check if state has any dead ends (slots with 0 candidates).

        OPTIMIZATION: Only checks slots that intersect with last_filled_slot
        instead of all slots. This reduces false negatives dramatically while
        maintaining correctness.

        Args:
            state: Beam state to check
            last_filled_slot: The slot we just filled (optional)

        Returns:
            True if viable (checked slots have ≥1 candidate)
            False if dead end (any checked slot has 0 candidates)

        Complexity: O(intersecting_slots × pattern_match_time)
            - Before: O(38 slots × pattern_match)
            - After: O(~10 slots × pattern_match) [73% reduction]

        Rationale:
            - Checking ALL slots after placing 3 words is too pessimistic
            - Distant slots may look impossible now but become viable later
            - Only need to check slots that share cells with just-placed word
        """
        # Get slots to check (only intersecting ones if we have a reference)
        if last_filled_slot:
            slots_to_check = self._get_intersecting_slots(state.grid, last_filled_slot)
        else:
            # No reference - check all (first few slots)
            slots_to_check = state.grid.get_empty_slots()

        # DEBUG: Track viability check details
        if hasattr(state, '_debug_viability_count'):
            state._debug_viability_count += 1
        else:
            state._debug_viability_count = 0

        if state._debug_viability_count < 2:
            print(f"\nDEBUG VIABILITY: Checking {len(slots_to_check)} intersecting slots")

        # Check each slot has at least one candidate
        for slot in slots_to_check:
            pattern = state.grid.get_pattern_for_slot(slot)

            # Get candidates (excluding used words)
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=self.min_score
            )

            # Filter out used words
            available_candidates = [
                (word, score) for word, score in candidates
                if word not in state.used_words
            ]

            # Dead end if no candidates
            if not available_candidates:
                if state._debug_viability_count < 2:
                    print(f"  DEAD END: slot at ({slot['row']},{slot['col']}) {slot['direction']} length={slot['length']}")
                    print(f"    Pattern: '{pattern}'")
                    print(f"    Total candidates: {len(candidates)}, Available (not used): 0")
                    print(f"    Used words: {list(state.used_words)[:5]}...")
                return False

        if state._debug_viability_count < 2:
            print(f"  ✓ All {len(slots_to_check)} intersecting slots viable!")

        return True

    def _apply_diversity_bonus(
        self,
        beam: List[BeamState]
    ) -> List[BeamState]:
        """
        Apply bonus to states that differ from others in beam.

        Diversity metric: Count of slots with different words
        Bonus formula: avg_difference × diversity_bonus

        Args:
            beam: Beam before scoring

        Returns:
            Beam with updated scores (modified in-place)

        Complexity: O(beam_width² × slots)

        Rationale: Encourages exploration of different search paths
        """
        if len(beam) <= 1:
            return beam

        for i, state_i in enumerate(beam):
            diversity_score = 0

            for j, state_j in enumerate(beam):
                if i == j:
                    continue

                # Count slots with different words
                diff_count = self._count_differences(state_i, state_j)
                diversity_score += diff_count

            # Average diversity across beam
            avg_diversity = diversity_score / (len(beam) - 1)

            # Apply bonus
            state_i.score += avg_diversity * self.diversity_bonus

        return beam

    def _count_differences(
        self,
        state1: BeamState,
        state2: BeamState
    ) -> int:
        """
        Count number of slots with different words between two states.

        Args:
            state1: First state
            state2: Second state

        Returns:
            Number of differing slot assignments
        """
        diff_count = 0

        # Check all slots in state1
        for slot_id, word1 in state1.slot_assignments.items():
            word2 = state2.slot_assignments.get(slot_id)
            if word2 is None or word1 != word2:
                diff_count += 1

        # Check slots only in state2
        for slot_id in state2.slot_assignments:
            if slot_id not in state1.slot_assignments:
                diff_count += 1

        return diff_count

    def _compute_score(
        self,
        state: BeamState,
        word_score: int
    ) -> float:
        """
        Compute quality score for a state.

        Formula:
        - Completion weight: 70%
        - Quality weight: 30%

        Args:
            state: State to score
            word_score: Score of most recently placed word (1-100)

        Returns:
            Score in range 0.0-100.0
        """
        completion_weight = 70.0
        quality_weight = 30.0

        completion_score = (state.slots_filled / state.total_slots) * 100
        quality_score = word_score  # 1-100

        total = (completion_score * completion_weight / 100) + \
                (quality_score * quality_weight / 100)

        return total
