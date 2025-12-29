"""
Unit tests for WordTrie data structure.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from fill.word_trie import WordTrie, TrieNode
from fill.word_list import ScoredWord


def test_trie_node_creation():
    """Test TrieNode initialization."""
    node = TrieNode()
    assert node.children == {}
    assert node.words == []
    assert node.is_end_of_word  is False
    assert node.min_score == 0
    assert node.max_score == 0


def test_word_trie_initialization():
    """Test WordTrie initialization."""
    trie = WordTrie()
    assert len(trie) == 0
    assert trie._word_count == 0
    assert trie._total_nodes == 0
    assert trie._length_roots == {}


def test_add_single_word():
    """Test adding a single word to trie."""
    trie = WordTrie()
    word = ScoredWord("CAT", 85, 3)
    trie.add_word(word)

    assert len(trie) == 1
    assert 3 in trie._length_roots
    assert trie._word_count == 1


def test_add_multiple_words():
    """Test adding multiple words to trie."""
    trie = WordTrie()
    words = [
        ScoredWord("CAT", 85, 3),
        ScoredWord("DOG", 80, 3),
        ScoredWord("BIRD", 75, 4)
    ]

    for word in words:
        trie.add_word(word)

    assert len(trie) == 3
    assert 3 in trie._length_roots
    assert 4 in trie._length_roots


def test_find_pattern_exact():
    """Test finding words with exact pattern (no wildcards)."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("DOG", 80, 3))

    results = trie.find_pattern("CAT")
    assert len(results) == 1
    assert results[0].text == "CAT"
    assert results[0].score == 85


def test_find_pattern_wildcard():
    """Test finding words with wildcard pattern."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("COT", 80, 3))
    trie.add_word(ScoredWord("CUT", 75, 3))
    trie.add_word(ScoredWord("DOG", 70, 3))

    results = trie.find_pattern("C?T")
    assert len(results) == 3
    words = {r.text for r in results}
    assert words == {"CAT", "COT", "CUT"}


def test_find_pattern_all_wildcards():
    """Test finding words with all wildcards."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("DOG", 80, 3))

    results = trie.find_pattern("???")
    assert len(results) == 2


def test_find_pattern_min_score():
    """Test finding words with minimum score filter."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("COT", 50, 3))
    trie.add_word(ScoredWord("CUT", 30, 3))

    results = trie.find_pattern("C?T", min_score=60)
    assert len(results) == 1
    assert results[0].text == "CAT"


def test_find_pattern_max_results():
    """Test limiting number of results."""
    trie = WordTrie()
    for i in range(10):
        trie.add_word(ScoredWord(f"WOR{i}", 80, 4))

    results = trie.find_pattern("WOR?", max_results=5)
    assert len(results) == 5


def test_find_pattern_sorted_by_score():
    """Test that results are sorted by score descending."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 70, 3))
    trie.add_word(ScoredWord("COT", 90, 3))
    trie.add_word(ScoredWord("CUT", 80, 3))

    results = trie.find_pattern("C?T")
    scores = [r.score for r in results]
    assert scores == [90, 80, 70]


def test_count_matches():
    """Test counting pattern matches."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("COT", 80, 3))
    trie.add_word(ScoredWord("DOG", 75, 3))

    count = trie.count_matches("C?T")
    assert count == 2


def test_has_matches():
    """Test checking if pattern has matches."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))

    assert trie.has_matches("CAT")
    assert trie.has_matches("DOG")  is False
    assert trie.has_matches("C?T")


def test_get_stats():
    """Test getting trie statistics."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))
    trie.add_word(ScoredWord("BIRD", 80, 4))

    stats = trie.get_stats()
    assert stats['total_words'] == 2
    assert stats['num_length_tries'] == 2
    assert 3 in stats['length_ranges']
    assert 4 in stats['length_ranges']


def test_empty_pattern():
    """Test finding with empty pattern."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))

    results = trie.find_pattern("")
    assert len(results) == 0


def test_nonexistent_length():
    """Test finding pattern for length not in trie."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 85, 3))

    results = trie.find_pattern("BIRD")  # 4 letters, only 3-letter words in trie
    assert len(results) == 0
