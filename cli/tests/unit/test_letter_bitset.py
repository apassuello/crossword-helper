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

import itertools
from pathlib import Path

import numpy as np
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


@pytest.fixture(scope="module")
def real_word_list() -> WordList:
    # use_cache=False: determinism, not correctness -- both paths load the
    # same list today, but the cache's freshness depends on a build artifact's
    # mtime relative to the source file's.
    return WordList.from_file(str(COMPREHENSIVE_WORDLIST), use_cache=False)


@pytest.fixture(scope="module")
def real_bitset_index(real_word_list) -> LetterBitsetIndex:
    return LetterBitsetIndex.from_word_list(real_word_list)


@pytest.fixture(scope="module")
def real_trie_matcher(real_word_list) -> TriePatternMatcher:
    return TriePatternMatcher(real_word_list)


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

    def test_from_word_list_accepts_alphabet_of_exactly_64_letters(self):
        """The boundary the whole uint64 storage layout rests on: 64 is legal, 65 (above) is not."""
        word_list = _word_list_spanning_n_letters(64)

        idx = LetterBitsetIndex.from_word_list(word_list)

        assert len(idx.alphabet) == 64

    def test_top_alphabet_bit_is_live_through_letters_at_and_restrict(self):
        """Bit 63 -- the highest bit a uint64 chunk provides -- must actually carry a letter's
        occurrences through letters_at and restrict, not merely exist as unused headroom.
        """
        word_list = _word_list_spanning_n_letters(64)
        idx = LetterBitsetIndex.from_word_list(word_list)
        top_letter = idx.alphabet[63]
        assert idx.letter_index[top_letter] == 63

        carrier = next(word for word in word_list.words if top_letter in word.text)
        pos = carrier.text.index(top_letter)
        mask = idx.mask("?" * carrier.length)

        letters = idx.letters_at(carrier.length, pos, mask)
        assert letters & (1 << 63)

        restricted = idx.restrict(carrier.length, pos, 1 << 63, mask)
        assert idx.count(restricted) > 0
        assert all(text[pos] == top_letter for text, _ in idx.words(carrier.length, restricted))

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

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_find_matches_oracle_on_real_wordlist(self, real_bitset_index, real_trie_matcher, pattern, min_score):
        expected = _by_sort_order(real_trie_matcher.find(pattern, min_score, max_results=None))
        actual = _by_sort_order(real_bitset_index.find(pattern, min_score))

        assert actual == expected

    def test_find_all_wildcard_on_real_wordlist_is_already_in_score_then_text_order(self, real_bitset_index):
        """The other tests in this class sort both sides before comparing, so none of them pin find's own
        return order on data spanning multiple 64-bit chunks -- a chunk-decode bug in _ids_from_mask
        that silently reordered chunks would still pass every one of them. This does not sort first.
        """
        results = real_bitset_index.find("???", 0)

        assert results == _by_sort_order(results)


class TestPropagatorPrimitiveNormativeCases:
    """Literal values from the task-3 brief's normative-cases table, on FIXTURE_WORDS."""

    def test_count_of_mask_two_fixed_letters(self, bitset_index):
        assert bitset_index.count(bitset_index.mask("C?T")) == 3

    def test_count_of_mask_letter_outside_alphabet(self, bitset_index):
        assert bitset_index.count(bitset_index.mask("Z??")) == 0

    def test_count_of_mask_length_with_no_words(self, bitset_index):
        assert bitset_index.count(bitset_index.mask("CATS")) == 0

    def test_words_of_mask_two_fixed_letters(self, bitset_index):
        assert bitset_index.words(3, bitset_index.mask("C?T")) == [("CAT", 90), ("COT", 90), ("CUT", 70)]

    def test_letters_at_middle_position_of_two_fixed_letters(self, bitset_index):
        idx = bitset_index
        expected = (1 << idx.letter_index["A"]) | (1 << idx.letter_index["O"]) | (1 << idx.letter_index["U"])
        assert idx.letters_at(3, 1, idx.mask("C?T")) == expected

    def test_letters_at_first_position_of_all_wildcard(self, bitset_index):
        idx = bitset_index
        expected = (1 << idx.letter_index["A"]) | (1 << idx.letter_index["B"]) | (1 << idx.letter_index["C"])
        assert idx.letters_at(3, 0, idx.mask("???")) == expected

    def test_words_after_restrict_to_two_letters(self, bitset_index):
        idx = bitset_index
        letters = (1 << idx.letter_index["A"]) | (1 << idx.letter_index["O"])
        restricted = idx.restrict(3, 1, letters, idx.mask("C?T"))
        assert idx.words(3, restricted) == [("CAT", 90), ("COT", 90)]

    def test_restrict_to_empty_letter_set_empties_the_mask(self, bitset_index):
        assert bitset_index.count(bitset_index.restrict(3, 1, 0, bitset_index.mask("C?T"))) == 0


class TestMaskShapeAndDefault:
    """mask's own contract: array type/shape, and its default divergence from find/count_matches."""

    def test_mask_returns_uint64_array_shaped_like_bits_last_axis(self, bitset_index):
        result = bitset_index.mask("C?T")
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint64
        assert result.shape == (1,)  # 6 words in the fixture -> ceil(6/64) == 1 chunk

    def test_mask_degenerate_shape_matches_a_live_mask_on_the_same_length(self, bitset_index):
        """A letter outside the alphabet still resolves a real length (3); shape must match a live mask's."""
        assert bitset_index.mask("Z??").shape == bitset_index.mask("???").shape == (1,)

    def test_mask_length_with_no_words_has_zero_chunks(self, bitset_index):
        """Unlike Z??, CATS's length (4) has no bits[] entry at all -- no chunk count to borrow."""
        assert bitset_index.mask("CATS").shape == (0,)

    def test_mask_default_min_score_is_zero_not_finds_thirty(self, real_bitset_index):
        """mask defaults to min_score=0; find/count_matches default to 30 (mirroring TriePatternMatcher)."""
        assert np.array_equal(real_bitset_index.mask("???"), real_bitset_index.mask("???", 0))

    def test_mask_default_admits_more_words_than_count_matches_default(self, real_bitset_index):
        """The real list has length-3 words scoring below 30, invisible to count_matches's default floor."""
        assert real_bitset_index.count(real_bitset_index.mask("???")) > real_bitset_index.count_matches("???")


class TestPrimitiveDerivedOracles:
    """The four oracles the task-3 brief derives from find, over PATTERN_SAMPLE x MIN_SCORES."""

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_words_of_mask_equals_find(self, bitset_index, pattern, min_score):
        expected = bitset_index.find(pattern, min_score, max_results=None)
        actual = bitset_index.words(len(pattern), bitset_index.mask(pattern, min_score))
        assert actual == expected

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_count_of_mask_equals_len_of_find(self, bitset_index, pattern, min_score):
        expected = len(bitset_index.find(pattern, min_score, max_results=None))
        actual = bitset_index.count(bitset_index.mask(pattern, min_score))
        assert actual == expected

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_letters_at_equals_letters_seen_at_pos_among_matches(self, bitset_index, pattern, min_score):
        """Holds at every position (fixed or wildcard) and every min_score -- it never reconstructs a pattern."""
        matches = bitset_index.find(pattern, min_score, max_results=None)
        mask = bitset_index.mask(pattern, min_score)
        for pos in range(len(pattern)):
            expected = 0
            for text, _ in matches:
                expected |= 1 << bitset_index.letter_index[text[pos]]
            assert bitset_index.letters_at(len(pattern), pos, mask) == expected

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_restrict_to_a_letter_set_equals_the_union_of_per_letter_masks(self, bitset_index, pattern, min_score):
        """The brief's oracle is over a letters *set*: restrict(pos, letters, mask(p)) == OR(mask(p
        with pos := a) for a in letters). Checked for every 1-, 2- and 3-letter subset of the alphabet
        at each wildcard position -- restrict's reason for existing over a per-letter lookup is
        OR-accumulating across multiple set bits (its loop is `allowed |= bits[pos, a, :]`), so a
        singleton-only sweep cannot exercise that accumulation; a mutation honouring only the lowest
        set bit of `letters` would pass a singleton-only version of this property.

        Only valid at a wildcard position: restrict narrows an *unconstrained* slot, like a real arc
        revision. At a position already fixed in `pattern`, substituting a different letter changes
        what the pattern means and the two sides diverge by construction -- this is not a gap in the
        oracle, it is why the primitive takes (length, pos, mask) instead of a second pattern.
        """
        idx = bitset_index
        length = len(pattern)
        base_mask = idx.mask(pattern, min_score)
        subset_sizes = [size for size in (1, 2, 3) if size <= len(idx.alphabet)]
        for pos, char in enumerate(pattern):
            if char != "?":
                continue
            for subset_size in subset_sizes:
                for subset in itertools.combinations(idx.alphabet, subset_size):
                    letters = 0
                    expected = np.zeros_like(base_mask)
                    for letter in subset:
                        letters |= 1 << idx.letter_index[letter]
                        substituted = pattern[:pos] + letter + pattern[pos + 1 :]
                        expected |= idx.mask(substituted, min_score)
                    actual = idx.restrict(length, pos, letters, base_mask)
                    detail = f"pattern={pattern!r} pos={pos} subset={subset}"
                    assert np.array_equal(actual, expected), detail


class TestPrimitiveInvariants:
    """No repeated text within a length; lengths present are exactly those WordList holds.

    Exercised through the primitives (mask/count/words), not the internal
    _words/_bits dicts -- Task 3 ships a query surface, and these invariants
    are about what that surface reports.
    """

    @pytest.mark.parametrize("length", range(3, 22))
    def test_count_of_all_wildcard_mask_is_nonzero_iff_word_list_has_that_length(
        self, fixture_word_list, bitset_index, length
    ):
        expected_present = any(word.length == length for word in fixture_word_list.words)
        actual_present = bitset_index.count(bitset_index.mask("?" * length)) > 0
        assert actual_present == expected_present

    @pytest.mark.parametrize("length", range(3, 22))
    def test_words_of_all_wildcard_mask_has_no_repeated_text(self, bitset_index, length):
        texts = [text for text, _ in bitset_index.words(length, bitset_index.mask("?" * length))]
        assert len(texts) == len(set(texts))


class TestPrimitiveInvariantsOnRealWordList:
    """Same invariants as TestPrimitiveInvariants, over the shipping comprehensive word list."""

    @pytest.mark.parametrize("length", range(3, 22))
    def test_count_of_all_wildcard_mask_is_nonzero_iff_word_list_has_that_length(
        self, real_word_list, real_bitset_index, length
    ):
        expected_present = any(word.length == length for word in real_word_list.words)
        actual_present = real_bitset_index.count(real_bitset_index.mask("?" * length)) > 0
        assert actual_present == expected_present

    @pytest.mark.parametrize("length", range(3, 22))
    def test_words_of_all_wildcard_mask_has_no_repeated_text(self, real_bitset_index, length):
        texts = [text for text, _ in real_bitset_index.words(length, real_bitset_index.mask("?" * length))]
        assert len(texts) == len(set(texts))


class TestStats:
    """Exact values from the task-4 brief's normative-cases table, on FIXTURE_WORDS."""

    def test_stats_words_is_total_word_count(self, bitset_index):
        assert bitset_index.stats()["words"] == 6

    def test_stats_lengths_is_the_lengths_present(self, bitset_index):
        assert bitset_index.stats()["lengths"] == (3,)

    def test_stats_alphabet_is_the_letters_joined_in_order(self, bitset_index):
        assert bitset_index.stats()["alphabet"] == "ABCOTU"

    def test_stats_key_set_is_pinned_exactly(self, bitset_index):
        assert sorted(bitset_index.stats().keys()) == ["alphabet", "bytes", "lengths", "words"]

    def test_stats_bytes_is_a_positive_int(self, bitset_index):
        bytes_value = bitset_index.stats()["bytes"]
        assert isinstance(bytes_value, int)
        assert bytes_value > 0

    def test_stats_bytes_grows_with_a_bigger_index(self, bitset_index, real_bitset_index):
        """Not pinned to an exact value, but a bigger backing WordList must report more, never equal or less."""
        assert real_bitset_index.stats()["bytes"] > bitset_index.stats()["bytes"]

    def test_stats_lengths_elements_are_native_ints_not_numpy_scalars(self, bitset_index):
        assert all(isinstance(length, int) for length in bitset_index.stats()["lengths"])

    def test_stats_on_empty_word_list_reports_zero_words_and_no_lengths(self):
        idx = LetterBitsetIndex.from_word_list(WordList([]))
        stats = idx.stats()
        assert stats["words"] == 0
        assert stats["lengths"] == ()
        assert stats["alphabet"] == ""
        assert stats["bytes"] == 0


class TestPersistenceArchiveFormat:
    """The on-disk boundary contract: flat arrays only, since a later Rust port must read this file directly."""

    def test_save_writes_only_the_pinned_keys(self, bitset_index, tmp_path):
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        with np.load(path) as data:
            assert sorted(data.files) == ["alphabet", "bits_3", "scores_3", "texts_3"]

    def test_save_writes_no_pickled_object_arrays(self, bitset_index, tmp_path):
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        with np.load(path) as data:
            for key in data.files:
                assert data[key].dtype.kind != "O", f"{key} is a pickled-object array, not a flat array"

    def test_save_writes_texts_as_a_unicode_array(self, bitset_index, tmp_path):
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        with np.load(path) as data:
            assert data["texts_3"].dtype.kind == "U"

    def test_save_writes_to_exactly_the_given_path(self, bitset_index, tmp_path):
        """save must not let np.savez append a suffix or otherwise relocate the file it is given."""
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        assert list(tmp_path.iterdir()) == [path]

    def test_save_on_empty_word_list_writes_only_the_alphabet_key(self, tmp_path):
        idx = LetterBitsetIndex.from_word_list(WordList([]))
        path = tmp_path / "empty.npz"
        idx.save(path)

        with np.load(path) as data:
            assert list(data.files) == ["alphabet"]


class TestPersistenceRoundTrip:
    """save/load round trip, using pytest's tmp_path for the file (task-4 brief)."""

    def test_load_after_save_reproduces_normative_find(self, bitset_index, tmp_path):
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        loaded = LetterBitsetIndex.load(path)

        assert loaded.find("C?T", 0) == [("CAT", 90), ("COT", 90), ("CUT", 70)]

    def test_loaded_index_reports_the_same_alphabet_and_letter_index(self, bitset_index, tmp_path):
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        loaded = LetterBitsetIndex.load(path)

        assert loaded.alphabet == bitset_index.alphabet
        assert loaded.letter_index == bitset_index.letter_index

    def test_loaded_index_stats_equal_the_original(self, bitset_index, tmp_path):
        """Two independently constructed objects: dtype drift or a dropped length would surface here."""
        path = tmp_path / "index.npz"
        bitset_index.save(path)

        loaded = LetterBitsetIndex.load(path)

        assert loaded.stats() == bitset_index.stats()

    def test_round_trip_on_empty_word_list_preserves_empty_state(self, tmp_path):
        idx = LetterBitsetIndex.from_word_list(WordList([]))
        path = tmp_path / "empty.npz"
        idx.save(path)

        loaded = LetterBitsetIndex.load(path)

        assert loaded.alphabet == ()
        assert loaded.find("???", 0) == []
        assert loaded.stats() == idx.stats()

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_round_trip_agrees_with_original_on_find_mask_count_letters_at_and_words(
        self, bitset_index, tmp_path, pattern, min_score
    ):
        path = tmp_path / "index.npz"
        bitset_index.save(path)
        loaded = LetterBitsetIndex.load(path)

        assert loaded.find(pattern, min_score) == bitset_index.find(pattern, min_score)

        original_mask = bitset_index.mask(pattern, min_score)
        loaded_mask = loaded.mask(pattern, min_score)
        assert np.array_equal(loaded_mask, original_mask)

        assert loaded.count(loaded_mask) == bitset_index.count(original_mask)

        length = len(pattern)
        for pos in range(length):
            assert loaded.letters_at(length, pos, loaded_mask) == bitset_index.letters_at(length, pos, original_mask)

        assert loaded.words(length, loaded_mask) == bitset_index.words(length, original_mask)


class TestPersistenceRoundTripOnRealWordList:
    """Same round trip, over the shipping comprehensive word list -- the only fixture with num_chunks > 1,
    so this is the direct check that the 3-D bits array's shape survives a save/load cycle intact.
    """

    @pytest.mark.parametrize("min_score", MIN_SCORES)
    @pytest.mark.parametrize("pattern", PATTERN_SAMPLE)
    def test_round_trip_agrees_with_original_on_find_and_mask(self, real_bitset_index, tmp_path, pattern, min_score):
        path = tmp_path / "index.npz"
        real_bitset_index.save(path)
        loaded = LetterBitsetIndex.load(path)

        assert loaded.find(pattern, min_score) == real_bitset_index.find(pattern, min_score)
        assert np.array_equal(loaded.mask(pattern, min_score), real_bitset_index.mask(pattern, min_score))
