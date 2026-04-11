"""
Trie data structure for fast pattern matching in crossword autofill.

Provides O(m) pattern lookup where m = pattern length, compared to O(n)
linear search. Particularly effective for large word lists (100k+ words).

Key optimizations:
- Length-indexed tries (separate trie per word length)
- Score filtering during traversal (prune low-scoring branches early)
- Wildcard support with early termination
"""

from typing import Dict, List, Optional

from .word_list import ScoredWord


class TrieNode:
    """
    Node in the trie structure.

    Each node represents a character position in words. Leaf nodes
    (where is_end_of_word=True) contain the actual words ending there.
    """

    def __init__(self):
        self.children: Dict[str, TrieNode] = {}  # char -> child node
        self.words: List[ScoredWord] = []  # Words ending at this node
        self.is_end_of_word: bool = False
        self.min_score: float = float("inf")  # Minimum score in subtree (for pruning)
        self.max_score: int = 0  # Maximum score in subtree (for pruning)

    def __repr__(self) -> str:
        return f"TrieNode(children={len(self.children)}, words={len(self.words)})"


class WordTrie:
    """
    Trie optimized for crossword pattern matching.

    Features:
    - Separate trie for each word length (reduces search space)
    - Score-based pruning (skip branches below min_score threshold)
    - Wildcard support (? matches any letter)
    - Cache-friendly traversal

    Example:
        >>> trie = WordTrie()
        >>> trie.add_word(ScoredWord("CAT", 85, 3))
        >>> trie.add_word(ScoredWord("COT", 80, 3))
        >>> results = trie.find_pattern("C?T", min_score=70)
        >>> [w.text for w in results]
        ['CAT', 'COT']
    """

    def __init__(self):
        """Initialize empty trie with length-based indexing."""
        # Separate root for each word length (3-21 letters)
        self._length_roots: Dict[int, TrieNode] = {}
        self._word_count = 0
        self._total_nodes = 0

    def add_word(self, word: ScoredWord) -> None:
        """
        Add word to the trie.

        Args:
            word: ScoredWord object to add

        Time Complexity: O(m) where m = word length
        """
        length = word.length

        # Create root for this length if needed
        if length not in self._length_roots:
            self._length_roots[length] = TrieNode()

        # Insert word into trie
        node = self._length_roots[length]

        # Update root's score bounds (fix for pruning bug)
        node.min_score = min(node.min_score, word.score)
        node.max_score = max(node.max_score, word.score)

        for char in word.text:
            if char not in node.children:
                node.children[char] = TrieNode()
                self._total_nodes += 1

            node = node.children[char]

            # Update score bounds for pruning
            node.min_score = min(node.min_score, word.score)
            node.max_score = max(node.max_score, word.score)

        # Mark end of word and store it
        node.is_end_of_word = True
        node.words.append(word)
        self._word_count += 1

    def add_words(self, words: List[ScoredWord]) -> None:
        """
        Add multiple words to trie.

        Args:
            words: List of ScoredWord objects
        """
        for word in words:
            self.add_word(word)

    def find_pattern(
        self,
        pattern: str,
        min_score: int = 0,
        max_results: Optional[int] = None,
        progress_callback=None,
    ) -> List[ScoredWord]:
        """
        Find all words matching a pattern.

        Supports wildcards:
        - '?' matches any single letter
        - Specific letters match themselves

        Args:
            pattern: Pattern string (e.g., "C?T", "RE??")
            min_score: Minimum word score to include
            max_results: Maximum number of results (None = unlimited)
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of matching ScoredWord objects, sorted by score (descending)

        Time Complexity:
        - Best case (no wildcards): O(m) where m = pattern length
        - Worst case (all wildcards): O(26^m) but pruned by min_score
        - Typical case: O(m * w) where w = wildcards count

        Example:
            >>> trie.find_pattern("?AT", min_score=70)
            [ScoredWord('CAT', 85), ScoredWord('BAT', 80), ScoredWord('RAT', 75)]
        """
        pattern = pattern.upper()
        length = len(pattern)

        # Check if we have a trie for this length
        if length not in self._length_roots:
            return []

        # Estimate total nodes to search (rough approximation for progress)
        wildcard_count = pattern.count("?")
        estimated_total = max(1, 26 ** min(wildcard_count, 3))  # Cap estimate at 3 wildcards

        # Search trie recursively
        results = []
        progress_state = {"nodes_visited": 0}

        self._search_trie(
            node=self._length_roots[length],
            pattern=pattern,
            index=0,
            min_score=min_score,
            results=results,
            max_results=max_results,
            progress_callback=progress_callback,
            progress_state=progress_state,
            estimated_total=estimated_total,
        )

        # Sort by score (descending)
        results.sort(key=lambda w: w.score, reverse=True)

        # Limit results if requested
        if max_results is not None:
            results = results[:max_results]

        return results

    def _search_trie(
        self,
        node: TrieNode,
        pattern: str,
        index: int,
        min_score: int,
        results: List[ScoredWord],
        max_results: Optional[int],
        progress_callback=None,
        progress_state=None,
        estimated_total=1,
    ) -> None:
        """
        Recursive trie search with wildcard support and pruning.

        Args:
            node: Current trie node
            pattern: Full pattern string
            index: Current position in pattern
            min_score: Minimum score threshold
            results: Accumulator for matching words
            max_results: Stop after finding this many results
            progress_callback: Optional callback for progress updates
            progress_state: Dict tracking nodes_visited
            estimated_total: Estimated total nodes to search
        """
        # Track visited nodes for progress
        if progress_state is not None:
            progress_state["nodes_visited"] += 1

            # Report progress every 100 nodes
            if progress_callback and progress_state["nodes_visited"] % 100 == 0:
                progress_callback(
                    min(progress_state["nodes_visited"], estimated_total),
                    estimated_total,
                )

        # Early exit if we have enough results
        if max_results is not None and len(results) >= max_results:
            return

        # Prune: If this subtree's max score is below threshold, skip it
        if node.max_score < min_score:
            return

        # Base case: We've matched the entire pattern
        if index == len(pattern):
            if node.is_end_of_word:
                # Add all words at this node that meet score threshold
                for word in node.words:
                    if word.score >= min_score:
                        results.append(word)

                        # Early exit if we have enough
                        if max_results is not None and len(results) >= max_results:
                            return
            return

        char = pattern[index]

        if char == "?":
            # Wildcard: Try all children
            for child_char, child_node in node.children.items():
                self._search_trie(
                    child_node,
                    pattern,
                    index + 1,
                    min_score,
                    results,
                    max_results,
                    progress_callback,
                    progress_state,
                    estimated_total,
                )

                # Early exit if we have enough results
                if max_results is not None and len(results) >= max_results:
                    return
        else:
            # Specific letter: Follow single path
            if char in node.children:
                self._search_trie(
                    node.children[char],
                    pattern,
                    index + 1,
                    min_score,
                    results,
                    max_results,
                    progress_callback,
                    progress_state,
                    estimated_total,
                )

    def count_matches(self, pattern: str, min_score: int = 0) -> int:
        """
        Count words matching pattern without returning them.

        Args:
            pattern: Pattern string
            min_score: Minimum score threshold

        Returns:
            Number of matching words

        Note: Slightly faster than len(find_pattern(...)) because
        it doesn't need to sort or copy results.
        """
        results = self.find_pattern(pattern, min_score, max_results=None)
        return len(results)

    def has_matches(self, pattern: str, min_score: int = 0) -> bool:
        """
        Check if any words match pattern.

        Args:
            pattern: Pattern string
            min_score: Minimum score threshold

        Returns:
            True if at least one word matches

        Note: Much faster than count_matches() because it stops after
        finding the first match.
        """
        results = self.find_pattern(pattern, min_score, max_results=1)
        return len(results) > 0

    def get_stats(self) -> Dict[str, any]:
        """
        Get trie statistics.

        Returns:
            Dictionary with trie metrics
        """
        return {
            "total_words": self._word_count,
            "total_nodes": self._total_nodes,
            "length_ranges": sorted(self._length_roots.keys()),
            "num_length_tries": len(self._length_roots),
            "avg_nodes_per_word": (self._total_nodes / self._word_count if self._word_count > 0 else 0),
        }

    def __len__(self) -> int:
        """Return total number of words in trie."""
        return self._word_count

    def __repr__(self) -> str:
        """String representation."""
        return f"WordTrie(words={self._word_count}, nodes={self._total_nodes})"


def build_trie_from_wordlist(word_list) -> WordTrie:
    """
    Build trie from WordList object.

    Args:
        word_list: WordList object containing ScoredWord objects

    Returns:
        WordTrie populated with all words

    Example:
        >>> from .word_list import WordList
        >>> wl = WordList(['CAT', 'DOG', 'BAT'])
        >>> trie = build_trie_from_wordlist(wl)
        >>> len(trie)
        3
    """
    trie = WordTrie()
    trie.add_words(word_list.words)
    return trie
