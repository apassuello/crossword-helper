"""
Unit tests for convention normalization.
"""
import pytest
from backend.core.conventions import ConventionHelper


class TestConventionHelper:
    """Test suite for ConventionHelper class."""

    def test_two_word_names(self):
        """Test normalization of two-word names."""
        helper = ConventionHelper()
        
        normalized, rule = helper.normalize('Tina Fey')
        assert normalized == 'TINAFEY'
        assert rule['type'] == 'two_word_names'
        
        normalized, rule = helper.normalize('Tracy Jordan')
        assert normalized == 'TRACYJORDAN'

    def test_title_with_article(self):
        """Test normalization of titles with articles."""
        helper = ConventionHelper()
        
        # "The Office" matches two_word_names (both capitalized)
        # which is checked first, so it uses that rule
        normalized, rule = helper.normalize('The Office')
        assert normalized == 'THEOFFICE'
        # Accept either rule type since both produce same result
        assert rule['type'] in ['two_word_names', 'title_with_article']
        
        # "La haine" (lowercase 'h') matches title_with_article
        normalized, rule = helper.normalize('La haine')
        assert normalized == 'LAHAINE'
        assert rule['type'] == 'title_with_article'

    def test_hyphenated_words(self):
        """Test normalization of hyphenated words."""
        helper = ConventionHelper()
        
        normalized, rule = helper.normalize('self-aware')
        assert normalized == 'SELFAWARE'
        assert rule['type'] == 'hyphenated'
        
        normalized, rule = helper.normalize('co-worker')
        assert normalized == 'COWORKER'

    def test_apostrophe(self):
        """Test normalization of words with apostrophes."""
        helper = ConventionHelper()
        
        normalized, rule = helper.normalize("can't")
        assert normalized == 'CANT'
        assert rule['type'] == 'apostrophe'
        
        normalized, rule = helper.normalize("it's")
        assert normalized == 'ITS'

    def test_default_rule(self):
        """Test default normalization when no pattern matches."""
        helper = ConventionHelper()
        
        normalized, rule = helper.normalize('hello world')
        assert normalized == 'HELLOWORLD'
        assert rule['type'] == 'default'

    def test_get_alternatives(self):
        """Test alternative normalization suggestions."""
        helper = ConventionHelper()
        
        # Very long entry should suggest keeping spaces
        normalized, _ = helper.normalize('This Is A Very Long Entry Indeed')
        alternatives = helper.get_alternatives(
            'This Is A Very Long Entry Indeed',
            normalized
        )
        assert len(alternatives) > 0
        
        # Title with article should suggest removing article
        normalized, _ = helper.normalize('The Office')
        alternatives = helper.get_alternatives('The Office', normalized)
        # Should have alternative without "The"
        assert any('OFFICE' in alt['form'] for alt in alternatives)
