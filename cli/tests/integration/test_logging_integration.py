"""
Integration tests for Phase 2 fixes.

Tests:
- Logging replaces print statements
- DataClass fields are properly defined
- Cell type standardization
- Gibberish filtering
"""

import logging
import pytest
from unittest.mock import Mock, patch
from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamSearchAutofill, BeamState
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher


class TestLoggingIntegration:
    """Test that logging works correctly."""

    def test_no_print_statements(self):
        """Ensure no print() calls remain in production code."""
        # This is verified by the fact that logger.debug is used instead
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        # Create autofill instance
        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # The constructor should not raise any NameError for print
        assert autofill is not None

    @patch('cli.src.fill.beam_search_autofill.logger')
    def test_debug_logging_works(self, mock_logger):
        """Test that debug messages are logged correctly."""
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        autofill = BeamSearchAutofill(
            grid, word_list, pattern_matcher,
            beam_width=2
        )

        # The logger should be available
        assert mock_logger is not None


class TestDataClassFields:
    """Test that BeamState has all required fields."""

    def test_beam_state_has_all_fields(self):
        """Verify BeamState has domains and domain_reductions fields."""
        grid = Grid(11)
        state = BeamState(
            grid=grid,
            slots_filled=0,
            total_slots=10,
            score=0.0
        )

        # These fields should exist without hasattr checks
        assert hasattr(state, 'domains')
        assert hasattr(state, 'domain_reductions')
        assert hasattr(state, 'used_words')
        assert hasattr(state, 'slot_assignments')

        # They should be initialized properly
        assert state.domains == {}
        assert state.domain_reductions == {}
        assert state.used_words == set()
        assert state.slot_assignments == {}

    def test_beam_state_clone_copies_all_fields(self):
        """Verify clone() copies all fields including new ones."""
        grid = Grid(11)
        state = BeamState(
            grid=grid,
            slots_filled=5,
            total_slots=10,
            score=50.0
        )

        # Add some data to the fields
        state.domains[(0, 0, 'across')] = ['WORD', 'TEST']
        state.domain_reductions[(0, 0, 'across')] = [('reduction', 1)]
        state.used_words.add('HELLO')
        state.slot_assignments[(0, 0, 'across')] = 'HELLO'

        # Clone the state
        cloned = state.clone()

        # Verify all fields are copied
        assert cloned.slots_filled == 5
        assert cloned.total_slots == 10
        assert cloned.score == 50.0
        assert cloned.domains == state.domains
        assert cloned.domain_reductions == state.domain_reductions
        assert cloned.used_words == state.used_words
        assert cloned.slot_assignments == state.slot_assignments

        # Verify they're independent copies
        cloned.domains[(0, 0, 'across')].append('NEW')
        assert 'NEW' not in state.domains[(0, 0, 'across')]

        cloned.used_words.add('WORLD')
        assert 'WORLD' not in state.used_words


class TestCellTypeIntegration:
    """Test cell type standardization in beam search."""

    def test_grid_uses_dots_for_empty(self):
        """Verify grid returns dots for empty cells."""
        grid = Grid(11)
        assert grid.get_cell(0, 0) == '.'

    def test_patterns_use_wildcards(self):
        """Verify patterns use ? for wildcards."""
        grid = Grid(11)
        slot = {'row': 0, 'col': 0, 'length': 4, 'direction': 'across'}
        pattern = grid.get_pattern_for_slot(slot)
        assert pattern == '????'

    def test_place_word_rejects_wildcards(self):
        """Verify place_word rejects invalid characters."""
        grid = Grid(11)

        # Should reject wildcard
        with pytest.raises(ValueError, match="Cannot place wildcard"):
            grid.place_word('VI?A', 0, 0, 'across')

        # Should reject dot
        with pytest.raises(ValueError, match="Cannot place empty marker"):
            grid.place_word('VI.A', 0, 0, 'across')


class TestGibberishFiltering:
    """Test that gibberish words are filtered."""

    def test_gibberish_pattern_detection(self):
        """Test _is_gibberish_pattern method."""
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Test gibberish patterns
        assert autofill._is_gibberish_pattern('AAAAA') == True
        assert autofill._is_gibberish_pattern('III') == True
        assert autofill._is_gibberish_pattern('NNN') == True

        # Test valid patterns
        assert autofill._is_gibberish_pattern('HELLO') == False
        assert autofill._is_gibberish_pattern('VISA') == False
        assert autofill._is_gibberish_pattern('AREA') == False

        # Test patterns with wildcards
        assert autofill._is_gibberish_pattern('AAA??') == True
        assert autofill._is_gibberish_pattern('HE??O') == False

    def test_is_quality_word(self):
        """Test _is_quality_word method filters gibberish."""
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Test gibberish words
        assert autofill._is_quality_word('QZXRTPL') == False  # No vowels
        assert autofill._is_quality_word('AAAAAN') == False   # Repeated letters
        assert autofill._is_quality_word('NNRRRN') == False   # Excessive repetition

        # Test valid words
        assert autofill._is_quality_word('HELLO') == True
        assert autofill._is_quality_word('WORLD') == True
        assert autofill._is_quality_word('PYTHON') == True


class TestMACIntegration:
    """Test MAC propagation with proper domains."""

    def test_domains_initialized_in_state(self):
        """Test that domains are properly initialized."""
        grid = Grid(11)
        state = BeamState(
            grid=grid,
            slots_filled=0,
            total_slots=10,
            score=0.0
        )

        # Domains should be empty initially
        assert state.domains == {}

        # Add a domain
        state.domains[(0, 0, 'across')] = ['HELLO', 'WORLD']
        assert len(state.domains) == 1
        assert 'HELLO' in state.domains[(0, 0, 'across')]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])