"""
WordListManager reads lists through the parser the solver uses.

novice-readiness spec 0.2.12 section 4 item 1 and P5 ("every word-list load"):
fold, "word,score" split and validity check are the solver's, so the list
browser, the pattern search and the solver agree on which words a list holds.
Order rule: file order of first occurrence, duplicates dropped.

Every test uses a fresh manager and clears ``_cache`` so a cached pre-fold value
cannot make a row pass vacuously.
"""

import pytest

from backend.data.wordlist_manager import WordListManager
from cli.src.fill.word_list import WordList

_LINES = ["CAFÉ", "naïve,40", "STRAßE;3", "CAFE", "# comment", "", "ΑΒΓ"]

# Task 7.3's parity fixture (backend/tests/unit/test_routes.py).
_PARITY_LINES = [
    "CAFÉ",
    "NAÏVE;50",
    "ÜBER",
    "café,40",
    "CAFÉ;50",
    "CAFÉ",
    "ＣＡＴ",
    "STRAßE",
    "ÆON",
    "BJØRN",
    "ONE TWO",
    "AB",
    "ΑΒΓ",
    "ONE",
    "dogs,30",
    "# a comment line",
    "",
    "DOGS",
    "CAFE",
]


def _manager(tmp_path, lines, name="custom"):
    (tmp_path / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    m = WordListManager(wordlist_dir=str(tmp_path))
    m._cache.clear()
    return m


def test_load_folds_splits_commas_and_skips_invalid(tmp_path):
    m = _manager(tmp_path, _LINES)
    assert m.load("custom") == ["CAFE", "NAIVE"]


def test_load_matches_the_solver_on_the_parity_fixture(tmp_path):
    m = _manager(tmp_path, _PARITY_LINES)
    solver = {w.text for w in WordList.from_file(str(tmp_path / "custom.txt"), use_cache=False).words}
    loaded = m.load("custom")
    assert set(loaded) == solver
    assert len(loaded) == len(set(loaded))


def test_search_pattern_finds_the_folded_word(tmp_path):
    m = _manager(tmp_path, _LINES)
    assert m.search_pattern("NA?VE", ["custom"]) == [("NAIVE", "custom")]
    m._cache.clear()
    assert m.search_pattern("NAIVE", ["custom"]) == [("NAIVE", "custom")]


def test_search_pattern_counts_a_folded_duplicate_once(tmp_path):
    m = _manager(tmp_path, _LINES)
    assert m.search_pattern("C?FE", ["custom"]) == [("CAFE", "custom")]


def test_saved_list_reads_back_through_load(tmp_path):
    m = _manager(tmp_path, ["DOG"])
    m.add_words("custom", ["CAFÉ", "naïve;40", "BAT"])
    # what a fresh manager (no cache) returns is what the cache must hold
    fresh = WordListManager(wordlist_dir=str(tmp_path))
    expected = fresh.load("custom")
    assert "CAFE" in expected and "NAIVE" in expected
    assert m.load("custom") == expected
    assert not any(";" in w or not w.isascii() for w in m.load("custom"))


def test_cache_after_save_is_not_raw_lines(tmp_path):
    m = _manager(tmp_path, ["DOG"])
    m.add_words("custom", ["naïve;40"])
    assert "NAIVE" in m.load("custom")
    assert "NAÏVE;40" not in m.load("custom")


def test_get_wordlist_info_counts_loaded_words(tmp_path):
    m = _manager(tmp_path, _LINES)
    assert m.get_wordlist_info("custom")["word_count"] == 2
    m._cache.clear()
    assert m.analyze_words("custom")["total_words"] == 2


@pytest.mark.parametrize("name", ["custom"])
def test_file_order_is_kept(tmp_path, name):
    m = _manager(tmp_path, ["ZEBRA", "APPLE", "zebra", "MANGO"], name)
    assert m.load(name) == ["ZEBRA", "APPLE", "MANGO"]


def test_load_raises_on_an_undecodable_list_and_caches_nothing(tmp_path):
    """load() must not serve a truncated list as if it were whole.

    Verify/Clean keep their swallow-and-skip (Task 7.3, unchanged behaviour);
    WordListManager.load raised on a read error before Task 7.7 and still must,
    or GET /api/wordlists/<name> would show the words before the bad byte as
    the whole list.
    """
    (tmp_path / "latin.txt").write_bytes("CAT\nDOG\n".encode() + "CAFÉ\nEMU\n".encode("latin-1"))
    mgr = WordListManager(wordlist_dir=str(tmp_path))
    mgr._cache.clear()

    with pytest.raises(UnicodeDecodeError):
        mgr.load("latin")
    assert "latin" not in mgr._cache


def _file_lines(tmp_path, name="custom"):
    text = (tmp_path / f"{name}.txt").read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if ln]


class TestEditsKeyOnTheFoldedWord:
    """novice-readiness spec 0.2.14 section 4 item 1: add/remove key on the word load() shows."""

    def test_remove_folded_word_drops_accented_scored_line(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50", "APPLE"])
        m.remove_words("custom", ["CAFE"])
        assert _file_lines(tmp_path) == ["APPLE"]
        m._cache.clear()
        assert m.load("custom") == ["APPLE"]

    def test_remove_matches_comma_scored_line(self, tmp_path):
        m = _manager(tmp_path, ["grape,40"])
        m.remove_words("custom", ["GRAPE"])
        assert _file_lines(tmp_path) == []

    def test_remove_accepts_a_lowercase_accented_request(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50"])
        m.remove_words("custom", ["café"])
        assert _file_lines(tmp_path) == []

    def test_remove_accented_request_matches_unaccented_stored_line(self, tmp_path):
        """Row 3b: row 3 alone passes pre-fix (str.upper() already maps café to CAFÉ)."""
        m = _manager(tmp_path, ["CAFE;50"])
        m.remove_words("custom", ["café"])
        assert _file_lines(tmp_path) == []

    def test_remove_drops_every_line_with_the_key(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50", "CAFE;40"])
        m.remove_words("custom", ["CAFE"])
        assert _file_lines(tmp_path) == []
        m._cache.clear()
        assert "CAFE" not in m.load("custom")

    def test_add_bare_folded_word_keeps_stored_accented_score(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50"])
        m.add_words("custom", ["CAFE"])
        assert _file_lines(tmp_path) == ["CAFÉ;50"]

    def test_add_scored_folded_word_replaces_stored_line(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50"])
        m.add_words("custom", ["CAFE;60"])
        assert _file_lines(tmp_path) == ["CAFE;60"]

    def test_add_uppercase_to_comma_scored_lowercase_writes_one_line(self, tmp_path):
        m = _manager(tmp_path, ["apple,50"])
        m.add_words("custom", ["APPLE"])
        assert len(_file_lines(tmp_path)) == 1

    def test_add_rewrite_keeps_the_first_line_of_a_key(self, tmp_path):
        m = _manager(tmp_path, ["CAFÉ;50", "CAFE;40"])
        m.add_words("custom", ["DOGS"])
        kept = [ln for ln in _file_lines(tmp_path) if ln.startswith("CAF")]
        assert kept == ["CAFÉ;50"]

    def test_add_rewrite_keeps_a_stored_sharp_s_line_as_given(self, tmp_path):
        """Spec 0.2.14 4.1: "ß".upper() is "SS", which would make a skipped line valid."""
        m = _manager(tmp_path, ["STRAßE"])
        m.add_words("custom", ["DOGS"])
        assert "STRAßE" in _file_lines(tmp_path)
        m._cache.clear()
        assert "STRASSE" not in m.load("custom")

    def test_add_writes_a_new_sharp_s_entry_as_given(self, tmp_path):
        m = _manager(tmp_path, ["CAT"])
        m.add_words("custom", ["Straße"])
        m._cache.clear()
        assert "STRASSE" not in m.load("custom")

    def test_pin_add_rewrite_uppercases_a_comma_scored_accented_line(self, tmp_path):
        """Passes before the fix too."""
        m = _manager(tmp_path, ["naïve,40"])
        m.add_words("custom", ["DOGS"])
        assert "NAÏVE,40" in _file_lines(tmp_path)

    def test_pin_add_rewrite_uppercases_a_semicolon_scored_accented_line(self, tmp_path):
        """Passes before the fix too."""
        m = _manager(tmp_path, ["café;50"])
        m.add_words("custom", ["DOGS"])
        assert "CAFÉ;50" in _file_lines(tmp_path)

    def test_add_rewrite_keeps_the_accepted_line_over_a_rejected_one_sharing_its_key(self, tmp_path):
        """Spec 0.2.14 4.1: the add keeps the line the list shows, not a rejected line first."""
        m = _manager(tmp_path, ["GRAPE;abc", "GRAPE;40", "APPLE"])
        m.add_words("custom", ["PEAR"])
        lines = _file_lines(tmp_path)
        assert "GRAPE;40" in lines
        assert "GRAPE;ABC" not in lines
        m._cache.clear()
        assert "GRAPE" in m.load("custom")

    def test_pin_add_rewrite_keeps_the_accepted_line_when_it_comes_first(self, tmp_path):
        """Passes before the fix too."""
        m = _manager(tmp_path, ["GRAPE;40", "GRAPE;abc", "APPLE"])
        m.add_words("custom", ["PEAR"])
        lines = _file_lines(tmp_path)
        assert "GRAPE;40" in lines
        assert "GRAPE;ABC" not in lines
        m._cache.clear()
        assert "GRAPE" in m.load("custom")

    def test_pin_add_rewrite_keeps_a_lone_rejected_line(self, tmp_path):
        """Passes before the fix too."""
        m = _manager(tmp_path, ["GRAPE;abc"])
        m.add_words("custom", ["PEAR"])
        assert "GRAPE;ABC" in _file_lines(tmp_path)

    def test_pin_rejected_line_keeps_the_old_key(self, tmp_path):
        """Passes before the fix too: parse_line rejects APPLE;x, so the old key applies."""
        m = _manager(tmp_path, ["APPLE;x"])
        m.remove_words("custom", ["APPLE"])
        assert _file_lines(tmp_path) == []
