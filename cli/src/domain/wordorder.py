"""
Canonical word order for a WordList.

Defines the single source of truth for the per-length word ordering that
the letter-bitset index in this package, and a later id-space counterpart,
build their word ids from: a word's id is its position in the tuple
returned here for its length.
"""

from __future__ import annotations

from collections import defaultdict

from src.fill.word_list import ScoredWord, WordList


def canonical_words(word_list: WordList) -> dict[int, tuple[ScoredWord, ...]]:
    """
    Group and order a WordList's words by length for canonical id assignment.

    Within a length, words are ordered by score descending, then text
    ascending; a word's id is its position in the returned tuple. This
    reads word_list.words directly and sorts a copy of it — it does not
    delegate to WordList.get_by_length, which sorts by score alone and
    leaves equal-scored words in insertion order.

    Args:
        word_list: Source WordList.

    Returns:
        Mapping from word length to an ordered tuple of ScoredWord. A
        length with no words in word_list has no key; an empty WordList
        returns an empty dict.
    """
    by_length: dict[int, list[ScoredWord]] = defaultdict(list)
    for word in word_list.words:
        by_length[word.length].append(word)

    return {length: tuple(sorted(words, key=lambda w: (-w.score, w.text))) for length, words in by_length.items()}
