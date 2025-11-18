"""
Pattern matching engine for crossword word lookups.

This module provides functionality to match partial word patterns (e.g., "?AT?RN")
against wordlists and external APIs like OneLook. Supports wildcards and
known letter positions.
"""

from typing import List, Tuple
from backend.core.scoring import score_word, analyze_letters
from backend.data.wordlist_manager import WordListManager
from backend.data.onelook_client import OneLookClient


class PatternMatcher:
    """Finds words matching crossword patterns and scores them."""

    def __init__(self, wordlist_names: List[str] = None):
        """
        Initialize pattern matcher with word lists.

        Args:
            wordlist_names: List of wordlist file names (e.g., ['personal', 'standard'])
                          If None, uses ['standard']
        """
        self.wordlist_names = wordlist_names or ['standard']
        self.wordlist_manager = WordListManager()
        self.onelook_client = OneLookClient()

    def search(
        self,
        pattern: str,
        max_results: int = 20
    ) -> List[Tuple[str, int, str]]:
        """
        Find words matching pattern.

        Args:
            pattern: Pattern with ? as wildcards (e.g., '?I?A')
            max_results: Maximum number of results to return

        Returns:
            List of (word, score, source) tuples, sorted by score descending

        Raises:
            ValueError: If pattern is invalid (no ?, too long, etc.)
        """
        # Validate pattern format
        self._validate_pattern(pattern)

        # Search OneLook API (gracefully fails to empty list)
        onelook_words = self._search_onelook(pattern)

        # Search local wordlists
        local_words = []
        for wordlist_name in self.wordlist_names:
            try:
                words = self.wordlist_manager.load(wordlist_name)
                matches = self._match_local(pattern, words)
                local_words.extend([(word, wordlist_name) for word in matches])
            except FileNotFoundError:
                # Skip missing wordlists
                continue

        # Merge and score results
        results = self._merge_results(
            onelook_words,
            [word for word, _ in local_words]
        )

        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def _validate_pattern(self, pattern: str) -> None:
        """
        Validate pattern format.

        Rules:
        - Must contain at least one ?
        - Length must be 3-20 characters
        - Must contain only A-Z and ?

        Raises:
            ValueError: With specific message about what's wrong
        """
        if '?' not in pattern:
            raise ValueError("Pattern must contain at least one ? wildcard")

        if len(pattern) < 3 or len(pattern) > 20:
            raise ValueError(f"Pattern length must be 3-20, got {len(pattern)}")

        if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ?' for c in pattern):
            raise ValueError("Pattern must contain only uppercase letters and ?")

    def _match_local(self, pattern: str, words: List[str]) -> List[str]:
        """
        Match pattern against local word list.

        Algorithm:
        1. Filter words by length (must match pattern length)
        2. For each word, check if it matches pattern:
           - ? matches any letter
           - A-Z must match exactly
        3. Return matching words

        Args:
            pattern: Pattern with wildcards
            words: List of words to search

        Returns:
            List of matching words
        """
        matches = []
        pattern_len = len(pattern)

        for word in words:
            if len(word) != pattern_len:
                continue

            if all(
                pattern[i] == '?' or pattern[i] == word[i]
                for i in range(pattern_len)
            ):
                matches.append(word)

        return matches

    def _search_onelook(self, pattern: str) -> List[str]:
        """
        Query OneLook API for matching words.

        Args:
            pattern: Pattern to search

        Returns:
            List of words (empty list on error - graceful degradation)
        """
        return self.onelook_client.search(pattern)

    def _merge_results(
        self,
        onelook_words: List[str],
        local_words: List[str]
    ) -> List[Tuple[str, int, str]]:
        """
        Merge results from OneLook API and local wordlists.

        Args:
            onelook_words: Words from OneLook API
            local_words: Words from local wordlists

        Returns:
            Merged list with (word, score, source) tuples
            - Deduplicates (prefers 'local' over 'onelook')
            - Scores all words
        """
        # Track unique words with their source
        word_sources = {}

        # Add local words first (preferred source)
        for word in local_words:
            if word not in word_sources:
                word_sources[word] = 'local'

        # Add OneLook words (only if not already present)
        for word in onelook_words:
            if word not in word_sources:
                word_sources[word] = 'onelook'

        # Score and return results
        results = [
            (word, score_word(word), source)
            for word, source in word_sources.items()
        ]

        return results
