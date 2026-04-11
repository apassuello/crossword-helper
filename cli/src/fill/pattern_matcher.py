"""
Pattern matching for crossword autofill.

Efficiently finds words matching wildcard patterns using regex and indexing.
"""

import re
from typing import Dict, List, Pattern, Tuple

from .word_list import WordList


class PatternMatcher:
    """
    Fast pattern matching for crossword fill.

    Supports wildcards:
    - '?' matches any single letter
    - '.' matches any single letter (alternative notation)
    - Specific letters match themselves

    Examples:
    - "?I?A" matches VISA, PITA, DIVA
    - "RE??" matches READ, REAL, REAP
    """

    def __init__(self, word_list: WordList):
        """
        Initialize matcher with word list.

        Args:
            word_list: WordList object containing scored words
        """
        self.word_list = word_list
        self._pattern_cache: Dict[str, List[Tuple[str, int]]] = {}

    def find(
        self,
        pattern: str,
        min_score: int = 30,
        max_results: int = 100,
        progress_callback=None,
    ) -> List[Tuple[str, int]]:
        """
        Find words matching pattern.

        Args:
            pattern: Pattern string (e.g., "?I?A" or ".I.A")
            min_score: Minimum crossword-ability score
            max_results: Maximum number of results
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of (word, score) tuples, sorted by score descending

        Example:
            >>> matcher.find("?I?A")
            [('VISA', 85), ('PITA', 80), ('DIVA', 75), ('RITA', 70)]
        """
        # Normalize pattern (convert . to ?)
        pattern = pattern.upper().replace(".", "?")

        # Check cache
        cache_key = f"{pattern}:{min_score}:{max_results}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        # Get pattern length
        length = len(pattern)

        # Get words of matching length
        candidate_words = self.word_list.get_by_length(length, min_score)
        total_words = len(candidate_words)

        # Convert pattern to regex
        regex = self._pattern_to_regex(pattern)

        # Filter by pattern match
        matches = []
        for idx, word in enumerate(candidate_words):
            if regex.match(word.text):
                matches.append((word.text, word.score))

            # Report progress every 1000 words
            if progress_callback and idx % 1000 == 0:
                progress_callback(idx, total_words)

            # Stop if we have enough high-scoring matches
            if len(matches) >= max_results:
                break

        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Cache result
        self._pattern_cache[cache_key] = matches

        return matches

    def find_all_matching(self, pattern: str) -> List[Tuple[str, int]]:
        """
        Find all words matching pattern (no score or result limit).

        Args:
            pattern: Pattern string

        Returns:
            All matching words with scores
        """
        return self.find(pattern, min_score=0, max_results=float("inf"))

    def count_matches(self, pattern: str, min_score: int = 30) -> int:
        """
        Count words matching pattern.

        Args:
            pattern: Pattern string
            min_score: Minimum score

        Returns:
            Number of matching words
        """
        return len(self.find(pattern, min_score=min_score, max_results=float("inf")))

    def _pattern_to_regex(self, pattern: str) -> Pattern:
        """
        Convert crossword pattern to regex.

        Args:
            pattern: Pattern with '?' wildcards

        Returns:
            Compiled regex pattern

        Example:
            "?I?A" → "^.I.A$"
        """
        # Escape any special regex characters except ?
        # Then replace ? with .
        regex_str = "^" + pattern.replace("?", ".") + "$"
        return re.compile(regex_str)

    def get_best_match(self, pattern: str) -> Tuple[str, int]:
        """
        Get single best matching word.

        Args:
            pattern: Pattern string

        Returns:
            (word, score) tuple for best match, or (None, 0) if no match
        """
        matches = self.find(pattern, min_score=0, max_results=1)
        if matches:
            return matches[0]
        return (None, 0)

    def has_matches(self, pattern: str, min_score: int = 30) -> bool:
        """
        Check if any words match pattern.

        Args:
            pattern: Pattern string
            min_score: Minimum score

        Returns:
            True if at least one word matches
        """
        return self.count_matches(pattern, min_score) > 0

    def matches_pattern(self, word: str, pattern: str) -> bool:
        """
        Check if a specific word matches a pattern.

        Args:
            word: Word to check (will be uppercased)
            pattern: Pattern string (e.g., "?I?A" or ".I.A")

        Returns:
            True if word matches pattern

        Example:
            >>> matcher.matches_pattern("VISA", "?I?A")
            True
            >>> matcher.matches_pattern("VISA", "?I??A")
            False
        """
        # Normalize both word and pattern
        word = word.upper()
        pattern = pattern.upper().replace(".", "?")

        # Check length first (quick rejection)
        if len(word) != len(pattern):
            return False

        # Convert pattern to regex and check match
        regex = self._pattern_to_regex(pattern)
        return regex.match(word) is not None

    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self._pattern_cache.clear()

    def __repr__(self) -> str:
        """String representation."""
        return f"PatternMatcher(words={len(self.word_list)}, cached_patterns={len(self._pattern_cache)})"
