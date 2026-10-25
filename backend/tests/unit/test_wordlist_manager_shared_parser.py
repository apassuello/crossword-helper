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
