"""
Aho-Corasick based pattern matcher for crossword autofill.

Uses the pyahocorasick library for ultra-fast pattern matching with wildcards.
This is the fastest option for crossword pattern matching, especially when
doing multiple pattern queries.

Performance comparison (454k word list):
- Regex (PatternMatcher): 200-500ms per query
- Trie (TriePatternMatcher): 10-50ms per query
- Aho-Corasick (AhoCorasickMatcher): 1-20ms per query with caching

The Aho-Corasick algorithm builds an automaton that allows O(n+m+z) pattern
matching where n=text length, m=pattern length, z=number of matches.

For crossword patterns with wildcards, we use pyahocorasick's built-in
wildcard support with the MATCH_EXACT_LENGTH flag.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time

try:
    import ahocorasick
    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False
    ahocorasick = None

from .word_list import WordList, ScoredWord


@dataclass
class MatcherStats:
    """Statistics for the Aho-Corasick matcher."""
    build_time_ms: float
    total_words: int
    automaton_count: int
    query_count: int
    cache_hits: int
    cache_misses: int
    avg_query_time_ms: float


class AhoCorasickMatcher:
    """
    Ultra-fast pattern matcher using Aho-Corasick algorithm.

    This matcher builds separate automata for each word length (3-21),
    allowing very fast wildcard pattern matching using pyahocorasick's
    native wildcard support.

    Features:
    - 10-100x faster than regex for pattern matching
    - Native wildcard support (? or . for any single letter)
    - Automatic caching of query results
    - Score-based filtering and sorting
    - Memory-efficient for large wordlists

    Requirements:
    - pyahocorasick library: pip install pyahocorasick

    Example:
        >>> from word_list import WordList
        >>> wl = WordList.from_file("words.txt")
        >>> matcher = AhoCorasickMatcher(wl)
        >>> matcher.find("?I?A")
        [('VISA', 85), ('DIVA', 80), ('PITA', 75)]
    """

    def __init__(self, word_list: WordList, build_progress_callback=None):
        """
        Initialize matcher with word list.

        Builds Aho-Corasick automata for each word length (one-time cost).

        Args:
            word_list: WordList object containing scored words
            build_progress_callback: Optional callback(current, total, message)

        Build Time: O(n * m) where n = num words, m = avg length
        - 10k words: ~100ms
        - 100k words: ~400ms
        - 454k words: ~1.5 seconds

        Raises:
            ImportError: If pyahocorasick is not installed
        """
        if not AHOCORASICK_AVAILABLE:
            raise ImportError(
                "pyahocorasick is required for AhoCorasickMatcher. "
                "Install with: pip install pyahocorasick"
            )

        self.word_list = word_list
        self._automata: Dict[int, ahocorasick.Automaton] = {}
        self._words_by_length: Dict[int, Dict[str, ScoredWord]] = {}
        self._pattern_cache: Dict[str, List[Tuple[str, int]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._query_count = 0
        self._total_query_time_ms = 0.0

        start_time = time.time()
        self._build_automata(build_progress_callback)
        self._build_time_ms = (time.time() - start_time) * 1000

    def _build_automata(self, progress_callback=None) -> None:
        """
        Build Aho-Corasick automata for each word length.

        Creates separate automata for lengths 3-21, each containing
        all words of that length. This allows efficient pattern matching
        when the pattern length is known.
        """
        # Group words by length
        words_by_length: Dict[int, List[ScoredWord]] = {}

        for word in self.word_list.words:
            length = word.length
            if length not in words_by_length:
                words_by_length[length] = []
            words_by_length[length].append(word)

        total_lengths = len(words_by_length)
        processed = 0

        # Build automaton for each length
        for length, words in sorted(words_by_length.items()):
            if progress_callback:
                progress_callback(processed, total_lengths, f"Building automaton for {length}-letter words...")

            # Create automaton
            automaton = ahocorasick.Automaton()

            # Create word lookup dict
            self._words_by_length[length] = {}

            for word in words:
                # Store word with its index as value
                automaton.add_word(word.text, (word.text, word.score))
                self._words_by_length[length][word.text] = word

            # Finalize automaton (required before searching)
            automaton.make_automaton()
            self._automata[length] = automaton

            processed += 1

        if progress_callback:
            progress_callback(total_lengths, total_lengths, "Build complete")

    def find(
        self,
        pattern: str,
        min_score: int = 30,
        max_results: Optional[int] = None,
        progress_callback=None
    ) -> List[Tuple[str, int]]:
        """
        Find words matching pattern with wildcards.

        Args:
            pattern: Pattern string (e.g., "?I?A" or ".I.A")
                     ? or . matches any single letter
                     Letters match themselves (case-insensitive)
            min_score: Minimum crossword-ability score (0-100)
            max_results: Maximum number of results (None = unlimited)
            progress_callback: Optional callback for progress updates

        Returns:
            List of (word, score) tuples, sorted by score descending

        Performance:
            - Cached queries: O(1)
            - Uncached with no wildcards: O(1)
            - Uncached with wildcards: O(26^w * m) where w=wildcards, m=avg matches
            - Typical crossword query: 1-20ms
        """
        start_time = time.time()
        self._query_count += 1

        # Normalize pattern
        pattern = pattern.upper().replace('.', '?')
        length = len(pattern)

        # Check cache
        cache_key = f"{pattern}:{min_score}:{max_results}"
        if cache_key in self._pattern_cache:
            self._cache_hits += 1
            return self._pattern_cache[cache_key]

        self._cache_misses += 1

        # Check if we have an automaton for this length
        if length not in self._automata:
            return []

        automaton = self._automata[length]
        results: List[Tuple[str, int]] = []

        # Check if pattern has wildcards
        if '?' in pattern:
            # Use pyahocorasick's wildcard matching
            # keys() with wildcard returns matching words
            try:
                for word in automaton.keys(pattern, '?', ahocorasick.MATCH_EXACT_LENGTH):
                    word_obj = self._words_by_length[length].get(word)
                    if word_obj and word_obj.score >= min_score:
                        results.append((word, word_obj.score))
            except (TypeError, AttributeError):
                # Fallback for older pyahocorasick versions without wildcard support
                results = self._fallback_wildcard_match(pattern, min_score)
        else:
            # Exact match - check if word exists
            if pattern in self._words_by_length.get(length, {}):
                word_obj = self._words_by_length[length][pattern]
                if word_obj.score >= min_score:
                    results.append((pattern, word_obj.score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        if max_results is not None and len(results) > max_results:
            results = results[:max_results]

        # Update timing stats
        query_time = (time.time() - start_time) * 1000
        self._total_query_time_ms += query_time

        # Cache result (limit cache size)
        if len(self._pattern_cache) < 10000:
            self._pattern_cache[cache_key] = results

        return results

    def _fallback_wildcard_match(
        self,
        pattern: str,
        min_score: int
    ) -> List[Tuple[str, int]]:
        """
        Fallback wildcard matching for older pyahocorasick versions.

        Uses brute-force matching against all words of the pattern length.
        """
        length = len(pattern)
        results = []

        if length not in self._words_by_length:
            return results

        # Convert pattern to a matcher function
        def matches(word: str) -> bool:
            if len(word) != len(pattern):
                return False
            for p, w in zip(pattern, word):
                if p != '?' and p != w:
                    return False
            return True

        for word, word_obj in self._words_by_length[length].items():
            if word_obj.score >= min_score and matches(word):
                results.append((word, word_obj.score))

        return results

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
        return len(self.find(pattern, min_score=min_score, max_results=None))

    def get_best_match(self, pattern: str) -> Tuple[Optional[str], int]:
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
        return len(self.find(pattern, min_score=min_score, max_results=1)) > 0

    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self._pattern_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_stats(self) -> MatcherStats:
        """
        Get performance statistics.

        Returns:
            MatcherStats object with all metrics
        """
        avg_query_time = 0.0
        if self._query_count > 0:
            avg_query_time = self._total_query_time_ms / self._query_count

        return MatcherStats(
            build_time_ms=self._build_time_ms,
            total_words=len(self.word_list),
            automaton_count=len(self._automata),
            query_count=self._query_count,
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            avg_query_time_ms=avg_query_time
        )

    def get_performance_report(self) -> str:
        """
        Get formatted performance report.

        Returns:
            Multi-line string with all statistics
        """
        stats = self.get_stats()
        total_queries = stats.cache_hits + stats.cache_misses
        hit_rate = stats.cache_hits / total_queries if total_queries > 0 else 0

        report = []
        report.append("=== AhoCorasickMatcher Performance Report ===")
        report.append("")
        report.append("Build Statistics:")
        report.append(f"  Build time: {stats.build_time_ms:.1f}ms")
        report.append(f"  Total words: {stats.total_words:,}")
        report.append(f"  Automata count: {stats.automaton_count} (one per word length)")
        report.append("")
        report.append("Query Statistics:")
        report.append(f"  Total queries: {stats.query_count}")
        report.append(f"  Cache hits: {stats.cache_hits}")
        report.append(f"  Cache misses: {stats.cache_misses}")
        report.append(f"  Cache hit rate: {hit_rate:.1%}")
        report.append(f"  Avg query time: {stats.avg_query_time_ms:.2f}ms")
        report.append("")
        report.append("Length Distribution:")

        for length in sorted(self._automata.keys()):
            count = len(self._words_by_length.get(length, {}))
            report.append(f"  {length}-letter words: {count:,}")

        report.append("")
        return "\n".join(report)

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            "AhoCorasickMatcher("
            f"words={stats.total_words:,}, "
            f"automata={stats.automaton_count}, "
            f"build_time={stats.build_time_ms:.0f}ms"
            ")"
        )


def is_available() -> bool:
    """Check if pyahocorasick is available."""
    return AHOCORASICK_AVAILABLE


def create_matcher(word_list: WordList, progress_callback=None):
    """
    Factory function to create the best available matcher.

    Returns AhoCorasickMatcher if pyahocorasick is available,
    otherwise falls back to TriePatternMatcher.

    Args:
        word_list: WordList object
        progress_callback: Optional progress callback

    Returns:
        Either AhoCorasickMatcher or TriePatternMatcher
    """
    if AHOCORASICK_AVAILABLE:
        return AhoCorasickMatcher(word_list, progress_callback)
    else:
        from .trie_pattern_matcher import TriePatternMatcher
        return TriePatternMatcher(word_list)
