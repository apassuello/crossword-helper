"""
Trie-based pattern matcher for crossword autofill.

Drop-in replacement for PatternMatcher that uses WordTrie instead of regex
for 10-50x faster pattern matching with large word lists.

API-compatible with pattern_matcher.PatternMatcher for easy switching.
"""

from typing import List, Tuple, Dict, Optional
from .word_list import WordList
from .word_trie import build_trie_from_wordlist


class TriePatternMatcher:
    """
    Fast pattern matching using trie data structure.

    Provides same API as PatternMatcher but uses WordTrie instead of regex
    for significantly faster performance on large word lists.

    Performance comparison (454k word list):
    - Regex (PatternMatcher): 200-500ms per query
    - Trie (TriePatternMatcher): 10-50ms per query
    - **Speedup: 10-50x**

    Supports wildcards:
    - '?' matches any single letter
    - '.' matches any single letter (converted to '?')
    - Specific letters match themselves

    Examples:
        >>> matcher = TriePatternMatcher(word_list)
        >>> matcher.find("?I?A")
        [('VISA', 85), ('PITA', 80), ('DIVA', 75)]
    """

    def __init__(self, word_list: WordList):
        """
        Initialize matcher with word list.

        Builds trie on initialization (one-time cost).

        Args:
            word_list: WordList object containing scored words

        Build Time: O(n * m) where n = num words, m = avg length
        - 10k words: ~50ms
        - 100k words: ~500ms
        - 454k words: ~2-3 seconds
        """
        self.word_list = word_list
        self.trie = build_trie_from_wordlist(word_list)
        self._pattern_cache: Dict[str, List[Tuple[str, int]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def find(
        self,
        pattern: str,
        min_score: int = 30,
        max_results: Optional[int] = None,
        progress_callback=None
    ) -> List[Tuple[str, int]]:
        """
        Find words matching pattern.

        Args:
            pattern: Pattern string (e.g., "?I?A" or ".I.A")
            min_score: Minimum crossword-ability score
            max_results: Maximum number of results (None = unlimited)
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of (word, score) tuples, sorted by score descending

        Time Complexity:
        - Best case (cached): O(1)
        - Best case (no wildcards): O(m)
        - Worst case (all wildcards): O(26^m) but pruned by min_score
        - Typical case: O(m * w) where w = wildcard count

        Example:
            >>> matcher.find("?I?A")
            [('VISA', 85), ('PITA', 80), ('DIVA', 75), ('RITA', 70)]
        """
        # Normalize pattern (convert . to ?)
        pattern = pattern.upper().replace('.', '?')

        # Check cache
        cache_key = f"{pattern}:{min_score}:{max_results}"
        if cache_key in self._pattern_cache:
            self._cache_hits += 1
            return self._pattern_cache[cache_key]

        self._cache_misses += 1

        # Use trie to find matches
        matches = self.trie.find_pattern(pattern, min_score, max_results, progress_callback)

        # Convert to (word, score) tuples
        result = [(word.text, word.score) for word in matches]

        # Cache result (limit cache size to prevent memory bloat)
        if len(self._pattern_cache) < 10000:
            self._pattern_cache[cache_key] = result

        return result

    def find_all_matching(self, pattern: str) -> List[Tuple[str, int]]:
        """
        Find all words matching pattern (no score or result limit).

        Args:
            pattern: Pattern string

        Returns:
            All matching words with scores
        """
        return self.find(pattern, min_score=0, max_results=None)

    def count_matches(self, pattern: str, min_score: int = 30) -> int:
        """
        Count words matching pattern.

        Args:
            pattern: Pattern string
            min_score: Minimum score

        Returns:
            Number of matching words
        """
        pattern = pattern.upper().replace('.', '?')
        return self.trie.count_matches(pattern, min_score)

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
        pattern = pattern.upper().replace('.', '?')
        return self.trie.has_matches(pattern, min_score)

    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self._pattern_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache metrics
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0

        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'total_queries': total,
            'hit_rate': f"{hit_rate:.1%}",
            'cache_size': len(self._pattern_cache)
        }

    def get_trie_stats(self) -> Dict[str, any]:
        """
        Get trie structure statistics.

        Returns:
            Dictionary with trie metrics
        """
        return self.trie.get_stats()

    def get_performance_report(self) -> str:
        """
        Get formatted performance report.

        Returns:
            Multi-line string with cache and trie statistics
        """
        cache_stats = self.get_cache_stats()
        trie_stats = self.get_trie_stats()

        report = []
        report.append("=== TriePatternMatcher Performance Report ===")
        report.append("")
        report.append("Cache Statistics:")
        report.append(f"  Total queries: {cache_stats['total_queries']}")
        report.append(f"  Cache hits: {cache_stats['hits']}")
        report.append(f"  Cache misses: {cache_stats['misses']}")
        report.append(f"  Hit rate: {cache_stats['hit_rate']}")
        report.append(f"  Cache size: {cache_stats['cache_size']} patterns")
        report.append("")
        report.append("Trie Statistics:")
        report.append(f"  Total words: {trie_stats['total_words']}")
        report.append(f"  Total nodes: {trie_stats['total_nodes']}")
        report.append(f"  Length tries: {trie_stats['num_length_tries']}")
        report.append(f"  Avg nodes/word: {trie_stats['avg_nodes_per_word']:.1f}")
        report.append(f"  Length ranges: {trie_stats['length_ranges']}")
        report.append("")

        return "\n".join(report)

    def __repr__(self) -> str:
        """String representation."""
        cache_stats = self.get_cache_stats()
        return (
            "TriePatternMatcher("
            f"words={len(self.word_list)}, "
            f"cache_size={cache_stats['cache_size']}, "
            f"hit_rate={cache_stats['hit_rate']}"
            ")"
        )
