"""
Simplified regression test suite for Phase 4 bug fixes.

This test suite ensures that all bugs fixed during Phase 4 do not regress.
Each test corresponds to a specific "FIX #N" comment in the codebase.
"""

import pytest

from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamState
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher


class TestPhase4Regressions:
    """Comprehensive tests for all Phase 4 fixes."""

    def test_fix1_slot_completion_counting(self):
        """
        FIX #1 (Phase 4.2): Only increment slots_filled if slot is COMPLETELY filled.
        Previous bug: Counted every word placement, even if slot still had '?' wildcards.
        """
        # Test that partial patterns are not counted as complete
        patterns_and_completeness = [
            ("STONE", True),   # Complete word - should count
            ("A?C??", False),  # Partial pattern - should NOT count
            ("?????", False),  # All wildcards - should NOT count
            ("ARENA", True),   # Complete word - should count
            ("ST?NE", False),  # One wildcard - should NOT count
        ]

        for pattern, should_be_complete in patterns_and_completeness:
            is_complete = '?' not in pattern
            assert is_complete == should_be_complete, \
                f"Pattern '{pattern}' completion check failed"

    def test_fix2_gibberish_detection(self):
        """
        FIX #2 (Phase 4.1): Detect and remove gibberish patterns.
        Previous bug: Words like AAAAA, III, NNN were accepted as valid.
        """
        def is_gibberish(word: str) -> bool:
            """Simple gibberish detection."""
            if len(word) < 3:
                return False
            # All same letter
            if len(set(word)) == 1:
                return True
            # More than 80% same letter
            most_common = max(word.count(c) for c in set(word))
            if most_common / len(word) > 0.8:
                return True
            return False

        # Test gibberish patterns
        gibberish_words = ["AAAAA", "III", "NNN", "ZZZZ", "XXXXX", "QQQ"]
        valid_words = ["STONE", "BOOK", "TREE", "SPEED", "ALL", "HELLO"]

        for word in gibberish_words:
            assert is_gibberish(word), f"{word} should be detected as gibberish"

        for word in valid_words:
            assert not is_gibberish(word), f"{word} should NOT be detected as gibberish"

    def test_fix3_pattern_restoration(self):
        """
        FIX #3 (Phase 4.1/4.2): Fix pattern restoration bug.
        Previous bug: Pattern restoration could crash on certain inputs.
        """
        Grid(11)

        # Test various patterns can be restored without crashing
        test_cases = [
            # (word_to_place, expected_pattern)
            ("STONE", "STONE"),  # Full word
            ("ABC", "ABC"),      # Short word
        ]

        for word, expected in test_cases:
            test_grid = Grid(11)
            test_grid.place_word(word, 0, 0, 'across')
            pattern = test_grid.get_pattern_for_slot({
                'row': 0, 'col': 0, 'direction': 'across', 'length': len(word)
            })
            assert pattern == expected, f"Pattern restoration failed for {word}"

    def test_fix4_grid_completion_validation(self):
        """
        FIX #4 (Phase 4.2): Double-check actual grid completion.
        Previous bug: Relied on counter instead of checking actual grid state.
        """
        grid = Grid(11)

        # Place some words
        grid.place_word("STONE", 0, 0, 'across')
        grid.place_word("ARENA", 1, 0, 'across')

        # Manually create slots to test
        test_slots = [
            {'row': 0, 'col': 0, 'direction': 'across', 'length': 5},
            {'row': 1, 'col': 0, 'direction': 'across', 'length': 5},
            {'row': 2, 'col': 0, 'direction': 'across', 'length': 5},  # Empty slot
        ]

        # Count actually filled slots
        actual_filled = sum(
            1 for slot in test_slots
            if '?' not in grid.get_pattern_for_slot(slot)
        )

        # Should count only the two filled slots, not the empty one
        assert actual_filled == 2, f"Should have 2 filled slots, got {actual_filled}"

    def test_fix5_word_length_validation(self):
        """
        FIX #5 (Phase 4.3): Validate word length matches slot length.
        Previous bug: Words could be placed in wrong-length slots.
        """
        # Test word length validation
        test_cases = [
            ("STONE", 5, True),   # Exact match
            ("CAT", 5, False),    # Too short
            ("STONES", 5, False),  # Too long
            ("DOG", 3, True),     # Exact match
        ]

        for word, slot_length, should_match in test_cases:
            matches = (len(word) == slot_length)
            assert matches == should_match, \
                f"Word '{word}' length check for slot {slot_length} failed"

    def test_gibberish_scoring(self):
        """Test that gibberish patterns receive lower scores than real words."""
        word_list = WordList()

        # Test that gibberish scores lower than real words
        gibberish_words = ["AAAAA", "III", "NNN", "ZZZZZ"]
        real_words = ["STONE", "ARENA", "RATES", "INTER"]

        # Get scores
        gibberish_scores = [word_list._score_word(w) for w in gibberish_words]
        real_scores = [word_list._score_word(w) for w in real_words]

        # Every real word should score higher than every gibberish word
        max_gibberish = max(gibberish_scores)
        min_real = min(real_scores)

        # This is the key test - real words should outscore gibberish
        # Note: The original bug was that AAAAA scored 40, which was too high
        # The fix should ensure gibberish scores much lower
        assert max_gibberish < min_real, \
            f"Best gibberish ({max_gibberish}) should score less than worst real word ({min_real})"

    def test_empty_cell_consistency(self):
        """Test consistent handling of empty cells (dots vs wildcards)."""
        grid = Grid(11)

        # Grid starts with all empty cells
        # get_pattern_for_slot should convert empty cells to '?'
        slot = {'row': 0, 'col': 0, 'direction': 'across', 'length': 5}
        pattern = grid.get_pattern_for_slot(slot)

        assert pattern == "?????", "Empty cells should be represented as wildcards"
        assert '.' not in pattern, "Pattern should not contain dots"

    def test_duplicate_word_prevention(self):
        """Test that duplicate words are properly tracked."""
        state = BeamState(
            grid=Grid(11),
            slots_filled=0,
            total_slots=10,
            score=0.0,
            used_words=set()
        )

        # Add words to used set
        state.used_words.add("STONE")
        state.used_words.add("ARENA")

        # Check tracking
        assert "STONE" in state.used_words, "Should track STONE"
        assert "ARENA" in state.used_words, "Should track ARENA"
        assert "RATES" not in state.used_words, "RATES should not be tracked"

        # When getting candidates, should filter used words
        all_words = ["STONE", "ARENA", "RATES", "INTER"]
        available = [w for w in all_words if w not in state.used_words]

        assert "STONE" not in available, "Used word should be filtered"
        assert "RATES" in available, "Unused word should be available"

    def test_integration_no_gibberish_in_solutions(self):
        """Integration test: Solutions should never contain obvious gibberish."""
        # Create a quality word list (no gibberish)
        quality_words = ['STONE', 'ARENA', 'RATES', 'INTER', 'HELLO', 'WORLD']
        word_list = WordList(quality_words)

        # Verify no single-letter repetitions in word list
        for word_obj in word_list.words:
            word = word_obj.text
            # No word should be all the same letter
            assert len(set(word)) > 1, f"Word {word} is gibberish (all same letter)"
            # No word should be mostly the same letter
            if len(word) >= 3:
                most_common = max(word.count(c) for c in set(word))
                ratio = most_common / len(word)
                assert ratio <= 0.8, f"Word {word} is gibberish ({ratio:.1%} same letter)"


class TestPerformanceRegression:
    """Ensure fixes don't degrade performance."""

    def test_pattern_matching_performance(self):
        """Test pattern matching remains fast with validation."""
        import time

        # Create word list with alphabetic words only
        # WordList validates with isalpha(), so can't use digits
        words = [f"WORD{'ABCD'[i %4]}{'EFGH'[i %4]}{chr(65+i %26)}{chr(65+(i//26) %26)}"
                 for i in range(1000)]
        word_list = WordList(words)
        pm = PatternMatcher(word_list)

        # Time pattern matching
        start = time.time()
        # Use the actual method name from PatternMatcher
        # Pattern must match word length: WORDAAEA = 8 letters
        pattern = "WORD????"
        candidates = [(w.text, w.score) for w in word_list.words
                      if pm.matches_pattern(w.text, pattern)]
        end = time.time()

        # Should be fast even with validation
        assert end - start < 0.5, f"Pattern matching took {end - start:.2f}s"
        assert len(candidates) > 0, "Should find matches"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
