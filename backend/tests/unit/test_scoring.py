"""
Unit tests for word scoring algorithms.
"""
import pytest
from backend.core.scoring import score_word, analyze_letters


class TestScoreWord:
    """Test suite for score_word function."""

    def test_common_letters_word(self):
        """Test word with all common letters."""
        # AREA: 4 common letters (A,R,E,A)
        # Score = (4 * 10) + (0 * 5) - (0 * 15) + (4 * 2) = 40 + 8 = 48
        assert score_word('AREA') == 48

    def test_uncommon_letters_word(self):
        """Test word with uncommon letters."""
        # QUIZ: 1 common (I), 1 regular (U), 2 uncommon (Q,Z)
        # Score = (1 * 10) + (1 * 5) - (2 * 15) + (4 * 2) = 10 + 5 - 30 + 8 = -7
        # Clamped to 1
        assert score_word('QUIZ') == 1

    def test_mixed_letters_word(self):
        """Test word with mixed letter types."""
        # YOGA: 1 common (O), 3 regular (Y,G,A could be A common)
        # Actually: O,A are common (2), Y,G are regular (2)
        # Score = (2 * 10) + (2 * 5) - (0 * 15) + (4 * 2) = 20 + 10 + 8 = 38
        score = score_word('YOGA')
        assert 30 <= score <= 45  # Approximate range

    def test_case_insensitive(self):
        """Test that scoring works with lowercase input."""
        assert score_word('area') == score_word('AREA')

    def test_max_score_clamping(self):
        """Test that score doesn't exceed 100."""
        # Long word with all common letters
        score = score_word('EEEEEEEEEEE')  # 11 E's
        assert score <= 100


class TestAnalyzeLetters:
    """Test suite for analyze_letters function."""

    def test_all_common(self):
        """Test word with all common letters."""
        result = analyze_letters('AREA')
        assert result['common'] == 4
        assert result['uncommon'] == 0
        assert result['regular'] == 0

    def test_mixed_letters(self):
        """Test word with mixed letter types."""
        result = analyze_letters('QUIZ')
        assert result['common'] == 1  # I
        assert result['uncommon'] == 2  # Q, Z
        assert result['regular'] == 1  # U

    def test_case_insensitive(self):
        """Test case insensitivity."""
        upper = analyze_letters('QUIZ')
        lower = analyze_letters('quiz')
        assert upper == lower
