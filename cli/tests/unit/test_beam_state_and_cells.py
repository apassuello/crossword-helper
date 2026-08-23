"""
Unit tests for BeamState dataclass, cell type handling, and gibberish filtering.
"""

from unittest.mock import Mock

import pytest
from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamSearchAutofill, BeamState
from src.fill.pattern_matcher import PatternMatcher
from src.fill.word_list import WordList


class TestDataClassFields:
    """Test that BeamState has all required fields."""

    def test_beam_state_has_all_fields(self):
        """Verify BeamState has domains and domain_reductions fields."""
        grid = Grid(11)
        state = BeamState(grid=grid, slots_filled=0, total_slots=10, score=0.0)

        # These fields should exist without hasattr checks
        assert hasattr(state, "domains")
        assert hasattr(state, "domain_reductions")
        assert hasattr(state, "used_words")
        assert hasattr(state, "slot_assignments")

        # They should be initialized properly
        assert state.domains == {}
        assert state.domain_reductions == {}
        assert state.used_words == set()
        assert state.slot_assignments == {}

    def test_beam_state_clone_copies_all_fields(self):
        """Verify clone() copies all fields including new ones."""
        grid = Grid(11)
        state = BeamState(grid=grid, slots_filled=5, total_slots=10, score=50.0)

        # Add some data to the fields
        state.domains[(0, 0, "across")] = ["WORD", "TEST"]
        state.domain_reductions[(0, 0, "across")] = [("reduction", 1)]
        state.used_words.add("HELLO")
        state.slot_assignments[(0, 0, "across")] = "HELLO"

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
        cloned.domains[(0, 0, "across")].append("NEW")
        assert "NEW" not in state.domains[(0, 0, "across")]

        cloned.used_words.add("WORLD")
        assert "WORLD" not in state.used_words


class TestCellTypeIntegration:
    """Test cell type standardization in beam search."""

    def test_grid_uses_dots_for_empty(self):
        """Verify grid returns dots for empty cells."""
        grid = Grid(11)
        assert grid.get_cell(0, 0) == "."

    def test_patterns_use_wildcards(self):
        """Verify patterns use ? for wildcards."""
        grid = Grid(11)
        slot = {"row": 0, "col": 0, "length": 4, "direction": "across"}
        pattern = grid.get_pattern_for_slot(slot)
        assert pattern == "????"

    def test_place_word_rejects_wildcards(self):
        """Verify place_word rejects invalid characters."""
        grid = Grid(11)

        # Should reject wildcard
        with pytest.raises(ValueError, match="Cannot place wildcard"):
            grid.place_word("VI?A", 0, 0, "across")

        # Should reject dot
        with pytest.raises(ValueError, match="Cannot place empty marker"):
            grid.place_word("VI.A", 0, 0, "across")


class TestGibberishFiltering:
    """Test that gibberish words are filtered."""

    def test_gibberish_pattern_detection(self):
        """Test _is_gibberish_pattern method."""
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Test gibberish patterns
        assert autofill._is_gibberish_pattern("AAAAA")
        assert autofill._is_gibberish_pattern("III")
        assert autofill._is_gibberish_pattern("NNN")

        # Test valid patterns
        assert not autofill._is_gibberish_pattern("HELLO")
        assert not autofill._is_gibberish_pattern("VISA")
        assert not autofill._is_gibberish_pattern("AREA")

        # Test patterns with wildcards
        assert autofill._is_gibberish_pattern("AAA??")
        assert not autofill._is_gibberish_pattern("HE??O")

    def test_is_quality_word(self):
        """Test _is_quality_word method filters gibberish."""
        grid = Grid(11)
        word_list = Mock(spec=WordList)
        pattern_matcher = Mock(spec=PatternMatcher)

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Test gibberish words
        assert not autofill._is_quality_word("QZXRTPL")  # No vowels
        assert not autofill._is_quality_word("AAAAAN")  # Repeated letters
        assert not autofill._is_quality_word("NNRRRN")  # Excessive repetition

        # Test valid words
        assert autofill._is_quality_word("HELLO")
        assert autofill._is_quality_word("WORLD")
        assert autofill._is_quality_word("PYTHON")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
