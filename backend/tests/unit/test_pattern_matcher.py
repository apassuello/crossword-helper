"""
Unit tests for pattern matching.
"""
import pytest
from backend.core.pattern_matcher import PatternMatcher


class TestPatternMatcher:
    """Test suite for PatternMatcher class."""

    def test_validate_pattern_valid(self):
        """Test pattern validation with valid patterns."""
        matcher = PatternMatcher([])
        
        # These should not raise
        matcher._validate_pattern('?AT')
        matcher._validate_pattern('????')
        matcher._validate_pattern('C??T')
        matcher._validate_pattern('??????????')  # 10 chars

    def test_validate_pattern_no_wildcard(self):
        """Test pattern validation rejects patterns without wildcards."""
        matcher = PatternMatcher([])
        
        with pytest.raises(ValueError, match="must contain at least one"):
            matcher._validate_pattern('CAT')

    def test_validate_pattern_too_short(self):
        """Test pattern validation rejects too-short patterns."""
        matcher = PatternMatcher([])
        
        with pytest.raises(ValueError, match="must be 3-20"):
            matcher._validate_pattern('?A')

    def test_validate_pattern_too_long(self):
        """Test pattern validation rejects too-long patterns."""
        matcher = PatternMatcher([])
        
        with pytest.raises(ValueError, match="must be 3-20"):
            matcher._validate_pattern('?' * 21)

    def test_validate_pattern_invalid_chars(self):
        """Test pattern validation rejects invalid characters."""
        matcher = PatternMatcher([])
        
        with pytest.raises(ValueError, match="only uppercase letters"):
            matcher._validate_pattern('?a?')  # lowercase
        
        with pytest.raises(ValueError, match="only uppercase letters"):
            matcher._validate_pattern('?1?')  # number

    def test_match_local(self):
        """Test local word list matching."""
        matcher = PatternMatcher([])
        
        words = ['CAT', 'BAT', 'RAT', 'DOG', 'CATS']
        matches = matcher._match_local('?AT', words)
        
        assert set(matches) == {'CAT', 'BAT', 'RAT'}
        assert 'DOG' not in matches
        assert 'CATS' not in matches

    def test_match_local_all_wildcards(self):
        """Test pattern with all wildcards."""
        matcher = PatternMatcher([])
        
        words = ['CAT', 'DOG', 'RAT']
        matches = matcher._match_local('???', words)
        
        assert set(matches) == {'CAT', 'DOG', 'RAT'}

    def test_match_local_specific_pattern(self):
        """Test pattern with specific letters."""
        matcher = PatternMatcher([])
        
        words = ['VISA', 'PITA', 'DIVA', 'IDEA', 'BEST']
        matches = matcher._match_local('?I?A', words)
        
        assert set(matches) == {'VISA', 'PITA', 'DIVA'}
        assert 'IDEA' not in matches  # Second letter is not I
        assert 'BEST' not in matches
