"""
Unit tests for WordListManager.
"""

import json

import pytest

from backend.data.wordlist_manager import WordListManager


@pytest.fixture
def wordlist_dir(tmp_path):
    """Set up a temporary wordlist directory with test files."""
    # Root-level wordlist
    comprehensive = tmp_path / "comprehensive.txt"
    comprehensive.write_text("CAT\nDOG\nBAT\nRAT\nCOT\n")

    # Category subdirectory
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    crosswordese = core_dir / "crosswordese.txt"
    crosswordese.write_text("ACE\nORE\nETA\nERE\n")

    # metadata.json (empty structure)
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "wordlists": {},
                "categories": {"core": {"description": "Core wordlists"}},
                "tags": {"common": {"description": "Common words"}},
            }
        )
    )

    return tmp_path


@pytest.fixture
def manager(wordlist_dir):
    """Create a WordListManager pointed at the tmp wordlist dir."""
    return WordListManager(wordlist_dir=str(wordlist_dir))


# ---- Loading ----


class TestLoad:
    def test_load_returns_uppercase_words(self, manager):
        words = manager.load("comprehensive")
        assert words == ["CAT", "DOG", "BAT", "RAT", "COT"]

    def test_load_category_path(self, manager):
        words = manager.load("core/crosswordese")
        assert words == ["ACE", "ORE", "ETA", "ERE"]

    def test_load_file_not_found_raises(self, manager):
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            manager.load("nonexistent")

    def test_load_caches_result(self, manager, wordlist_dir):
        first = manager.load("comprehensive")
        # Overwrite file on disk
        (wordlist_dir / "comprehensive.txt").write_text("CHANGED\n")
        second = manager.load("comprehensive")
        # Should return cached version, not the updated file
        assert second is first
        assert second == ["CAT", "DOG", "BAT", "RAT", "COT"]

    def test_load_lowercases_input_file(self, wordlist_dir):
        """Words in file are converted to uppercase regardless of original case."""
        (wordlist_dir / "mixed.txt").write_text("hello\nWorld\nUPPER\n")
        mgr = WordListManager(wordlist_dir=str(wordlist_dir))
        words = mgr.load("mixed")
        assert words == ["HELLO", "WORLD", "UPPER"]


# ---- Discovery ----


class TestDiscovery:
    def test_list_available_returns_keys(self, manager):
        keys = manager.list_available()
        assert "comprehensive" in keys
        assert "core/crosswordese" in keys

    def test_list_all_returns_metadata_dicts(self, manager):
        items = manager.list_all()
        keys = [item["key"] for item in items]
        assert "comprehensive" in keys
        assert "core/crosswordese" in keys

        comp = next(i for i in items if i["key"] == "comprehensive")
        assert "name" in comp
        assert "category" in comp
        assert "filepath" in comp

    def test_list_all_category_filter(self, manager):
        items = manager.list_all(category="core")
        assert len(items) == 1
        assert items[0]["key"] == "core/crosswordese"

    def test_list_all_category_filter_no_match(self, manager):
        items = manager.list_all(category="themed")
        assert items == []

    def test_get_categories(self, manager):
        cats = manager.get_categories()
        assert "core" in cats
        assert cats["core"]["description"] == "Core wordlists"

    def test_get_categories_empty_when_no_metadata(self, tmp_path):
        """When no metadata.json exists, categories is empty."""
        (tmp_path / "words.txt").write_text("A\nB\n")
        mgr = WordListManager(wordlist_dir=str(tmp_path))
        assert mgr.get_categories() == {}


# ---- Analysis ----


class TestAnalysis:
    def test_get_wordlist_info_word_count(self, manager):
        info = manager.get_wordlist_info("comprehensive")
        assert info["word_count"] == 5
        assert info["key"] == "comprehensive"

    def test_get_wordlist_info_generates_name(self, manager):
        info = manager.get_wordlist_info("comprehensive")
        assert "name" in info
        assert isinstance(info["name"], str)

    def test_analyze_words_length_distribution(self, manager):
        stats = manager.analyze_words("comprehensive")
        assert stats["total_words"] == 5
        assert stats["length_distribution"][3] == 5  # all words are 3 letters
        assert stats["average_length"] == 3.0

    def test_analyze_words_letter_frequency(self, manager):
        stats = manager.analyze_words("comprehensive")
        freq = stats["letter_frequency"]
        # 'A' appears in CAT, BAT, RAT = 3 times
        assert freq["A"] == 3
        assert stats["unique_letters"] > 0

    def test_analyze_words_start_end_letters(self, manager):
        stats = manager.analyze_words("comprehensive")
        assert "most_common_starts" in stats
        assert "most_common_ends" in stats
        # CAT, COT start with C
        assert stats["most_common_starts"]["C"] == 2


# ---- Pattern Search ----


class TestPatternSearch:
    def test_search_pattern_wildcard(self, manager):
        results = manager.search_pattern("C?T", ["comprehensive"])
        words = [r[0] for r in results]
        assert "CAT" in words
        assert "COT" in words
        assert "DOG" not in words

    def test_search_pattern_exact(self, manager):
        results = manager.search_pattern("DOG", ["comprehensive"])
        assert len(results) == 1
        assert results[0] == ("DOG", "comprehensive")

    def test_search_pattern_no_matches(self, manager):
        results = manager.search_pattern("ZZZ", ["comprehensive"])
        assert results == []

    def test_search_pattern_across_multiple_wordlists(self, manager):
        results = manager.search_pattern("??E", ["comprehensive", "core/crosswordese"])
        words = [r[0] for r in results]
        assert "ACE" in words
        assert "ORE" in words
        assert "ERE" in words

    def test_search_pattern_source_wordlist_tracked(self, manager):
        results = manager.search_pattern("ACE", ["core/crosswordese"])
        assert results[0] == ("ACE", "core/crosswordese")

    def test_search_pattern_all_wildcards(self, manager):
        results = manager.search_pattern("???", ["comprehensive"])
        assert len(results) == 5  # all words are 3 letters


# ---- Modification ----


class TestModification:
    def test_add_words_appends(self, manager, wordlist_dir):
        manager.add_words("comprehensive", ["FOX", "HEN"])
        words = manager.load("comprehensive")
        assert "FOX" in words
        assert "HEN" in words
        # Original words still present
        assert "CAT" in words

    def test_add_words_create_new_file(self, manager, wordlist_dir):
        manager.add_words("custom", ["ALPHA", "BETA"], create=True)
        words = manager.load("custom")
        assert "ALPHA" in words
        assert "BETA" in words
        assert (wordlist_dir / "custom.txt").exists()

    def test_add_words_no_create_raises(self, manager):
        with pytest.raises(FileNotFoundError, match="not found"):
            manager.add_words("nonexistent", ["WORD"])

    def test_add_words_deduplicates(self, manager):
        manager.add_words("comprehensive", ["CAT", "CAT", "NEW"])
        words = manager.load("comprehensive")
        assert words.count("CAT") == 1
        assert "NEW" in words


# ---- Edge Cases ----


class TestEdgeCases:
    def test_empty_wordlist(self, wordlist_dir):
        (wordlist_dir / "empty.txt").write_text("")
        mgr = WordListManager(wordlist_dir=str(wordlist_dir))
        words = mgr.load("empty")
        assert words == []

    def test_wordlist_with_blank_lines(self, wordlist_dir):
        (wordlist_dir / "blanks.txt").write_text("FOO\n\n  \nBAR\n\n")
        mgr = WordListManager(wordlist_dir=str(wordlist_dir))
        words = mgr.load("blanks")
        assert words == ["FOO", "BAR"]

    def test_wordlist_with_comments(self, wordlist_dir):
        (wordlist_dir / "commented.txt").write_text("# header comment\nWORD\n# another\nTEST\n")
        mgr = WordListManager(wordlist_dir=str(wordlist_dir))
        words = mgr.load("commented")
        assert words == ["WORD", "TEST"]

    def test_no_metadata_file(self, tmp_path):
        """Manager works even without metadata.json."""
        (tmp_path / "simple.txt").write_text("ONE\nTWO\n")
        mgr = WordListManager(wordlist_dir=str(tmp_path))
        words = mgr.load("simple")
        assert words == ["ONE", "TWO"]
