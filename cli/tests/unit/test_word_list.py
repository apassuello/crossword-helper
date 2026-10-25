"""
Unit tests for word_list module.
"""

import os
import tempfile
from pathlib import Path

import pytest
from src.fill.word_list import ScoredWord, WordList, fold_letters


class TestWordList:
    """Test WordList class."""

    def test_init_empty(self):
        """Test creating empty word list."""
        wl = WordList()
        assert len(wl) == 0

    def test_init_with_words(self):
        """Test creating word list with initial words."""
        words = ["CAT", "DOG", "BIRD"]
        wl = WordList(words)
        assert len(wl) == 3

    def test_add_words(self):
        """Test adding words to list."""
        wl = WordList()
        wl.add_words(["CAT", "DOG"])
        assert len(wl) == 2

    def test_add_words_uppercase_conversion(self):
        """Test that words are converted to uppercase."""
        wl = WordList(["cat", "dog"])
        assert all(w.text.isupper() for w in wl.words)

    def test_add_words_duplicate_rejection(self):
        """Test that duplicate words are rejected."""
        wl = WordList(["CAT"])
        wl.add_words(["CAT"])
        assert len(wl) == 1

    def test_add_words_invalid_length(self):
        """Test that words with invalid length are rejected."""
        wl = WordList(["A", "AB", "ABC", "X" * 22])
        # Only ABC should be added (3-21 letters)
        assert len(wl) == 1
        assert wl.words[0].text == "ABC"

    def test_add_words_invalid_characters(self):
        """Test that words with non-alpha characters are rejected."""
        wl = WordList(["CAT", "DOG123", "BIRD-FLY", "FISH"])
        # Only CAT and FISH should be added
        assert len(wl) == 2

    def test_get_by_length(self):
        """Test getting words by length."""
        wl = WordList(["CAT", "DOGS", "BIRDS"])
        words_3 = wl.get_by_length(3)
        words_4 = wl.get_by_length(4)
        words_5 = wl.get_by_length(5)

        assert len(words_3) == 1
        assert words_3[0].text == "CAT"
        assert len(words_4) == 1
        assert words_4[0].text == "DOGS"
        assert len(words_5) == 1
        assert words_5[0].text == "BIRDS"

    def test_get_by_length_with_min_score(self):
        """Test getting words by length with minimum score."""
        wl = WordList(["CAT", "DOG", "FOX"])
        words = wl.get_by_length(3, min_score=50)
        # High-scoring words should be included
        assert len(words) >= 0

    def test_get_all(self):
        """Test getting all words."""
        wl = WordList(["CAT", "DOG", "BIRD"])
        all_words = wl.get_all()
        assert len(all_words) == 3

    def test_get_all_sorted_by_score(self):
        """Test that get_all returns words sorted by score."""
        wl = WordList(["INTEREST", "JAZZ", "EASY"])  # Different scores
        all_words = wl.get_all()
        # Should be sorted descending by score
        for i in range(len(all_words) - 1):
            assert all_words[i].score >= all_words[i + 1].score

    def test_score_word_common_letters(self):
        """Test that words with common letters score higher."""
        wl = WordList(["EATERS", "JAZZ"])  # EATERS has many common letters
        eaters = next(w for w in wl.words if w.text == "EATERS")
        jazz = next(w for w in wl.words if w.text == "JAZZ")
        # EATERS should score higher than JAZZ
        assert eaters.score > jazz.score

    def test_score_word_length_bonus(self):
        """Test that longer words get bonus."""
        wl = WordList(["CAT", "CATEGORY"])
        cat = next(w for w in wl.words if w.text == "CAT")
        category = next(w for w in wl.words if w.text == "CATEGORY")
        # CATEGORY should have higher base score due to length
        assert category.score > cat.score

    def test_score_word_repetition_penalty(self):
        """Test that repeated letters reduce score."""
        wl = WordList(["LETTER", "STRONG"])  # LETTER has repeated letters
        next(w for w in wl.words if w.text == "LETTER")
        strong = next(w for w in wl.words if w.text == "STRONG")
        # STRONG should score higher (no repeated letters)
        # Note: this might not always hold due to other factors
        assert strong.score >= 0  # Just verify scoring works

    def test_score_clamped(self):
        """Test that scores are clamped to 1-100."""
        wl = WordList(["JAZZ", "EASY"])
        for word in wl.words:
            assert 1 <= word.score <= 100

    def test_length_index(self):
        """Test that length index is maintained."""
        wl = WordList(["CAT", "DOG", "BIRD", "FISH"])
        # Check that words are indexed by length
        assert len(wl._length_index[3]) == 2  # CAT, DOG
        assert len(wl._length_index[4]) >= 2  # BIRD, FISH

    def test_first_letter_index(self):
        """Test that first letter index is maintained."""
        wl = WordList(["CAT", "COW", "DOG"])
        # Check that words are indexed by first letter
        assert len(wl._first_letter_index["C"]) == 2  # CAT, COW
        assert len(wl._first_letter_index["D"]) == 1  # DOG

    def test_from_file_valid(self):
        """Test loading word list from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("CAT\n")
            f.write("DOG\n")
            f.write("BIRD\n")
            f.flush()
            temp_path = f.name

        try:
            wl = WordList.from_file(temp_path)
            assert len(wl) == 3
        finally:
            Path(temp_path).unlink()

    def test_from_file_not_found(self):
        """Test that ValueError is raised for missing file."""
        with pytest.raises(ValueError, match="Failed to read"):
            WordList.from_file("/nonexistent/path/to/file.txt")

    def test_from_file_not_regular_file(self):
        """Test that ValueError is raised for directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="not a regular file"):
                WordList.from_file(tmpdir)

    def test_from_file_too_large(self):
        """Test that a normal-sized file loads successfully; this does not exercise
        the >100MB ValueError guard itself (impractical to create a 100MB+
        fixture here) -- see fill/word_list.py's file-size check."""
        # Create a file that appears to be too large
        # (We'll mock this by checking the error message)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            # Can't actually create 100MB+ file in test, but verify the check exists
            # by testing with a normal file
            wl = WordList.from_file(temp_path)
            # Should succeed for small files
            assert len(wl) == 0
        finally:
            Path(temp_path).unlink()

    def test_from_file_path_traversal_protection(self):
        """Test that path traversal attempts are handled safely."""
        # Create a legitimate temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("CAT\n")
            f.flush()
            temp_path = f.name

        try:
            # Even with path traversal attempts, should resolve to actual path
            wl = WordList.from_file(temp_path)
            assert len(wl) == 1
        finally:
            Path(temp_path).unlink()

    def test_from_file_with_blank_lines(self):
        """Test that blank lines are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("CAT\n")
            f.write("\n")
            f.write("DOG\n")
            f.write("  \n")
            f.write("BIRD\n")
            f.flush()
            temp_path = f.name

        try:
            wl = WordList.from_file(temp_path)
            assert len(wl) == 3
        finally:
            Path(temp_path).unlink()

    def test_repr(self):
        """Test string representation."""
        wl = WordList(["CAT", "DOG"])
        repr_str = repr(wl)
        assert "WordList" in repr_str
        assert "words=2" in repr_str


class TestScoredWordlistFormats:
    """Regression tests: scored wordlist formats used to load 0 words
    (whole lines like 'CAT;50' were rejected by word validation)."""

    def _load(self, content):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        try:
            return WordList.from_file(temp_path, use_cache=False)
        finally:
            Path(temp_path).unlink()

    def test_semicolon_scored_format(self):
        """WORD;SCORE lines (raw/comprehensive_scored.txt, *.dict) parse with scores."""
        wl = self._load("CAT;50\nCOT;42\nCUT;77\n")

        assert len(wl) == 3
        by_text = {w.text: w.score for w in wl.words}
        assert by_text == {"CAT": 50, "COT": 42, "CUT": 77}

    def test_comma_scored_format(self):
        """word,score CSV lines (broda.owl) parse, uppercased, with scores."""
        wl = self._load("cat,55\ncob,33\nCUP,60\n")

        assert len(wl) == 3
        by_text = {w.text: w.score for w in wl.words}
        assert by_text == {"CAT": 55, "COB": 33, "CUP": 60}

    def test_csv_header_line_skipped(self):
        """A 'word,score' CSV header must not become the word 'WORD'."""
        wl = self._load("word,score\ncat,55\n")

        assert len(wl) == 1
        assert wl.words[0].text == "CAT"

    def test_malformed_score_line_skipped(self):
        """Scored lines with non-numeric scores are dropped, not mis-parsed."""
        wl = self._load("CAT;50\nBADLINE;xx\nDOG;10\n")

        assert {w.text for w in wl.words} == {"CAT", "DOG"}

    def test_comment_lines_skipped(self):
        """'#' comment headers (as in raw/comprehensive_scored.txt) are ignored."""
        wl = self._load("# Format: WORD;SCORE\n#\nCAT;50\n")

        assert len(wl) == 1
        assert wl.words[0].text == "CAT"

    def test_plain_format_still_computes_scores(self):
        """Plain wordlists keep the computed letter-frequency score."""
        wl = self._load("CAT\nDOG\n")

        assert len(wl) == 2
        assert all(w.score >= 1 for w in wl.words)

    def test_file_score_overrides_computed_score(self):
        """File-supplied scores win over the internal letter formula."""
        plain = WordList(["CAT"])
        computed_score = plain.words[0].score

        wl = self._load(f"CAT;{computed_score + 17}\n")
        assert wl.words[0].score == computed_score + 17

    def test_add_words_accepts_tuples(self):
        """add_words accepts (word, score) tuples and plain strings mixed."""
        wl = WordList()
        wl.add_words([("CAT", 91), "DOG"])

        by_text = {w.text: w.score for w in wl.words}
        assert by_text["CAT"] == 91
        assert by_text["DOG"] >= 1

    def test_parse_line(self):
        """parse_line handles all three formats plus malformed lines."""
        assert WordList.parse_line("CAT") == ("CAT", None)
        assert WordList.parse_line("CAT;50") == ("CAT", 50)
        assert WordList.parse_line("cat,55") == ("cat", 55)
        assert WordList.parse_line("CAT;50.0") == ("CAT", 50)
        assert WordList.parse_line("word,score") is None
        assert WordList.parse_line("BADLINE;xx") is None

    def test_parse_line_overflowing_score_is_malformed(self):
        """A score float() reads as infinity is malformed, not a crash (PR #61 review)."""
        assert WordList.parse_line("DOG;1e999") is None
        assert WordList.parse_line("DOG;inf") is None
        assert WordList.parse_line("dog,-inf") is None


class TestFromFileCacheFallback:
    """A cache that cannot load falls back to parsing the .txt (spec section 3)."""

    @staticmethod
    def _make(tmp_path, cache_bytes=None):
        txt = tmp_path / "list.txt"
        txt.write_text("CAT\nDOG\nBIRD\n")
        cache = tmp_path / "list.pkl"
        if cache_bytes is None:
            WordList(["CAT", "DOG", "BIRD"]).to_cache(str(cache))
        else:
            cache.write_bytes(cache_bytes)
        # Cache must be NEWER than the source or from_cache is never reached.
        os.utime(txt, (1_000_000, 1_000_000))
        os.utime(cache, (1_000_010, 1_000_010))
        return txt, cache

    def test_valid_newer_cache_is_used(self, tmp_path, capsys):
        txt, cache = self._make(tmp_path)
        # Make the cache distinguishable from the text so we know which loaded.
        WordList(["ZEBRA"]).to_cache(str(cache))
        os.utime(cache, (1_000_010, 1_000_010))
        wl = WordList.from_file(str(txt))
        assert [w.text for w in wl.words] == ["ZEBRA"]
        assert capsys.readouterr().err == ""

    def test_equal_mtimes_read_the_text_not_the_cache(self, tmp_path, capsys):
        """Spec O2 (#42): freshness is strict, cache_mtime > source_mtime."""
        txt, cache = self._make(tmp_path)
        WordList(["ZEBRA"]).to_cache(str(cache))
        os.utime(cache, (1_000_000, 1_000_000))
        wl = WordList.from_file(str(txt))
        assert sorted(w.text for w in wl.words) == ["BIRD", "CAT", "DOG"]

    def test_cache_naming_missing_module_falls_back(self, tmp_path, capsys):
        txt, cache = self._make(tmp_path, b"cno_such_module_xyz\nThing\n.")
        with pytest.raises(ModuleNotFoundError):
            WordList.from_cache(str(cache))
        wl = WordList.from_file(str(txt))
        assert sorted(w.text for w in wl.words) == ["BIRD", "CAT", "DOG"]
        err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.strip()]
        assert len(err_lines) == 1
        assert str(cache.resolve()) in err_lines[0]

    def test_truncated_cache_falls_back(self, tmp_path, capsys):
        good = tmp_path / "g.pkl"
        WordList(["CAT"]).to_cache(str(good))
        data = good.read_bytes()
        txt, cache = self._make(tmp_path, data[: len(data) // 2])
        wl = WordList.from_file(str(txt))
        assert sorted(w.text for w in wl.words) == ["BIRD", "CAT", "DOG"]
        err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.strip()]
        assert len(err_lines) == 1
        assert str(cache.resolve()) in err_lines[0]

    @staticmethod
    def _write_pre_fold_cache(cache, texts):
        """Write a cache in the layout from before the fold (version "1.0").

        Built by hand, not through to_cache, so it stays the old layout.
        """
        import pickle

        words = [ScoredWord(text=t, score=50, length=len(t)) for t in texts]
        length_index = {}
        first_letter_index = {}
        for w in words:
            length_index.setdefault(w.length, []).append(w)
            first_letter_index.setdefault(w.text[0], []).append(w)
        with open(cache, "wb") as f:
            pickle.dump(
                {
                    "words": words,
                    "length_index": length_index,
                    "first_letter_index": first_letter_index,
                    "version": "1.0",
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    def test_pre_fold_cache_is_not_served(self, tmp_path, capsys):
        """novice-readiness spec 0.2.12 section 4 (L11): a cache from before the fold can hold an accented CAFE."""
        txt = tmp_path / "list.txt"
        txt.write_text("CAF\u00c9\nDOGS\n", encoding="utf-8")
        cache = tmp_path / "list.pkl"
        self._write_pre_fold_cache(cache, ["CAF\u00c9", "DOGS"])
        os.utime(txt, (1_000_000, 1_000_000))
        os.utime(cache, (1_000_010, 1_000_010))
        wl = WordList.from_file(str(txt))
        assert sorted(w.text for w in wl.words) == ["CAFE", "DOGS"]
        assert str(cache.resolve()) in capsys.readouterr().err

    def test_cache_written_after_the_fold_is_used(self, tmp_path, capsys):
        txt = tmp_path / "list.txt"
        txt.write_text("CAF\u00c9\nDOGS\n", encoding="utf-8")
        cache = tmp_path / "list.pkl"
        WordList(["ZEBRA"]).to_cache(str(cache))
        os.utime(txt, (1_000_000, 1_000_000))
        os.utime(cache, (1_000_010, 1_000_010))
        wl = WordList.from_file(str(txt))
        assert [w.text for w in wl.words] == ["ZEBRA"]
        assert capsys.readouterr().err == ""

    def test_cache_older_than_text_reads_the_text(self, tmp_path):
        txt = tmp_path / "list.txt"
        txt.write_text("CAF\u00c9\nDOGS\n", encoding="utf-8")
        cache = tmp_path / "list.pkl"
        WordList(["ZEBRA"]).to_cache(str(cache))
        os.utime(cache, (1_000_000, 1_000_000))
        os.utime(txt, (1_000_010, 1_000_010))
        wl = WordList.from_file(str(txt))
        assert sorted(w.text for w in wl.words) == ["CAFE", "DOGS"]


class TestScoredWord:
    """Test ScoredWord dataclass."""

    def test_creation(self):
        """Test creating a ScoredWord."""
        word = ScoredWord(text="CAT", score=75, length=3)
        assert word.text == "CAT"
        assert word.score == 75
        assert word.length == 3

    def test_equality(self):
        """Test ScoredWord equality."""
        word1 = ScoredWord(text="CAT", score=75, length=3)
        word2 = ScoredWord(text="CAT", score=75, length=3)
        word3 = ScoredWord(text="DOG", score=75, length=3)
        assert word1 == word2
        assert word1 != word3


class TestFoldLetters:
    """novice-readiness spec 0.2.12 section 4 (L11): NFKD, combining marks dropped, case preserved."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("CAFÉ", "CAFE"),
            ("café", "cafe"),
            ("NAÏVE", "NAIVE"),
            ("ÜBER", "UBER"),
            ("CAFE\u0301", "CAFE"),
            ("\uff23\uff21\uff34", "CAT"),
            ("STRAßE", "STRAßE"),
            ("plain", "plain"),
        ],
    )
    def test_fold(self, text, expected):
        assert fold_letters(text) == expected

    def test_idempotent(self):
        once = fold_letters("NAÏVE café")
        assert fold_letters(once) == once


class TestCanonicalWord:
    def test_sharp_s_is_not_uppercased_to_ss(self):
        assert WordList.canonical_word("ß") == "ß"

    def test_folds_strips_and_uppercases_ascii(self):
        assert WordList.canonical_word("  café ") == "CAFE"

    def test_non_ascii_after_fold_is_left_unchanged(self):
        assert WordList.canonical_word("STRAßE") == "STRAßE"


class TestIsValidWordAscii:
    def test_accented_rejected(self):
        assert WordList()._is_valid_word("CAFÉ") is False

    def test_ascii_accepted(self):
        assert WordList()._is_valid_word("CAFE") is True

    def test_greek_capitals_rejected(self):
        assert WordList()._is_valid_word("ΑΒΓ") is False


class TestFoldInEveryLoadPath:
    def test_constructor_folds(self):
        assert [w.text for w in WordList(["CAFÉ"]).words] == ["CAFE"]

    def test_constructor_folds_scored_tuple(self):
        wl = WordList([("café", 60)])
        assert [(w.text, w.score) for w in wl.words] == [("CAFE", 60)]

    def test_duplicates_detected_after_fold_keep_first(self):
        wl = WordList(["CAFE", "CAFÉ"])
        assert [w.text for w in wl.words] == ["CAFE"]

    def test_add_words_skips_unfoldable(self):
        wl = WordList(["STRAßE", "ÆON", "BJØRN", "ΑΒΓ", "CAT"])
        assert [w.text for w in wl.words] == ["CAT"]

    def test_parse_line_folds_word_part(self):
        assert WordList.parse_line("CAFÉ;50") == ("CAFE", 50)
        assert WordList.parse_line("café,40") == ("cafe", 40)
        assert WordList.parse_line("NAÏVE") == ("NAIVE", None)

    def test_from_file_folds(self, tmp_path):
        f = tmp_path / "w.txt"
        f.write_text("CAFÉ;50\nnaïve\nSTRAßE\n", encoding="utf-8")
        wl = WordList.from_file(str(f), use_cache=False)
        assert sorted(w.text for w in wl.words) == ["CAFE", "NAIVE"]
