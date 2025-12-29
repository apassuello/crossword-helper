"""
State evaluation and scoring for beam search.

This module implements strategies for evaluating beam states,
including viability assessment, quality checks, and score computation.
"""

from typing import Tuple, Dict, Optional
from abc import ABC, abstractmethod
import logging
import itertools

from ..state import BeamState

logger = logging.getLogger(__name__)


class StateEvaluationStrategy(ABC):
    """Abstract base class for state evaluation strategies."""

    @abstractmethod
    def evaluate_state_viability(
        self,
        state: BeamState,
        last_filled_slot: Optional[Dict] = None
    ) -> Tuple[bool, float]:
        """
        Check viability and assess risk level.

        Returns:
            Tuple of (is_viable, risk_penalty)
        """

    @abstractmethod
    def compute_score(self, state: BeamState, word_score: int) -> float:
        """
        Compute quality score for a state.

        Returns:
            Score in range 0.0-100.0
        """


class StateEvaluator(StateEvaluationStrategy):
    """
    State evaluation for beam search.

    Evaluates beam states for viability, quality, and risk assessment.
    Includes gibberish detection and predictive risk analysis.
    """

    def __init__(
        self,
        pattern_matcher,
        get_min_score_func,
        get_intersecting_slots_func
    ):
        """
        Initialize state evaluator.

        Args:
            pattern_matcher: Pattern matching utility for finding valid words
            get_min_score_func: Function to get minimum score for a given length
            get_intersecting_slots_func: Function to get slots intersecting a reference slot
        """
        self.pattern_matcher = pattern_matcher
        self.get_min_score = get_min_score_func
        self.get_intersecting_slots = get_intersecting_slots_func

    def evaluate_state_viability(
        self,
        state: BeamState,
        last_filled_slot: Optional[Dict] = None
    ) -> Tuple[bool, float]:
        """
        Check viability with PREDICTIVE RISK ASSESSMENT.

        CRITICAL FIX (Phase 1.4 - Research Gap #4):
        Go beyond binary viability (possible/impossible) to assess risk level.

        Previous bug: Only checked if count == 0 (dead end)
        Problem: Doesn't detect risky states with only 1-2 candidates
        Result: Algorithm commits to paths that fail 2-3 slots later

        Enhancement: Return risk penalty based on candidate counts:
        - 0 candidates: Dead end (return False)
        - 1-2 candidates: Severe risk (0.70x score penalty)
        - 3-4 candidates: High risk (0.85x score penalty)
        - 5-9 candidates: Medium risk (0.95x score penalty)
        - 10+ candidates: No penalty (1.0x)

        Research (Ginsberg 1990): "Look-ahead is critical"

        OPTIMIZATION: Only checks intersecting slots for efficiency.

        Args:
            state: Beam state to check
            last_filled_slot: The slot we just filled (optional)

        Returns:
            (is_viable, risk_penalty) tuple where:
            - is_viable: True if no dead ends
            - risk_penalty: Multiplier  [0.70, 1.0] based on risk
        """
        # Get slots to check (only intersecting ones if we have a reference)
        if last_filled_slot:
            slots_to_check = self.get_intersecting_slots(state.grid, last_filled_slot)
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
            logger.debug(f"\nDEBUG VIABILITY: Checking {len(slots_to_check)} intersecting slots")

        # Check each slot and assess risk
        for slot in slots_to_check:
            pattern = state.grid.get_pattern_for_slot(slot)

            # Use length-dependent quality threshold
            min_score = self.get_min_score(slot['length'])

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
                    logger.debug(f"  DEAD END: slot at ({slot['row']},{slot['col']}) {slot['direction']} length={slot['length']}")
                    logger.debug(f"    Pattern: '{pattern}'")
                    logger.debug(f"    Total candidates: {len(candidates)}, Available (not used): 0")
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
                logger.debug(f"   Viable, but {risky_slots} risky slots (penalty: {total_penalty:.2f}x)")
            else:
                logger.debug(f"   All {len(slots_to_check)} intersecting slots have good options!")

        return (True, total_penalty)

    def compute_score(
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

    def is_quality_word(self, word: str) -> bool:
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

    def is_gibberish_pattern(self, pattern: str) -> bool:
        """
        Check if a pattern contains obvious gibberish (repeated letters, impossible clusters).

        Args:
            pattern: Word or pattern to check (may contain '?' wildcards)

        Returns:
            True if pattern appears to be gibberish

        Examples:
            AAAAA x True (all same letter)
            AAA x True (all same letter)
            NNN x True (all same letter)
            BRNNN x True (impossible consonant cluster + repeated N)
            DRAMA x False (valid word pattern)
            D?AMA x False (partial valid pattern)
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
