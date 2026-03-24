"""
Unit tests for pattern_matcher module.
"""

import pytest
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher


class TestPatternMatcher:
    """Test PatternMatcher class."""

    @pytest.fixture
    def word_list(self):
        """Create a sample word list for testing."""
        words = [
            'CAT', 'COT', 'CUT',
            'BAT', 'BOT', 'BUT',
            'RAT', 'ROT', 'RUT',
            'CATS', 'DOGS', 'BIRD',
            'APPLE', 'APPLES',
        ]
        return WordList(words)

    @pytest.fixture
    def matcher(self, word_list):
        """Create a pattern matcher with sample word list."""
        return PatternMatcher(word_list)

    def test_init(self, word_list):
        """Test creating pattern matcher."""
        matcher = PatternMatcher(word_list)
        assert matcher.word_list == word_list

    def test_find_exact_pattern(self, matcher):
        """Test finding words with exact pattern (no wildcards)."""
        matches = matcher.find('CAT')
        assert len(matches) == 1
        assert matches[0][0] == 'CAT'

    def test_find_wildcard_start(self, matcher):
        """Test finding words with wildcard at start."""
        matches = matcher.find('?AT')
        # Should match CAT, BAT, RAT
        matched_words = {word for word, score in matches}
        assert 'CAT' in matched_words
        assert 'BAT' in matched_words
        assert 'RAT' in matched_words

    def test_find_wildcard_middle(self, matcher):
        """Test finding words with wildcard in middle."""
        matches = matcher.find('C?T', min_score=0)  # Set min_score=0 to get all matches
        # Should match CAT, COT, CUT
        matched_words = {word for word, score in matches}
        assert 'CAT' in matched_words
        assert 'COT' in matched_words
        assert 'CUT' in matched_words

    def test_find_wildcard_end(self, matcher):
        """Test finding words with wildcard at end."""
        matches = matcher.find('CA?')
        # Should match CAT
        matched_words = {word for word, score in matches}
        assert 'CAT' in matched_words

    def test_find_multiple_wildcards(self, matcher):
        """Test finding words with multiple wildcards."""
        matches = matcher.find('?A?')
        # Should match CAT, BAT, RAT
        matched_words = {word for word, score in matches}
        assert len(matched_words) >= 3

    def test_find_all_wildcards(self, matcher):
        """Test finding words with all wildcards."""
        matches = matcher.find('???', min_score=0)  # Set min_score=0 to get all matches
        # Should match all 3-letter words
        assert len(matches) >= 9  # At least CAT, COT, CUT, BAT, BOT, BUT, RAT, ROT, RUT

    def test_find_with_min_score(self, matcher):
        """Test filtering by minimum score."""
        matches_all = matcher.find('???', min_score=0)
        matches_high = matcher.find('???', min_score=70)
        # Higher min_score should return fewer or equal matches
        assert len(matches_high) <= len(matches_all)

    def test_find_with_max_results(self, matcher):
        """Test limiting number of results."""
        matches = matcher.find('???', max_results=3)
        assert len(matches) <= 3

    def test_find_sorted_by_score(self, matcher):
        """Test that results are sorted by score descending."""
        matches = matcher.find('???')
        scores = [score for word, score in matches]
        # Should be sorted descending
        assert scores == sorted(scores, reverse=True)

    def test_find_no_matches(self, matcher):
        """Test finding with pattern that matches nothing."""
        matches = matcher.find('XYZ')
        assert len(matches) == 0

    def test_find_case_insensitive(self, matcher):
        """Test that pattern matching is case insensitive."""
        matches_upper = matcher.find('CAT')
        matches_lower = matcher.find('cat')
        assert matches_upper == matches_lower

    def test_find_dot_converted_to_wildcard(self, matcher):
        """Test that dots are converted to wildcards."""
        matches_wildcard = matcher.find('C?T')
        matches_dot = matcher.find('C.T')
        assert matches_wildcard == matches_dot

    def test_count_matches(self, matcher):
        """Test counting matches without returning them."""
        count = matcher.count_matches('???', min_score=0)  # Set min_score=0 to count all
        assert count >= 9  # At least 9 three-letter words

    def test_count_matches_with_min_score(self, matcher):
        """Test counting matches with score filter."""
        count_all = matcher.count_matches('???', min_score=0)
        count_high = matcher.count_matches('???', min_score=70)
        assert count_high <= count_all

    def test_has_matches_true(self, matcher):
        """Test has_matches returns True when matches exist."""
        assert matcher.has_matches('CAT')
        assert matcher.has_matches('?AT')

    def test_has_matches_false(self, matcher):
        """Test has_matches returns False when no matches exist."""
        assert not matcher.has_matches('XYZ')
        assert not matcher.has_matches('ZZZZZ')

    def test_has_matches_with_min_score(self, matcher):
        """Test has_matches with score filter."""
        # Should have matches with low score requirement
        assert matcher.has_matches('???', min_score=0)

    def test_cache_hit(self, matcher):
        """Test that repeated queries use cache."""
        # First call populates cache
        matches1 = matcher.find('CAT')
        # Second call should use cache
        matches2 = matcher.find('CAT')
        assert matches1 == matches2

    def test_cache_different_patterns(self, matcher):
        """Test that cache stores different patterns separately."""
        matches1 = matcher.find('CAT')
        matches2 = matcher.find('DOG')
        # Should be different results
        assert matches1 != matches2

    def test_cache_key_includes_min_score(self, matcher):
        """Test that cache key includes min_score."""
        matches1 = matcher.find('???', min_score=0)
        matches2 = matcher.find('???', min_score=70)
        # Different min_score should give different results
        assert len(matches1) >= len(matches2)

    def test_cache_key_includes_max_results(self, matcher):
        """Test that cache key includes max_results."""
        matches1 = matcher.find('???', max_results=100)
        matches2 = matcher.find('???', max_results=5)
        # Different max_results should give different counts
        assert len(matches1) >= len(matches2)

    def test_pattern_to_regex_simple(self, matcher):
        """Test regex conversion for simple patterns."""
        regex = matcher._pattern_to_regex('CAT')
        assert regex.pattern == '^CAT$'

    def test_pattern_to_regex_wildcards(self, matcher):
        """Test regex conversion with wildcards."""
        regex = matcher._pattern_to_regex('C?T')
        assert regex.match('CAT')
        assert regex.match('COT')
        assert not regex.match('CAAT')

    def test_pattern_length_filter(self, matcher):
        """Test that only words of matching length are considered."""
        matches = matcher.find('????')  # 4 letters
        # Should only match 4-letter words
        assert all(len(word) == 4 for word, score in matches)

    def test_empty_pattern(self, matcher):
        """Test handling of empty pattern."""
        matches = matcher.find('')
        assert len(matches) == 0

    def test_pattern_longer_than_any_word(self, matcher):
        """Test pattern longer than any word in list."""
        matches = matcher.find('?' * 50)
        assert len(matches) == 0

    def test_special_regex_chars_escaped(self, matcher):
        """Test that special regex characters are handled properly."""
        # If word list had special chars, they should be escaped
        # For now, just verify the method doesn't crash
        regex = matcher._pattern_to_regex('A.B')  # Dot should become wildcard
        assert regex.match('AAB')
        assert regex.match('ABB')

    def test_find_performance_large_pattern(self, matcher):
        """Test that finding with large patterns is reasonably fast."""
        import time
        start = time.time()
        matcher.find('?' * 6, max_results=100)
        elapsed = time.time() - start
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0

    def test_cache_effectiveness(self, matcher):
        """Test that cache improves performance."""
        import time

        # First call (no cache)
        start1 = time.time()
        matcher.find('???')
        elapsed1 = time.time() - start1

        # Second call (with cache)
        start2 = time.time()
        matcher.find('???')
        elapsed2 = time.time() - start2

        # Cached call should be faster (or at least not slower)
        assert elapsed2 <= elapsed1 * 1.1  # Allow 10% variance
