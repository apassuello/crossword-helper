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
from .crosswordese import filter_crosswordese


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
        progress_reporter=None,
        theme_entries: Optional[Dict[Tuple[int, int, str], str]] = None
    ):
        """
        Initialize beam search solver.

        PHASE 2.2 - Research Gap #6: Theme Entry Prioritization

        Args:
            grid: Grid to fill (can be partially filled)
            word_list: Available words
            pattern_matcher: Pattern matching engine (trie or regex)
            beam_width: Number of parallel solutions (default: 5)
            candidates_per_slot: Top-K words to try per slot (default: 10)
            min_score: Minimum word quality score (default: 0)
            diversity_bonus: Bonus for diverse beams 0.0-1.0 (default: 0.1)
            progress_reporter: Optional progress reporting
            theme_entries: Dict of theme entries {(row, col, direction): word}
                          These are NON-NEGOTIABLE and will be placed first
                          Example: {(0, 0, 'across'): 'THEMEANSWER'}

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
        self.theme_entries = theme_entries or {}  # Theme entries (NON-NEGOTIABLE)

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

        # Sort slots with THEME ENTRY PRIORITIZATION
        # Theme entries are NON-NEGOTIABLE and must be placed first
        # CRITICAL: Longest slots filled first to ensure high-quality words
        if self.theme_entries:
            sorted_slots, theme_words = self._prioritize_theme_entries(all_slots)
        else:
            sorted_slots = self._sort_slots_by_constraint(all_slots)
            theme_words = set()

        # Pre-fill theme entries in grid (if any)
        initial_grid = self.grid.clone()
        theme_slot_count = 0
        theme_slot_assignments = {}

        for slot_id, word in self.theme_entries.items():
            row, col, direction = slot_id
            initial_grid.place_word(word.upper(), row, col, direction)
            theme_slot_assignments[slot_id] = word.upper()
            theme_slot_count += 1

        # Initialize beam with theme entries pre-filled
        initial_state = BeamState(
            grid=initial_grid,
            slots_filled=theme_slot_count,  # Theme entries already placed
            total_slots=total_slots,
            score=100.0 * theme_slot_count,  # Initial score for theme entries
            used_words=theme_words.copy(),  # Theme words marked as used
            slot_assignments=theme_slot_assignments.copy()
        )
        beam = [initial_state.clone() for _ in range(self.beam_width)]

        # DEBUG: Note that we're using DYNAMIC MRV, not static ordering
        print("\nDEBUG: Using DYNAMIC MRV variable ordering (will interleave directions naturally)")
        print(f"Total slots to fill: {total_slots}")

        # Main beam search loop with DYNAMIC MRV
        # Track which slots have been filled
        filled_slots = set(self.theme_entries.keys())  # Start with theme entries
        slot_idx = 0

        while len(filled_slots) < total_slots:
            self.iterations += 1
            slot_idx += 1

            # Check timeout
            elapsed = time.time() - self.start_time
            if elapsed > timeout:
                break

            # DYNAMIC MRV: Select next slot based on current state
            unfilled_slots = [s for s in all_slots
                             if (s['row'], s['col'], s['direction']) not in filled_slots]

            if not unfilled_slots:
                break  # All slots filled

            # Use first beam state as reference for MRV calculation
            slot = self._select_next_slot_dynamic_mrv(unfilled_slots, beam[0])

            if slot is None:
                print(f"\nDEBUG: No slot selected by MRV at iteration {slot_idx}")
                break

            # Mark slot as being filled
            slot_id = (slot['row'], slot['col'], slot['direction'])
            filled_slots.add(slot_id)

            # DEBUG: Print what MRV selected (shows direction interleaving)
            if slot_idx <= 10:  # Show first 10 to see interleaving pattern
                print(f"\nDEBUG MRV: Slot {slot_idx}/{total_slots}: {slot['direction'].upper():6s} length={slot['length']:2d} at ({slot['row']:2d},{slot['col']:2d})")

            # Report progress
            if self.progress_reporter:
                progress = int((len(filled_slots) / total_slots) * 90) + 10  # 10-100%
                self.progress_reporter.update(
                    progress,
                    f"Beam search: slot {len(filled_slots)}/{total_slots}"
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

            # PHASE 4: Apply Smart Adaptive Beam Width + Diverse Beam Search
            # Calculate adaptive width based on current search state
            # (unfilled_slots already calculated above for MRV)
            adaptive_width = self._get_adaptive_beam_width(
                beam_states=beam,
                unfilled_slots=unfilled_slots,
                total_slots=total_slots,
                slot=slot
            )

            # Apply pruning with adaptive width
            if len(expanded_beam) > adaptive_width:
                # Get candidate words for this slot (for diversity calculation)
                pattern = beam[0].grid.get_pattern_for_slot(slot) if beam else ""
                min_score = self._get_min_score_for_length(slot['length'])
                slot_candidates = self.pattern_matcher.find(pattern, min_score=min_score)
                slot_candidates = filter_crosswordese(slot_candidates, slot['length'])

                # Temporarily override beam_width for diverse pruning
                original_width = self.beam_width
                self.beam_width = adaptive_width

                # Apply Diverse Beam Search to select diverse states
                beam = self._diverse_beam_prune(expanded_beam, slot, num_groups=4, diversity_lambda=0.5)

                # Restore original width
                self.beam_width = original_width
            else:
                # Not enough states to need diversity - just take all
                beam = expanded_beam

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

        # FIX #1 (Phase 4.1 - REVISED): Clear GIBBERISH from unfilled slots
        # Only clear slots that contain obvious gibberish patterns
        # Don't clear all unfilled slots (too aggressive - breaks partial fills)
        for slot in problematic_slots:
            pattern = best_state.grid.get_pattern_for_slot(slot)
            # Check if pattern contains gibberish (repeated letters)
            if self._is_gibberish_pattern(pattern):
                best_state.grid.remove_word(
                    slot['row'], slot['col'], slot['length'], slot['direction']
                )

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
        Sort slots by length-first ordering with DIRECTION INTERLEAVING.

        CRITICAL FIXES (Phase 1.1 - Research Gap #1):
        1. Fill LONGEST words first (Ginsberg 1990, Shortz, Dr.Fill)
        2. INTERLEAVE directions (Across, Down, Across, Down...)
           - Prevents impossible vertical constraints
           - Shortz (NYT): "Never commit to all acrosses before downs"
           - Crossfire: "Interleaved construction mode (default)"

        Previous bug: All 11-letter ACROSS → all 11-letter DOWN
        Result: DOWN words impossible/gibberish

        Algorithm:
        1. Group slots by length (descending: 11, 9, 7, 5, 3)
        2. Within each length group:
           a. Separate ACROSS and DOWN
           b. Sort each by secondary constraint
           c. INTERLEAVE: A, D, A, D, A, D...
        3. Return interleaved list

        Args:
            slots: List of slot dicts

        Returns:
            Sorted list with direction interleaving
        """
        from collections import defaultdict

        # Group by length
        length_groups = defaultdict(list)
        for slot in slots:
            length_groups[slot['length']].append(slot)

        result = []

        # Process each length group (longest first)
        for length in sorted(length_groups.keys(), reverse=True):
            group = length_groups[length]

            # Separate by direction
            across = [s for s in group if s['direction'] == 'across']
            down = [s for s in group if s['direction'] == 'down']

            # Sort each by secondary constraint (domain size, empty count)
            across_sorted = self._sort_by_secondary_constraint(across)
            down_sorted = self._sort_by_secondary_constraint(down)

            # INTERLEAVE directions: A, D, A, D, A, D...
            max_len = max(len(across_sorted), len(down_sorted))
            for i in range(max_len):
                if i < len(across_sorted):
                    result.append(across_sorted[i])
                if i < len(down_sorted):
                    result.append(down_sorted[i])

        return result

    def _sort_by_secondary_constraint(self, slots: List[Dict]) -> List[Dict]:
        """
        Secondary sort within same length/direction by constraint level.

        Used after grouping by length and direction to order slots
        within each group by how constrained they are.

        Sorting criteria:
        1. Domain size (ascending): Fewer candidates = more constrained
        2. Empty count (ascending): More letters filled = more constrained

        Args:
            slots: List of slots (same length, same direction)

        Returns:
            Sorted list (most constrained first)
        """
        def constraint_key(slot: Dict):
            pattern = self.grid.get_pattern_for_slot(slot)

            # Use length-dependent quality threshold
            min_score = self._get_min_score_for_length(slot['length'])

            # Count candidates (domain size)
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=min_score
            )
            domain_size = len(candidates)

            # Count empty cells
            empty_count = pattern.count('?')

            # Sort by domain size, then empty count
            return (domain_size, empty_count)

        return sorted(slots, key=constraint_key)

    def _prioritize_theme_entries(self, slots: List[Dict]) -> Tuple[List[Dict], Set[str]]:
        """
        Separate theme entries from regular slots and prioritize them.

        PHASE 2.2 - Research Gap #6: Theme Entry Prioritization

        Theme entries are NON-NEGOTIABLE words that must appear in the puzzle
        (typically the answer to the puzzle's theme). They are:
        - Placed FIRST, before any other fill
        - Never changed during search or repair
        - Sorted by length (longest first) among themselves

        Research (Shortz, NYT): "Theme entries are non-negotiable"
        Research (Ginsberg): "Mandatory entries have weight ∞"

        Args:
            slots: All slots in grid

        Returns:
            Tuple of (ordered_slots, theme_words) where:
            - ordered_slots: Theme slots first, then regular slots
            - theme_words: Set of theme words (to mark as used)
        """
        theme_slots = []
        regular_slots = []
        theme_words = set()

        for slot in slots:
            slot_id = (slot['row'], slot['col'], slot['direction'])
            if slot_id in self.theme_entries:
                theme_slots.append(slot)
                theme_words.add(self.theme_entries[slot_id].upper())
            else:
                regular_slots.append(slot)

        # Sort theme slots by length (longest first)
        theme_slots_sorted = sorted(theme_slots, key=lambda s: s['length'], reverse=True)

        # Sort regular slots with interleaving
        regular_slots_sorted = self._sort_slots_by_constraint(regular_slots)

        # Theme entries ALWAYS come first
        return (theme_slots_sorted + regular_slots_sorted, theme_words)

    def _get_min_score_for_length(self, length: int) -> int:
        """
        Return quality threshold appropriate for word length.

        CRITICAL FIX (Phase 1.2 - Research Gap #2):
        Different word lengths require different quality standards.

        Research (NYT Crossword Construction Guidelines, Will Shortz):
        - Short words (3-4 letters): "Glue" words, can be obscure crosswordese
        - Medium words (5-6 letters): Should be recognizable
        - Long words (7-8 letters): Must be common, in-the-language
        - Very long (9+ letters): Must be high-quality, well-known phrases

        Previous bug: min_score=30 for ALL lengths
        Result: Long words accept low-quality fills, grid looks poor

        Args:
            length: Word length in letters

        Returns:
            Minimum score threshold for this length:
            - 3-letter: 0 (any word, including ESNE, ERE, ORE)
            - 4-letter: 10 (slightly filtered)
            - 5-6 letter: 30 (prefer common)
            - 7-8 letter: 50 (common only)
            - 9+ letter: 70 (high-quality only)
        """
        if length <= 3:
            return 0    # Accept any word (crosswordese OK)
        elif length == 4:
            return 10   # Slightly filtered
        elif length <= 6:
            return 30   # Prefer common words
        elif length <= 8:
            return 50   # Common words only
        else:  # 9+ letters
            return 70   # High-quality phrases only

    def _get_adaptive_beam_width(
        self,
        beam_states: List[BeamState],
        unfilled_slots: List[Dict],
        total_slots: int,
        slot: Dict
    ) -> int:
        """
        Smart adaptive beam width based on search state, not just depth.

        Key insights from research:
        - WIDEN when diversity is low (prevent collapse)
        - NARROW when few viable candidates exist (efficiency)
        - WIDEN in middle depths (fight convergence)

        Args:
            beam_states: Current beam of states
            unfilled_slots: Remaining unfilled slots
            total_slots: Total number of slots in grid
            slot: Current slot being filled

        Returns:
            Adaptive beam width (3-20)
        """
        # Calculate depth
        depth = 1.0 - (len(unfilled_slots) / total_slots)
        base_width = self.beam_width

        # Factor 1: Calculate diversity (variance in scores)
        if len(beam_states) > 1:
            scores = [s.score for s in beam_states]
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            # Normalize variance
            normalized_variance = variance / (mean_score ** 2 + 0.001)
        else:
            normalized_variance = 1.0

        # Low variance = risk of collapse, need MORE width
        if normalized_variance < 0.05:
            diversity_factor = 1.5  # INCREASE width to maintain diversity
        elif normalized_variance < 0.1:
            diversity_factor = 1.2
        else:
            diversity_factor = 1.0

        # Factor 2: Count viable candidates for current slot
        pattern = beam_states[0].grid.get_pattern_for_slot(slot) if beam_states else "?" * slot['length']
        min_score = self._get_min_score_for_length(slot['length'])
        candidates = self.pattern_matcher.find(pattern, min_score=min_score)
        viable_count = len(candidates)

        # Few candidates = can use narrower beam
        candidate_factor = min(1.0, viable_count / (base_width * 2))
        if candidate_factor < 0.3:
            candidate_factor = 0.3  # Don't narrow too much

        # Factor 3: Smart depth adjustment (not simple narrowing!)
        if depth < 0.3:
            depth_factor = 1.0  # Full width early for exploration
        elif depth < 0.7:
            depth_factor = 1.2  # WIDER in middle (fight convergence!)
        else:
            depth_factor = 0.8  # Only mild narrowing near end

        # Calculate final width
        adaptive_width = int(base_width * diversity_factor * candidate_factor * depth_factor)

        # Clamp between reasonable bounds
        adaptive_width = max(3, min(20, adaptive_width))

        # Debug output
        if hasattr(self, 'debug_adaptive') and self.debug_adaptive:
            print(f"DEBUG ADAPTIVE WIDTH: depth={depth:.2f}, variance={normalized_variance:.3f}, "
                  f"viable={viable_count}, factors=(div={diversity_factor:.1f}, "
                  f"cand={candidate_factor:.2f}, depth={depth_factor:.1f}) → width={adaptive_width}")

        return adaptive_width

    def _select_next_slot_dynamic_mrv(
        self,
        unfilled_slots: List[Dict],
        current_state: BeamState
    ) -> Optional[Dict]:
        """
        Dynamic MRV + degree heuristic for variable ordering.
        Recomputed after each assignment based on current domains.

        Key insight from Ginsberg (1990): "Dynamic ordering is NECESSARY
        for solving more difficult problems"

        Args:
            unfilled_slots: List of slots not yet filled
            current_state: Current beam state for domain evaluation

        Returns:
            Next slot to fill, or None if no slots remain
        """
        if not unfilled_slots:
            return None

        candidates = []
        for slot in unfilled_slots:
            # Get current pattern for this slot
            pattern = current_state.grid.get_pattern_for_slot(slot)

            # MRV: Count currently valid candidates given state
            min_score = self._get_min_score_for_length(slot['length'])
            valid_words = self.pattern_matcher.find(pattern, min_score=min_score)
            domain_size = len(valid_words)

            # Degree: Count unfilled crossing slots
            degree = 0
            for crossing in self._get_slot_crossings(slot):
                crossing_id = (crossing['row'], crossing['col'], crossing['direction'])
                if crossing_id not in current_state.slot_assignments:
                    degree += 1

            # Track for selection
            candidates.append({
                'slot': slot,
                'domain_size': domain_size,
                'degree': degree,
                'length': slot['length'],
                'direction': slot['direction']
            })

        if not candidates:
            return None

        # Determine last filled direction for tie-breaking
        last_direction = None
        if current_state.slot_assignments:
            # Get the most recently filled slot's direction
            last_slot_key = list(current_state.slot_assignments.keys())[-1]
            last_direction = last_slot_key[2]  # (row, col, direction)

        # Sort by MRV (ascending), then degree (descending), then length (descending)
        # Final tie-breaker: prefer alternating directions to encourage interleaving
        # If this is the first slot, prefer DOWN to avoid bias from get_word_slots() ordering
        candidates.sort(key=lambda c: (
            c['domain_size'],
            -c['degree'],
            -c['length'],
            0 if (last_direction is None and c['direction'] == 'down') or \
                 (last_direction is not None and c['direction'] != last_direction) else 1
        ))

        selected = candidates[0]

        # Debug: Verify direction interleaving
        # Always show MRV selection for first 10 slots to verify interleaving
        if len(current_state.slot_assignments) <= 10:
            directions = [c['direction'] for c in candidates[:5]]
            domain_sizes = [c['domain_size'] for c in candidates[:5]]
            print(f"  MRV top 5: {list(zip(directions, domain_sizes))}")
            print(f"  → Selected: {selected['direction'].upper()} (domain={selected['domain_size']})")

        return selected['slot']

    def _get_slot_crossings(self, slot: Dict) -> List[Dict]:
        """
        Get all slots that cross this slot.

        Args:
            slot: Slot dictionary with row, col, direction, length

        Returns:
            List of crossing slot dictionaries
        """
        crossings = []
        all_slots = self.grid.get_word_slots()

        for other_slot in all_slots:
            # Skip same slot
            if (other_slot['row'] == slot['row'] and
                other_slot['col'] == slot['col'] and
                other_slot['direction'] == slot['direction']):
                continue

            # Check for intersection
            if slot['direction'] == 'across' and other_slot['direction'] == 'down':
                # This slot is horizontal, other is vertical
                if (slot['row'] >= other_slot['row'] and
                    slot['row'] < other_slot['row'] + other_slot['length'] and
                    other_slot['col'] >= slot['col'] and
                    other_slot['col'] < slot['col'] + slot['length']):
                    crossings.append(other_slot)
            elif slot['direction'] == 'down' and other_slot['direction'] == 'across':
                # This slot is vertical, other is horizontal
                if (slot['col'] >= other_slot['col'] and
                    slot['col'] < other_slot['col'] + other_slot['length'] and
                    other_slot['row'] >= slot['row'] and
                    other_slot['row'] < slot['row'] + slot['length']):
                    crossings.append(other_slot)

        return crossings

    def _mac_propagate(
        self,
        slot: Dict,
        word: str,
        state: BeamState,
        domains: Dict[Tuple[int, int, str], List[str]]
    ) -> Tuple[bool, Dict, Set]:
        """
        Maintaining Arc Consistency (AC-3 algorithm).
        Transitive constraint propagation after assignment.

        Key insight from Sabin & Freuder (1994): "MAC is the most efficient
        general algorithm for solving hard CSPs"

        Args:
            slot: Slot being filled
            word: Word being assigned to slot
            state: Current beam state
            domains: Current domains for all slots

        Returns:
            (success, reduced_domains, conflict_set)
            - success: False if domain wipeout detected
            - reduced_domains: Which domains were reduced and by how much
            - conflict_set: Slots involved in the conflict
        """
        # Initialize queue with all arcs affected by this assignment
        queue = []
        slot_id = (slot['row'], slot['col'], slot['direction'])

        for crossing in self._get_slot_crossings(slot):
            crossing_id = (crossing['row'], crossing['col'], crossing['direction'])
            if crossing_id not in state.slot_assignments:
                queue.append((crossing_id, slot_id))

        reduced_domains = {}
        conflict_set = set()

        while queue:
            xi_id, xj_id = queue.pop(0)

            # Skip if xi is already assigned
            if xi_id in state.slot_assignments:
                continue

            # Get the slots
            xi_slot = self._get_slot_by_id(xi_id)
            if not xi_slot:
                continue

            # Revise domain of xi given xj's assignment
            removed = self._revise_domain(
                xi_slot, xi_id,
                slot if xj_id == slot_id else self._get_slot_by_id(xj_id),
                word if xj_id == slot_id else state.slot_assignments.get(xj_id, ''),
                domains
            )

            if removed:
                if xi_id not in reduced_domains:
                    reduced_domains[xi_id] = []
                reduced_domains[xi_id].extend(removed)

                # Domain wipeout - conflict detected
                if xi_id in domains and len(domains[xi_id]) == 0:
                    conflict_set.add(xj_id)
                    return False, reduced_domains, conflict_set

                # Add all OTHER neighbors of xi to queue (transitive propagation)
                for neighbor in self._get_slot_crossings(xi_slot):
                    neighbor_id = (neighbor['row'], neighbor['col'], neighbor['direction'])
                    if neighbor_id != xj_id and neighbor_id in state.slot_assignments:
                        queue.append((xi_id, neighbor_id))

        return True, reduced_domains, conflict_set

    def _revise_domain(
        self,
        xi_slot: Dict,
        xi_id: Tuple,
        xj_slot: Dict,
        xj_word: str,
        domains: Dict
    ) -> List[str]:
        """
        Remove values from xi's domain with no support in xj.

        Args:
            xi_slot: Slot whose domain is being revised
            xi_id: ID of xi_slot
            xj_slot: Constraining slot
            xj_word: Word assigned to xj
            domains: Current domains

        Returns:
            List of removed words
        """
        if not xj_word or xi_id not in domains:
            return []

        # Find crossing position
        crossing_pos = self._get_crossing_position(xi_slot, xj_slot)
        if crossing_pos is None:
            return []

        xi_pos, xj_pos = crossing_pos
        required_letter = xj_word[xj_pos]

        # Remove words from xi that don't match required letter
        removed = []
        remaining = []
        for word in domains[xi_id]:
            if word[xi_pos] != required_letter:
                removed.append(word)
            else:
                remaining.append(word)

        domains[xi_id] = remaining
        return removed

    def _get_slot_by_id(self, slot_id: Tuple) -> Optional[Dict]:
        """Get slot dict by its ID tuple (row, col, direction)."""
        row, col, direction = slot_id
        for slot in self.grid.get_word_slots():
            if (slot['row'] == row and
                slot['col'] == col and
                slot['direction'] == direction):
                return slot
        return None

    def _get_crossing_position(self, slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get the position where two slots cross.

        Returns:
            (pos_in_slot1, pos_in_slot2) or None if no crossing
        """
        if slot1['direction'] == slot2['direction']:
            return None  # Parallel slots don't cross

        if slot1['direction'] == 'across':
            h_slot, v_slot = slot1, slot2
        else:
            h_slot, v_slot = slot2, slot1

        # Check if they intersect
        h_row, h_col = h_slot['row'], h_slot['col']
        v_row, v_col = v_slot['row'], v_slot['col']

        if (h_row >= v_row and h_row < v_row + v_slot['length'] and
            v_col >= h_col and v_col < h_col + h_slot['length']):
            # They cross!
            h_pos = v_col - h_col
            v_pos = h_row - v_row

            if slot1['direction'] == 'across':
                return (h_pos, v_pos)
            else:
                return (v_pos, h_pos)

        return None

    def _order_values_lcv(
        self,
        slot: Dict,
        candidates: List[Tuple[str, int]],
        state: BeamState
    ) -> List[Tuple[str, int]]:
        """
        Order candidates by Least Constraining Value heuristic.
        Prefer words that leave more options for neighboring variables.

        Args:
            slot: Slot being filled
            candidates: List of (word, score) tuples
            state: Current beam state

        Returns:
            Reordered candidates with LCV consideration
        """
        scored_candidates = []

        for word, quality_score in candidates:
            # Count how many options this removes from neighbors
            constraints_removed = 0

            for crossing in self._get_slot_crossings(slot):
                crossing_id = (crossing['row'], crossing['col'], crossing['direction'])

                # Skip already filled slots
                if crossing_id in state.slot_assignments:
                    continue

                # Get crossing position
                crossing_pos = self._get_crossing_position(slot, crossing)
                if crossing_pos:
                    my_pos, their_pos = crossing_pos
                    required_letter = word[my_pos]

                    # Count how many words would be eliminated
                    pattern = state.grid.get_pattern_for_slot(crossing)
                    min_score = self._get_min_score_for_length(crossing['length'])
                    crossing_candidates = self.pattern_matcher.find(pattern, min_score=min_score)

                    for other_word, _ in crossing_candidates:
                        if other_word[their_pos] != required_letter:
                            constraints_removed += 1

            # Combine quality with constraint impact (lower constraints_removed is better)
            # Normalize constraints_removed to 0-100 scale
            lcv_penalty = min(100, constraints_removed / 10)
            combined_score = quality_score - 0.3 * lcv_penalty

            scored_candidates.append((word, quality_score, combined_score))

        # Sort by combined score (higher is better)
        scored_candidates.sort(key=lambda x: -x[2])

        # Return in original format but with LCV ordering
        return [(w, s) for w, s, _ in scored_candidates]

    def _stratified_shuffle(
        self,
        candidates: List[Tuple[str, int]],
        tier_boundaries: List[int] = [10, 30, 60, 100]
    ) -> List[Tuple[str, int]]:
        """
        Shuffle within quality tiers to prevent alphabetical bias
        while preserving quality gradient.

        Args:
            candidates: List of (word, score) tuples
            tier_boundaries: Percentile boundaries for tiers

        Returns:
            Stratified shuffled candidates
        """
        import random

        n = len(candidates)
        if n == 0:
            return []

        # Sort by quality first
        sorted_candidates = sorted(candidates, key=lambda x: -x[1])

        result = []
        prev_idx = 0

        for boundary in tier_boundaries:
            tier_size = int(n * boundary / 100)
            tier = sorted_candidates[prev_idx:tier_size]

            # Shuffle within tier
            random.shuffle(tier)
            result.extend(tier)
            prev_idx = tier_size

        return result

    def _diverse_beam_prune(
        self,
        expanded_beam: List[BeamState],
        slot: Dict,
        num_groups: int = 4,
        diversity_lambda: float = 0.5
    ) -> List[BeamState]:
        """
        Select diverse states from expanded beam using Diverse Beam Search principles.

        Instead of generating new states, this selects diverse states from
        an already-expanded beam to prevent collapse.

        Args:
            expanded_beam: All candidate states
            slot: Current slot being filled
            num_groups: Number of diversity groups
            diversity_lambda: Diversity weight

        Returns:
            Diverse subset of beam_width states
        """
        if len(expanded_beam) <= self.beam_width:
            return expanded_beam

        # Sort states by score first
        sorted_states = sorted(expanded_beam, key=lambda s: s.score, reverse=True)

        # Partition into diversity groups
        groups = []
        beams_per_group = max(1, self.beam_width // num_groups)

        for g in range(num_groups):
            group = []

            for state in sorted_states:
                if state in [s for grp in groups for s in grp]:
                    continue  # Already selected in previous group

                # Calculate diversity penalty against previous groups
                diversity_penalty = 0.0
                if groups:
                    for prev_group in groups:
                        for prev_state in prev_group:
                            # Measure state difference
                            diff = self._state_diversity_score(state, prev_state)
                            diversity_penalty += diff

                    # Normalize
                    num_prev_states = sum(len(g) for g in groups)
                    if num_prev_states > 0:
                        diversity_penalty /= num_prev_states

                # Augmented score
                augmented_score = state.score + diversity_lambda * diversity_penalty
                group.append((state, augmented_score))

            # Select top diverse candidates for this group
            group.sort(key=lambda x: -x[1])
            selected = [state for state, _ in group[:beams_per_group]]

            if selected:
                groups.append(selected)

        # Flatten groups
        result = []
        for group in groups:
            result.extend(group)

        # Debug output
        if len(result) > 0:
            print(f"  DEBUG DIVERSE PRUNE: Selected {len(result)} diverse states from {len(expanded_beam)} candidates")
            print(f"    Groups={num_groups}, Lambda={diversity_lambda}")

        return result[:self.beam_width]

    def _state_diversity_score(self, state1: BeamState, state2: BeamState) -> float:
        """
        Calculate diversity score between two beam states.

        Measures how different two states are based on their word assignments.

        Args:
            state1: First state
            state2: Second state

        Returns:
            Diversity score (higher = more different)
        """
        # Count different word assignments
        all_slots = set(state1.slot_assignments.keys()) | set(state2.slot_assignments.keys())

        different_count = 0
        for slot_id in all_slots:
            word1 = state1.slot_assignments.get(slot_id, "")
            word2 = state2.slot_assignments.get(slot_id, "")
            if word1 != word2:
                different_count += 1

        # Normalize by total slots
        return different_count / max(1, len(all_slots))

    def _diverse_beam_search(
        self,
        beam: List[BeamState],
        slot: Dict,
        candidates: List[Tuple[str, int]],
        num_groups: int = 4,
        diversity_lambda: float = 0.5
    ) -> List[BeamState]:
        """
        Diverse Beam Search (Vijayakumar et al., 2016 AAAI).

        PHASE 4 - Critical Fix #1: Replace adaptive beam width with diversity mechanism.

        Research (Cohen et al. 2019 "Beam Search Curse"):
        - Adaptive narrowing (8→5→3→1) is NOT validated
        - Beam quality is "highly non-monotonic" - narrowing can worsen solutions
        - Instead, use constant width + diversity to prevent beam collapse

        Research (Vijayakumar et al. 2016 "Diverse Beam Search"):
        - 300% increase in distinct solutions
        - Better top-1 solutions through exploration/exploitation balance

        Args:
            beam: Current beam states
            slot: Slot being filled
            candidates: Word candidates with scores
            num_groups: Number of diversity groups (default 4)
            diversity_lambda: Diversity weight (0.5 = balanced)

        Returns:
            New diverse beam states (constant width)
        """
        if not beam or not candidates:
            return []

        groups = []
        beams_per_group = max(1, self.beam_width // num_groups)

        for g in range(num_groups):
            group_states = []

            for state in beam[:beams_per_group]:  # Take subset of beam for this group
                for word, score in candidates:
                    if word in state.used_words:
                        continue

                    # Calculate diversity penalty (Hamming distance to previous groups)
                    diversity_penalty = 0.0
                    if groups:
                        for prev_group in groups:
                            for prev_state in prev_group:
                                # Count differing letters at crossing positions
                                diff = self._hamming_distance_at_crossings(
                                    word, prev_state, slot
                                )
                                diversity_penalty += diff
                        # Normalize by number of previous states
                        num_prev_states = sum(len(g) for g in groups)
                        if num_prev_states > 0:
                            diversity_penalty /= num_prev_states

                    # Augmented score = quality + diversity bonus
                    augmented_score = score + diversity_lambda * diversity_penalty

                    # Create new state
                    new_state = state.clone()
                    new_state.grid.place_word(word, slot['row'], slot['col'], slot['direction'])
                    new_state.slots_filled += 1
                    new_state.score += augmented_score
                    new_state.used_words.add(word)
                    new_state.slot_assignments[(slot['row'], slot['col'], slot['direction'])] = word

                    group_states.append((new_state, augmented_score))

            # Select top candidates for this group
            group_states.sort(key=lambda x: -x[1])
            group = [state for state, _ in group_states[:beams_per_group]]

            if group:
                groups.append(group)

        # Flatten groups into single beam (maintain constant width)
        result = []
        for group in groups:
            result.extend(group)

        # DEBUG: Show diversity effect
        if result:
            print(f"  DEBUG DIVERSE BEAM: Generated {len(result)} diverse candidates from {num_groups} groups")
            print(f"    Diversity lambda={diversity_lambda} applied to prevent collapse")

        return result[:self.beam_width]  # Maintain constant beam width

    def _hamming_distance_at_crossings(
        self, word: str, state: BeamState, slot: Dict
    ) -> int:
        """
        Count differing letters at intersection positions.

        Helper for Diverse Beam Search - measures diversity between
        word placement and existing state at crossing points.

        Args:
            word: Word to place
            state: Existing beam state
            slot: Slot where word would be placed

        Returns:
            Number of differing letters at crossings
        """
        diff_count = 0

        # Get all crossing slots for this slot
        for other_slot in state.grid.slots:
            if other_slot['direction'] != slot['direction']:
                # Check if they intersect
                intersection = self._get_slot_intersection(slot, other_slot)
                if intersection:
                    my_pos, their_pos = intersection

                    # Check if other slot is filled
                    other_id = (other_slot['row'], other_slot['col'], other_slot['direction'])
                    if other_id in state.slot_assignments:
                        other_word = state.slot_assignments[other_id]
                        # Count if letters differ
                        if my_pos < len(word) and their_pos < len(other_word):
                            if word[my_pos] != other_word[their_pos]:
                                diff_count += 1

        return diff_count

    def _get_slot_intersection(self, slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get intersection positions between two slots.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (slot1_position, slot2_position) if they intersect, None otherwise
        """
        if slot1['direction'] == slot2['direction']:
            return None  # Parallel slots don't intersect

        # Get cell coordinates for each slot
        cells1 = set()
        cells2 = set()

        if slot1['direction'] == 'across':
            for i in range(slot1['length']):
                cells1.add((slot1['row'], slot1['col'] + i, i))
        else:  # down
            for i in range(slot1['length']):
                cells1.add((slot1['row'] + i, slot1['col'], i))

        if slot2['direction'] == 'across':
            for i in range(slot2['length']):
                cells2.add((slot2['row'], slot2['col'] + i, i))
        else:  # down
            for i in range(slot2['length']):
                cells2.add((slot2['row'] + i, slot2['col'], i))

        # Find intersection
        for r1, c1, pos1 in cells1:
            for r2, c2, pos2 in cells2:
                if r1 == r2 and c1 == c2:
                    return (pos1, pos2)

        return None

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

            # Use length-dependent quality threshold
            min_score = self._get_min_score_for_length(slot['length'])

            # Get ALL candidate words
            all_candidates = self.pattern_matcher.find(
                pattern,
                min_score=min_score
            )

            if len(all_candidates) == 0:
                # No candidates: this beam state is dead
                continue

            # CROSSWORDESE FILTER (Phase 2.1 - Research Gap #8):
            # Filter out unacceptable crosswordese based on slot length
            # - 3-4 letters: Crosswordese OK (glue words)
            # - 5-6 letters: Crosswordese penalized (score reduced 50%)
            # - 7+ letters: Crosswordese completely filtered (unacceptable)
            all_candidates = filter_crosswordese(all_candidates, slot['length'])

            if len(all_candidates) == 0:
                # No candidates after crosswordese filter: dead end
                continue

            # QUALITY FILTER: For long slots, reject likely gibberish
            if slot['length'] >= 7:
                quality_candidates = [
                    (word, score) for word, score in all_candidates
                    if self._is_quality_word(word)
                ]

                # Safety valve: only use quality filter if enough candidates remain
                if len(quality_candidates) >= 5:
                    all_candidates = quality_candidates

            # PHASE 4 ENHANCEMENT: Apply LCV ordering then stratified shuffling
            # Step 1: Order by Least Constraining Value (prefer words that leave more options)
            all_candidates = self._order_values_lcv(slot, all_candidates, state)

            # Step 2: Apply stratified shuffling to break alphabetical bias while preserving quality
            # This prevents beam collapse from alphabetical ordering
            all_candidates = self._stratified_shuffle(all_candidates)

            # Debug output for LCV impact
            if hasattr(self, 'debug_lcv') and self.debug_lcv and beam_idx == 0:
                print(f"DEBUG LCV: Top 5 candidates after LCV+shuffle for slot at ({slot['row']},{slot['col']}):")
                for word, score in all_candidates[:5]:
                    print(f"  {word}: score={score}")

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

                # PHASE 4: MAC Propagation for early conflict detection
                # Initialize domains if not already present
                if not hasattr(new_state, 'domains'):
                    new_state.domains = {}
                    # Initialize domains for all unfilled slots
                    for s in self.grid.get_word_slots():
                        s_id = (s['row'], s['col'], s['direction'])
                        if s_id not in new_state.slot_assignments:
                            pattern = new_state.grid.get_pattern_for_slot(s)
                            min_score = self._get_min_score_for_length(s['length'])
                            new_state.domains[s_id] = [
                                w for w, _ in self.pattern_matcher.find(pattern, min_score=min_score)
                            ]

                # Apply MAC propagation
                success, reduced, conflicts = self._mac_propagate(
                    slot, word, new_state, new_state.domains
                )

                if not success:
                    # MAC detected conflict - skip this candidate
                    total_skipped_viability += 1
                    if hasattr(self, 'debug_mac') and self.debug_mac:
                        print(f"DEBUG MAC: Pruned {word} due to domain wipeout in {conflicts}")
                    continue

                # Track reductions for potential backtracking
                if not hasattr(new_state, 'domain_reductions'):
                    new_state.domain_reductions = {}
                new_state.domain_reductions[slot_id] = reduced

                # Check viability with PREDICTIVE RISK ASSESSMENT
                # Now enhanced with domain information from MAC
                is_viable, risk_penalty = self._evaluate_state_viability(new_state, slot)

                if is_viable:
                    # Apply risk penalty to score (discourages risky paths)
                    new_state.score *= risk_penalty
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

    def _evaluate_state_viability(self, state: BeamState, last_filled_slot: Dict = None) -> Tuple[bool, float]:
        """
        Check viability with PREDICTIVE RISK ASSESSMENT.

        CRITICAL FIX (Phase 1.4 - Research Gap #4):
        Go beyond binary viability (possible/impossible) to assess risk level.

        Previous bug: Only checked if count == 0 (dead end)
        Problem: Doesn't detect risky states with only 1-2 candidates
        Result: Algorithm commits to paths that fail 2-3 slots later

        Enhancement: Return risk penalty based on candidate counts:
        - 0 candidates: Dead end (return False)
        - 1-2 candidates: Severe risk (0.70× score penalty)
        - 3-4 candidates: High risk (0.85× score penalty)
        - 5-9 candidates: Medium risk (0.95× score penalty)
        - 10+ candidates: No penalty (1.0×)

        Research (Ginsberg 1990): "Look-ahead is critical"

        OPTIMIZATION: Only checks intersecting slots for efficiency.

        Args:
            state: Beam state to check
            last_filled_slot: The slot we just filled (optional)

        Returns:
            (is_viable, risk_penalty) tuple where:
            - is_viable: True if no dead ends
            - risk_penalty: Multiplier ∈ [0.70, 1.0] based on risk
        """
        # Get slots to check (only intersecting ones if we have a reference)
        if last_filled_slot:
            slots_to_check = self._get_intersecting_slots(state.grid, last_filled_slot)
        else:
            # No reference - check all (first few slots)
            slots_to_check = state.grid.get_empty_slots()

        # Initialize penalty (no penalty = 1.0)
        total_penalty = 1.0
        risky_slots = 0

        # DEBUG: Track viability check details
        if hasattr(state, '_debug_viability_count'):
            state._debug_viability_count += 1
        else:
            state._debug_viability_count = 0

        if state._debug_viability_count < 2:
            print(f"\nDEBUG VIABILITY: Checking {len(slots_to_check)} intersecting slots")

        # Check each slot and assess risk
        for slot in slots_to_check:
            pattern = state.grid.get_pattern_for_slot(slot)

            # Use length-dependent quality threshold
            min_score = self._get_min_score_for_length(slot['length'])

            # Get candidates (excluding used words)
            candidates = self.pattern_matcher.find(
                pattern,
                min_score=min_score
            )

            # Filter out used words
            available_candidates = [
                (word, score) for word, score in candidates
                if word not in state.used_words
            ]

            count = len(available_candidates)

            # PREDICTIVE RISK ASSESSMENT
            if count == 0:
                # Dead end - not viable
                if state._debug_viability_count < 2:
                    print(f"  DEAD END: slot at ({slot['row']},{slot['col']}) {slot['direction']} length={slot['length']}")
                    print(f"    Pattern: '{pattern}'")
                    print(f"    Total candidates: {len(candidates)}, Available (not used): 0")
                return (False, 0.0)
            elif count <= 2:
                # Severe risk: Very few options
                total_penalty *= 0.70
                risky_slots += 1
            elif count <= 4:
                # High risk: Limited options
                total_penalty *= 0.85
                risky_slots += 1
            elif count <= 9:
                # Medium risk: Some constraint
                total_penalty *= 0.95
            # 10+ candidates: No penalty (comfortable margin)

        if state._debug_viability_count < 2:
            if risky_slots > 0:
                print(f"  ✓ Viable, but {risky_slots} risky slots (penalty: {total_penalty:.2f}×)")
            else:
                print(f"  ✓ All {len(slots_to_check)} intersecting slots have good options!")

        return (True, total_penalty)

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

    def _is_gibberish_pattern(self, pattern: str) -> bool:
        """
        Check if a pattern contains obvious gibberish (repeated letters, impossible clusters).

        Args:
            pattern: Word or pattern to check (may contain '?' wildcards)

        Returns:
            True if pattern appears to be gibberish

        Examples:
            AAAAA → True (all same letter)
            AAA → True (all same letter)
            NNN → True (all same letter)
            BRNNN → True (impossible consonant cluster + repeated N)
            DRAMA → False (valid word pattern)
            D?AMA → False (partial valid pattern)
        """
        # Remove wildcards for checking
        letters_only = pattern.replace('?', '')

        if not letters_only or len(letters_only) < 3:
            return False  # Too short to be obviously gibberish

        # Check for 3+ repeated letters in a row
        for i in range(len(letters_only) - 2):
            if letters_only[i] == letters_only[i+1] == letters_only[i+2]:
                return True  # AAA, NNN, etc.

        # Check if entire pattern is same letter
        if len(set(letters_only)) == 1:
            return True  # AAAAA, NNN, etc.

        # Check for impossible consonant clusters (4+ consonants)
        vowels = set('AEIOUY')
        consonant_run = 0
        for char in letters_only:
            if char not in vowels:
                consonant_run += 1
                if consonant_run >= 4:
                    return True  # BRNNN, STRNG, etc.
            else:
                consonant_run = 0

        return False
