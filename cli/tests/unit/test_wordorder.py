"""
Unit tests for the canonical word order (src.domain.wordorder).
"""

import pytest
from src.domain.wordorder import canonical_words
from src.fill.word_list import WordList

# Normative fixture from the C1 task-1 brief: two pairs tie at score 90
# (CAT/COT), two more tie at score 30 (CAB/ACT). CAB is inserted before ACT
# so a delegating implementation (WordList.get_by_length, which sorts by
# score alone and leaves ties in insertion order) would return CAB before
# ACT here instead of the canonical ACT before CAB.
THREE_LETTER_PAIRS = [
    ("CAT", 90),
    ("COT", 90),
    ("CUT", 70),
    ("BAT", 50),
    ("CAB", 30),
    ("ACT", 30),
]

# Independent tie at a different length/score, used to prove ordering is
# computed per-length rather than reused or leaked across lengths.
FOUR_LETTER_PAIRS = [
    ("SORE", 90),
    ("ROSE", 90),
    ("TIDE", 60),
]


class TestCanonicalWords:
    """Tests for canonical_words()."""

    def test_keys_are_lengths_present_in_word_list(self):
        wl = WordList(THREE_LETTER_PAIRS)

        assert canonical_words(wl).keys() == {3}

    def test_length_absent_from_word_list_has_no_key(self):
        """A length with no words must be an absent key, not an empty value.

        A defaultdict(list)-shaped return would satisfy `.keys() == {3}` and
        `result[3]` but silently fabricate `result[4] == []` on lookup; this
        catches that shape.
        """
        wl = WordList(THREE_LETTER_PAIRS)

        with pytest.raises(KeyError):
            canonical_words(wl)[4]

    def test_orders_by_score_descending_then_text_ascending(self):
        wl = WordList(THREE_LETTER_PAIRS)

        result = canonical_words(wl)

        assert [w.text for w in result[3]] == ["CAT", "COT", "CUT", "BAT", "ACT", "CAB"]

    def test_empty_word_list_returns_empty_dict(self):
        assert canonical_words(WordList([])) == {}

    def test_values_are_tuples_not_lists(self):
        wl = WordList(THREE_LETTER_PAIRS)

        assert type(canonical_words(wl)[3]) is tuple

    def test_multiple_lengths_each_ordered_independently(self):
        wl = WordList(THREE_LETTER_PAIRS + FOUR_LETTER_PAIRS)

        result = canonical_words(wl)

        assert result.keys() == {3, 4}
        assert [w.text for w in result[3]] == ["CAT", "COT", "CUT", "BAT", "ACT", "CAB"]
        assert [w.text for w in result[4]] == ["ROSE", "SORE", "TIDE"]

    def test_does_not_mutate_word_list_words_order(self):
        """canonical_words must sort a copy, not word_list.words in place.

        Other WordList consumers rely on .words retaining insertion order;
        an in-place sort would corrupt that for everyone downstream.
        """
        wl = WordList(THREE_LETTER_PAIRS)
        before = [w.text for w in wl.words]

        canonical_words(wl)

        assert [w.text for w in wl.words] == before
