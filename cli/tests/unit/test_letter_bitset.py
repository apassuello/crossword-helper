"""
Differential tests for LetterBitsetIndex against the shipping TriePatternMatcher.

TriePatternMatcher is the oracle (spec decision 1): both implementations answer
the same question ("which words of this WordList match this pattern at this
min_score") over the same WordList, so every pattern in PATTERN_SAMPLE is
checked against both with max_results=None on the trie side always (the trie's
capped path is not top-N -- see WordTrie._search_trie's early-exit-in-
insertion-order behaviour, which find_pattern only sorts and slices
afterwards). The normative-case values further below are literal, hand-taken
from that same oracle on the fixture below, per the task-2 brief's table.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from src.domain.letter_bitset import LetterBitsetIndex
from src.fill.trie_pattern_matcher import TriePatternMatcher
from src.fill.word_list import WordList

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPREHENSIVE_WORDLIST = REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"

# Normative fixture from the C1 brief (shared with Task 1's canonical-order
# fixture): CAT/COT tie at score 90, ACT/CAB tie at score 30.
FIXTURE_WORDS = [
    ("CAT", 90),
    ("COT", 90),
    ("CUT", 70),
    ("BAT", 50),
    ("CAB", 30),
    ("ACT", 30),
]

# Every criterion the equivalence contract names, at minimum: all-wildcard; a
# fixed letter at the first, a middle, and the last position; two fixed
# letters; an all-fixed pattern on the list and one that is not; a letter
# outside the alphabet; a length with no words; and the empty string.
PATTERN_SAMPLE = [
    "???",  # all-wildcard
    "C??",  # fixed letter, first position
    "?A?",  # fixed letter, middle position
    "??T",  # fixed letter, last position
    "C?T",  # two fixed letters
    "CAT",  # all-fixed, on the list
    "BOT",  # all-fixed, not on the list (letters are all in-alphabet)
    "Z??",  # letter outside this list's alphabet
    "CATS",  # a length with no words (fixture is all length-3)
    "",  # empty string
]

MIN_SCORES = (0, 30, 50)


def _by_sort_order(pairs):
    """Sort (text, score) pairs the way the differential contract compares them."""
    return sorted(pairs, key=lambda pair: (-pair[1], pair[0]))


@pytest.fixture(scope="module")
def fixture_word_list() -> WordList:
    return WordList(list(FIXTURE_WORDS))


@pytest.fixture(scope="module")
def bitset_index(fixture_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(fixture_word_list)


@pytest.fixture(scope="module")
def trie_matcher(fixture_word_list) -> TriePatternMatcher:
    return TriePatternMatcher(fixture_word_list)


class TestDifferentialAgainstTrieOracle:
    """find() must agree with TriePatternMatcher, sorted-compared, for every sample pattern and min_score."""

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_find_matches_oracle(self, bitset_index, trie_matcher, pattern, min_score):
        expected = _by_sort_order(trie_matcher.find(pattern, min_score, max_results=None))
        actual = _by_sort_order(bitset_index.find(pattern, min_score))

        assert actual == expected


class TestNormativeCases:
    """Exact values from the task-2 brief's table, taken from the oracle on FIXTURE_WORDS."""

    def test_alphabet_is_derived_sorted_ascending(self, bitset_index):
        assert bitset_index.alphabet == ("A", "B", "C", "O", "T", "U")

    def test_letter_index_maps_each_letter_to_its_alphabet_position(self, bitset_index):
        assert bitset_index.letter_index == {"A": 0, "B": 1, "C": 2, "O": 3, "T": 4, "U": 5}

    def test_find_two_fixed_letters_min_score_zero(self, bitset_index):
        assert bitset_index.find("C?T", 0) == [("CAT", 90), ("COT", 90), ("CUT", 70)]

    def test_find_min_score_equal_to_a_word_score_keeps_it(self, bitset_index):
        """searchsorted(..., side="right") must keep a word scoring exactly min_score."""
        assert bitset_index.find("C?T", 70) == [("CAT", 90), ("COT", 90), ("CUT", 70)]

    def test_find_min_score_above_a_word_score_excludes_it(self, bitset_index):
        assert bitset_index.find("C?T", 80) == [("CAT", 90), ("COT", 90)]

    def test_find_max_results_is_true_top_n(self, bitset_index):
        assert bitset_index.find("C?T", 0, max_results=2) == [("CAT", 90), ("COT", 90)]

    def test_find_all_wildcard_breaks_score_ties_by_text(self, bitset_index):
        assert bitset_index.find("???", 0) == [
            ("CAT", 90),
            ("COT", 90),
            ("CUT", 70),
            ("BAT", 50),
            ("ACT", 30),
            ("CAB", 30),
        ]

    def test_find_normalises_lowercase_letters_and_dot_wildcard(self, bitset_index):
        assert bitset_index.find("c.t", 0) == [("CAT", 90), ("COT", 90), ("CUT", 70)]

    def test_find_letter_outside_alphabet_degrades_to_empty(self, bitset_index):
        assert bitset_index.find("Z??", 0) == []

    def test_find_length_with_no_words_degrades_to_empty(self, bitset_index):
        assert bitset_index.find("CATS", 0) == []

    def test_find_empty_pattern_degrades_to_empty(self, bitset_index):
        assert bitset_index.find("", 0) == []

    def test_count_matches_agrees_with_find_length(self, bitset_index):
        assert bitset_index.count_matches("C?T", 0) == 3

    def test_has_matches_false_when_letter_outside_alphabet(self, bitset_index):
        assert bitset_index.has_matches("Z??", 0) is False

    def test_find_min_score_above_every_word_degrades_to_empty(self, bitset_index):
        """The prefix bound can legitimately admit zero words; this must degrade like any other empty result.

        No row in the brief's table drives min_score past the fixture's top
        score (90); every other min_score case here (0, 70, 80) still leaves
        at least one word eligible.
        """
        assert bitset_index.find("???", 91) == []

    def test_count_matches_zero_when_min_score_above_every_word(self, bitset_index):
        assert bitset_index.count_matches("???", 91) == 0

    def test_has_matches_false_when_min_score_above_every_word(self, bitset_index):
        assert bitset_index.has_matches("???", 91) is False

    def test_from_word_list_rejects_alphabet_over_64_letters(self):
        word_list = _word_list_spanning_n_letters(65)

        with pytest.raises(ValueError, match=r"^alphabet has 65 letters; the index supports at most 64$"):
            LetterBitsetIndex.from_word_list(word_list)

    def test_from_word_list_on_empty_word_list_builds_and_finds_nothing(self):
        """An empty WordList is valid input (WordList's own validation, not re-checked here) and must not crash."""
        idx = LetterBitsetIndex.from_word_list(WordList([]))

        assert idx.alphabet == ()
        assert idx.find("???", 0) == []


class TestQueryMethodRelationships:
    """The relationships the brief pins directly, independent of any single normative row."""

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_count_matches_equals_len_of_uncapped_find(self, bitset_index, pattern, min_score):
        assert bitset_index.count_matches(pattern, min_score) == len(bitset_index.find(pattern, min_score, max_results=None))

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_has_matches_equals_count_matches_greater_than_zero(self, bitset_index, pattern, min_score):
        assert bitset_index.has_matches(pattern, min_score) == (bitset_index.count_matches(pattern, min_score) > 0)


def _word_list_spanning_n_letters(n: int) -> WordList:
    """Build a WordList whose words collectively use exactly n distinct uppercase letters.

    WordList._is_valid_word accepts any str.isalpha() and str.isupper() text,
    so uppercase Greek and Cyrillic characters extend the Latin block's 26
    when n > 26 (per the task-2 brief). Distinct letters are packed 3 to a
    word to satisfy WordList's minimum length; a final short group is padded
    with an already-used letter, which adds no new distinct letter.
    """
    latin = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    greek = [chr(code) for code in range(0x0391, 0x03AA) if chr(code).isalpha() and chr(code).isupper()]
    cyrillic = [chr(code) for code in range(0x0410, 0x0430) if chr(code).isalpha() and chr(code).isupper()]
    pool = latin + greek + cyrillic
    assert len(pool) >= n, "letter pool too small for the requested span"
    letters = pool[:n]

    words = []
    for start in range(0, len(letters), 3):
        chunk = letters[start : start + 3]
        while len(chunk) < 3:
            chunk.append(letters[0])
        words.append("".join(chunk))

    word_list = WordList(words)
    distinct_letters = {ch for word in words for ch in word}
    assert len(distinct_letters) == n, "test setup bug: word pool does not span exactly n distinct letters"
    return word_list


class TestDifferentialAgainstTrieOracleOnRealWordlist:
    """Same equivalence contract, over the shipping comprehensive word list.

    Not marked @pytest.mark.slow per the task-2 brief's threshold; run
    `pytest tests/unit/test_letter_bitset.py -k RealWordlist --durations=5`
    to check whether that still holds before adding the marker back.
    """

    @pytest.fixture(scope="class")
    def real_word_list(self) -> WordList:
        # use_cache=False: determinism, not correctness -- both paths load the
        # same list today, but the cache's freshness depends on a build
        # artifact's mtime relative to the source file's.
        return WordList.from_file(str(COMPREHENSIVE_WORDLIST), use_cache=False)

    @pytest.fixture(scope="class")
    def real_bitset_index(self, real_word_list) -> LetterBitsetIndex:
        return LetterBitsetIndex.from_word_list(real_word_list)

    @pytest.fixture(scope="class")
    def real_trie_matcher(self, real_word_list) -> TriePatternMatcher:
        return TriePatternMatcher(real_word_list)

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_find_matches_oracle_on_real_wordlist(self, real_bitset_index, real_trie_matcher, pattern, min_score):
        expected = _by_sort_order(real_trie_matcher.find(pattern, min_score, max_results=None))
        actual = _by_sort_order(real_bitset_index.find(pattern, min_score))

        assert actual == expected
