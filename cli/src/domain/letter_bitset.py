"""
Letter-bitset pattern index over a WordList.

Stores, per word length, a (position, letter, word-chunk) bitset so a pattern
lookup becomes a handful of bitwise ANDs over uint64 rows instead of a trie
walk or a regex rescan. Word order within a length is canonical_words'
(src.domain.wordorder) order: a word's id is its position in that tuple, ids
are grouped into 64-wide chunks, and bit b of chunk w encodes word id
64*w + b at that position/letter.

find/count_matches/has_matches are matcher-compatible with
src.fill.trie_pattern_matcher.TriePatternMatcher on the same WordList: same
normalisation (pattern.upper().replace(".", "?")), same min_score semantics
(scores[L] is non-increasing, so min_score is a searchsorted prefix bound
with side="right" -- a word scoring exactly min_score is kept), and the same
set of (text, score) results when the trie side is queried with
max_results=None. max_results here is true top-N, which TriePatternMatcher's
capped path is not: WordTrie._search_trie exits early in dict-insertion
traversal order and find_pattern only sorts and slices afterwards. See the
differential tests in cli/tests/unit/test_letter_bitset.py for the
equivalence contract this claims.
"""

from __future__ import annotations

import numpy as np
from src.domain.wordorder import canonical_words
from src.fill.word_list import ScoredWord, WordList

_CHUNK_BITS = 64
_FULL_CHUNK_MASK = np.uint64(0xFFFFFFFFFFFFFFFF)


class LetterBitsetIndex:
    """Per-(length, position, letter) bitset index over a WordList's words, for pattern lookup."""

    alphabet: tuple[str, ...]
    letter_index: dict[str, int]

    def __init__(
        self,
        alphabet: tuple[str, ...],
        letter_index: dict[str, int],
        words: dict[int, tuple[ScoredWord, ...]],
        scores: dict[int, np.ndarray],
        bits: dict[int, np.ndarray],
    ) -> None:
        self.alphabet = alphabet
        self.letter_index = letter_index
        self._words = words
        self._scores = scores
        self._bits = bits

    @classmethod
    def from_word_list(cls, word_list: WordList) -> "LetterBitsetIndex":
        """
        Build the index from a WordList.

        Length bounds (3-21) and de-duplication are WordList's own
        validation and are not re-checked here; this only groups, orders and
        bit-packs what WordList already accepted.

        Raises:
            ValueError: if the words collectively use more than 64 distinct
                letters. The cap comes from the domain-capability family's
                spec (docs/superpowers/specs/2026-09-07-domain-capabilities-
                design.md, "Constraints that bind every capability"): the
                spec calls it "an implementation decision, not a research
                finding", not something derived from this class's own
                storage layout.
        """
        words_by_length = canonical_words(word_list)

        alphabet = tuple(sorted({letter for words in words_by_length.values() for word in words for letter in word.text}))
        if len(alphabet) > 64:
            raise ValueError(f"alphabet has {len(alphabet)} letters; the index supports at most 64")
        letter_index = {letter: position for position, letter in enumerate(alphabet)}

        scores: dict[int, np.ndarray] = {}
        bits: dict[int, np.ndarray] = {}
        for length, words in words_by_length.items():
            scores[length] = np.array([word.score for word in words], dtype=np.int32)
            bits[length] = _pack_bits(words, length, letter_index)

        return cls(alphabet, letter_index, words_by_length, scores, bits)

    def find(self, pattern: str, min_score: int = 30, max_results: int | None = None) -> list[tuple[str, int]]:
        """
        Find words matching pattern, sorted by (-score, text).

        Normalises pattern the same way TriePatternMatcher does: upper-cased
        with '.' converted to '?'. Degrades silently to [] -- never raises --
        for a pattern of a length with no words, an empty pattern, or a
        pattern containing a letter outside this index's alphabet.

        max_results, if given, is true top-N over the full (-score, text)
        order: unlike TriePatternMatcher.find with a cap, this never returns
        a different set of words depending on whether a cap was applied.
        """
        pattern = _normalise(pattern)
        resolved = self._eligible_mask(pattern, min_score)
        if resolved is None:
            return []
        length, mask = resolved

        words = self._words[length]
        results = [(words[word_id].text, int(words[word_id].score)) for word_id in _ids_from_mask(mask)]
        if max_results is not None:
            results = results[:max_results]
        return results

    def count_matches(self, pattern: str, min_score: int = 30) -> int:
        """Count words matching pattern; equal to len(find(pattern, min_score, max_results=None))."""
        pattern = _normalise(pattern)
        resolved = self._eligible_mask(pattern, min_score)
        if resolved is None:
            return 0
        _, mask = resolved
        return _popcount(mask)

    def has_matches(self, pattern: str, min_score: int = 30) -> bool:
        """True if any word matches pattern; equal to count_matches(pattern, min_score) > 0."""
        pattern = _normalise(pattern)
        resolved = self._eligible_mask(pattern, min_score)
        if resolved is None:
            return False
        _, mask = resolved
        return bool(np.any(mask))

    def mask(self, pattern: str, min_score: int = 0) -> np.ndarray:
        """
        Resolve an already-canonical pattern to its uint64 eligibility mask.

        Unlike find, this does not normalise: pattern must already be
        upper-case with '?' for a wildcard and every other character a
        letter of the alphabet. Degrades to an all-zero array of shape
        (ceil(N_L/64),) -- never an exception -- for the same inputs find
        degrades to [] for: a length with no words, an empty pattern, or a
        letter outside the alphabet. min_score defaults to 0, not find's 30,
        because a propagator seeds a domain before any score floor applies.
        """
        resolved = self._eligible_mask(pattern, min_score)
        if resolved is not None:
            return resolved[1]
        length = len(pattern)
        num_chunks = self._bits[length].shape[-1] if length in self._bits else 0
        return np.zeros(num_chunks, dtype=np.uint64)

    def letters_at(self, length: int, pos: int, mask: np.ndarray) -> int:
        """
        Alphabet bitmask of letters occurring at pos among the word ids mask selects.

        Bit a is set iff any(bits[length][pos][a] & mask). An all-zero mask
        (including one mask() returned for a length this index holds no
        words for) never indexes per-length storage and returns 0.
        """
        if not np.any(mask):
            return 0
        hits = np.any(self._bits[length][pos] & mask, axis=-1)
        letters = 0
        for position, hit in enumerate(hits):
            if hit:
                letters |= 1 << position
        return letters

    def restrict(self, length: int, pos: int, letters: int, mask: np.ndarray) -> np.ndarray:
        """
        Narrow mask to the word ids whose letter at pos is one of letters.

        Equal to mask & OR(bits[length][pos][a] for a in letters), letters
        an alphabet bitmask. An empty letters set empties the mask; an
        all-zero mask never indexes per-length storage and is returned as
        is (a copy).
        """
        if not np.any(mask):
            return mask.copy()
        bits = self._bits[length]
        allowed = np.zeros_like(mask)
        for position in range(len(self.alphabet)):
            if letters & (1 << position):
                allowed |= bits[pos, position, :]
        return mask & allowed

    def words(self, length: int, mask: np.ndarray) -> list[tuple[str, int]]:
        """(text, score) pairs, in canonical order, for the word ids mask selects."""
        if not np.any(mask):
            return []
        words = self._words[length]
        return [(words[word_id].text, int(words[word_id].score)) for word_id in _ids_from_mask(mask)]

    def count(self, mask: np.ndarray) -> int:
        """Popcount of mask: the number of word ids it selects."""
        return _popcount(mask)

    def _eligible_mask(self, pattern: str, min_score: int) -> tuple[int, np.ndarray] | None:
        """
        Resolve a normalised pattern to (length, mask) of matching, score-eligible word ids.

        Returns None for every silent-degrade case: empty pattern, a length
        with no words, or a letter outside the alphabet. mask is a uint64
        array shaped like bits[length]'s last axis; bit b of chunk w set
        means word id 64*w + b matches pattern and scores >= min_score.
        """
        length = len(pattern)
        if length == 0 or length not in self._bits:
            return None
        for letter in pattern:
            if letter != "?" and letter not in self.letter_index:
                return None

        scores = self._scores[length]
        bits = self._bits[length]

        n_eligible = int(np.searchsorted(-scores, -min_score, side="right"))
        if n_eligible == 0:
            return None

        mask = _prefix_mask(n_eligible, bits.shape[-1])
        for position, letter in enumerate(pattern):
            if letter == "?":
                continue
            mask &= bits[position, self.letter_index[letter], :]

        return length, mask


def _normalise(pattern: str) -> str:
    """Match TriePatternMatcher's normalisation: upper-case, '.' as an alternate wildcard spelling."""
    return pattern.upper().replace(".", "?")


def _pack_bits(words: tuple[ScoredWord, ...], length: int, letter_index: dict[str, int]) -> np.ndarray:
    """Build the (length, alphabet size, ceil(len(words)/64)) uint64 bitset for one word length."""
    num_chunks = -(-len(words) // _CHUNK_BITS)  # ceil division
    bits = np.zeros((length, len(letter_index), num_chunks), dtype=np.uint64)
    for word_id, word in enumerate(words):
        chunk, bit = divmod(word_id, _CHUNK_BITS)
        bit_value = np.uint64(1) << np.uint64(bit)
        for position, letter in enumerate(word.text):
            bits[position, letter_index[letter], chunk] |= bit_value
    return bits


def _prefix_mask(n_eligible: int, num_chunks: int) -> np.ndarray:
    """A mask with the low-order n_eligible bits set across num_chunks uint64 chunks (id = 64*chunk + bit)."""
    mask = np.zeros(num_chunks, dtype=np.uint64)
    full_chunks, remainder = divmod(n_eligible, _CHUNK_BITS)
    if full_chunks:
        mask[:full_chunks] = _FULL_CHUNK_MASK
    if remainder:
        mask[full_chunks] = (np.uint64(1) << np.uint64(remainder)) - np.uint64(1)
    return mask


def _popcount(mask: np.ndarray) -> int:
    """Total set bits across a chunked uint64 mask: the number of word ids it selects."""
    return sum(bin(int(chunk)).count("1") for chunk in mask)


def _ids_from_mask(mask: np.ndarray) -> list[int]:
    """Decode a chunked bitmask into ascending word ids (id = 64*chunk_index + bit_index)."""
    ids: list[int] = []
    for chunk_index, chunk in enumerate(mask):
        value = int(chunk)
        bit = 0
        while value:
            if value & 1:
                ids.append(chunk_index * _CHUNK_BITS + bit)
            value >>= 1
            bit += 1
    return ids
