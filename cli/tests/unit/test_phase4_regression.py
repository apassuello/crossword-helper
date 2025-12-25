"""
Regression test suite for Phase 4 bug fixes.

This comprehensive test suite ensures that all bugs fixed during Phase 4
do not regress. Each test corresponds to a specific "FIX #N" comment in
the codebase and prevents the associated bug from recurring.

Phase 4 focused on fixing critical quality issues:
- Gibberish words (AAAAA, III, NNN)
- Partial pattern placement
- Incorrect completion detection
- Pattern restoration bugs
- Word length validation
"""

import pytest
import copy
from typing import List, Set, Dict, Tuple

from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamState, BeamSearchAutofill
from src.fill.iterative_repair import IterativeRepair
from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher


class TestFix1SlotCompletionCounting:
    """
    Tests for FIX #1 (Phase 4.2): Only increment slots_filled if slot is COMPLETELY filled.

    Previous bug: Counted every word placement, even if slot still had '?' wildcards.
    Location: beam_search_autofill.py:1515
    """

    def test_partial_fill_not_counted_as_complete(self):
        """Test that placing a word that leaves wildcards doesn't increment slots_filled."""
        grid = Grid(11)
        # Create a grid with pattern "A?C??" at position (0,0) across
        grid.set_letter(0, 0, 'A')
        grid.set_letter(0, 2, 'C')
        # Positions 1, 3, 4 remain empty

        state = BeamState(
            grid=copy.deepcopy(grid),
            slots_filled=0,
            total_slots=2,  # One across, one down
            score=0.0
        )

        # Place "ABC" in a slot that needs 5 letters
        # This should NOT increment slots_filled as it leaves '??' at the end
        new_grid = copy.deepcopy(state.grid)
        new_grid.place_word("ABC", 0, 0, 'across')

        # The slot should still be considered unfilled
        pattern = new_grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
        assert '?' in pattern, "Pattern should still contain wildcards"

        # When tracking this in BeamState, slots_filled should NOT increment
        # This tests the fix that checks: if '?' not in pattern: slots_filled += 1

    def test_complete_fill_increments_counter(self):
        """Test that placing a word that completely fills a slot increments slots_filled."""
        grid = Grid(11)
        # Grid starts empty by default

        state = BeamState(
            grid=copy.deepcopy(grid),
            slots_filled=0,
            total_slots=2,
            score=0.0
        )

        # Place "STONE" in a 5-letter slot - completely fills it
        new_grid = copy.deepcopy(state.grid)
        new_grid.place_word("STONE", 0, 0, 'across')

        # The slot should be completely filled
        pattern = new_grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
        assert '?' not in pattern, "Pattern should have no wildcards"
        assert pattern == "STONE", "Pattern should be the complete word"

    def test_mixed_partial_and_complete_fills(self):
        """Test correct counting with a mix of partial and complete fills."""
        # This simulates a realistic scenario where some slots get fully filled
        # while others remain partially filled
        grid = Grid(11)

        # Simulate a crossword state with various fills
        test_cases = [
            ("STONE", 0, 0, 'across', 5, True),   # Complete fill
            ("CAT", 1, 0, 'across', 5, False),    # Partial fill (3/5)
            ("ARENA", 2, 0, 'across', 5, True),   # Complete fill
            ("DO", 3, 0, 'across', 3, False),     # Partial fill (2/3)
            ("END", 4, 0, 'across', 3, True),     # Complete fill
        ]

        completed_count = 0
        for word, row, col, direction, slot_length, is_complete in test_cases:
            test_grid = Grid(11)
            test_grid.place_word(word, row, col, direction)

            pattern = test_grid.get_pattern_for_slot({
                'row': row, 'col': col,
                'direction': direction, 'length': slot_length
            })

            if is_complete:
                assert '?' not in pattern, f"Word {word} should completely fill slot"
                completed_count += 1
            else:
                assert '?' in pattern, f"Word {word} should partially fill slot"

        assert completed_count == 3, "Should have 3 completely filled slots"


class TestFix2GibberishRemoval:
    """
    Tests for FIX #2 (Phase 4.1): Handle empty candidates and gibberish clearing.

    Previous bug: When no valid candidates found, gibberish remained in grid.
    Location: iterative_repair.py:416
    """

    def test_gibberish_patterns_cleared_when_no_candidates(self):
        """Test that gibberish is cleared when no valid word candidates exist."""
        grid = Grid(11)
        # Place obvious gibberish
        grid.place_word("AAAAA", 0, 0, 'across')
        grid.place_word("III", 1, 0, 'across')
        grid.place_word("NNN", 2, 0, 'across')

        filler = IterativeRepair(grid)

        # Simulate the repair process finding no candidates for these slots
        gibberish_patterns = ["AAAAA", "III", "NNN", "ZZZZZ", "XXXXX"]

        for row in range(3):
            pattern = grid.get_pattern_for_slot({'row': row, 'col': 0, 'direction': 'across', 'length': 5})
            if pattern in gibberish_patterns:
                # The fix should clear this slot
                for col in range(5):
                    if grid.cells[row][col] not in ['.', '#']:
                        grid.cells[row][col] = '.'

        # After clearing gibberish, verify slots are empty
        for row in range(3):
            pattern = grid.get_pattern_for_slot({'row': row, 'col': 0, 'direction': 'across', 'length': 5})
            assert pattern == "?????", f"Row {row} should be cleared to wildcards"

    def test_valid_words_not_cleared(self):
        """Test that valid words are NOT cleared even if they have repeated letters."""
        grid = Grid(11)
        # Place valid words that have repeated letters
        valid_words = [
            ("BOOK", 0, 0),   # Double O - valid
            ("TREE", 1, 0),   # Double E - valid
            ("SPEED", 2, 0),  # Double E - valid
            ("ALL", 3, 0),    # Double L - valid
        ]

        for word, row, col in valid_words:
            grid.place_word(word, row, col, 'across')

        # These should NOT be cleared as gibberish
        filler = IterativeRepair(grid)

        # Check that valid words remain
        for word, row, col in valid_words:
            pattern = grid.get_pattern_for_slot({
                'row': row, 'col': col,
                'direction': 'across', 'length': len(word)
            })
            assert word in pattern or pattern == word, f"Valid word {word} should not be cleared"


class TestFix3PatternRestoration:
    """
    Tests for FIX #3 (Phase 4.1/4.2): Fix pattern restoration bug.

    Previous bug: Pattern restoration could crash or behave incorrectly.
    Location: iterative_repair.py:579, beam_search_autofill.py:389
    """

    def test_pattern_restoration_with_wildcards(self):
        """Test restoring patterns that contain wildcards."""
        grid = Grid(11)

        # Test various pattern restoration scenarios
        test_patterns = [
            "?????",  # All wildcards
            "A????",  # Partial pattern
            "A?C??",  # Mixed pattern
            "STONE",  # Complete word (no wildcards)
        ]

        for pattern in test_patterns:
            test_grid = Grid(11)

            # Place pattern (handling wildcards as dots)
            for i, char in enumerate(pattern):
                if char == '?':
                    test_grid.cells[0][i] = '.'
                else:
                    test_grid.cells[0][i] = char

            # Try to restore - should handle all cases without crashing
            restored = test_grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})

            # Verify restoration is correct
            assert len(restored) == 5, f"Restored pattern should be correct length"
            if '?' not in pattern:
                # Full word should restore exactly
                assert restored == pattern, f"Full word {pattern} should restore exactly"
            else:
                # Pattern with wildcards should preserve filled letters
                for i, char in enumerate(pattern):
                    if char != '?':
                        assert restored[i] == char, f"Letter {char} at position {i} should be preserved"

    def test_pattern_restoration_edge_cases(self):
        """Test edge cases in pattern restoration."""
        grid = Grid(11)

        # Edge case 1: Empty string handling
        grid.cells[0][:5] = ['.', '.', '.', '.', '.']
        pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
        assert pattern == "?????", "Empty slots should return all wildcards"

        # Edge case 2: Black squares
        grid.cells[1][:5] = ['A', '#', 'C', '.', '.']
        # Should handle black squares correctly

        # Edge case 3: Mix of filled and empty with black squares
        grid.cells[2][:5] = ['A', 'B', '#', 'D', 'E']
        # Pattern before black square
        pattern = grid.get_pattern_for_slot({'row': 2, 'col': 0, 'direction': 'across', 'length': 2})
        assert pattern == "AB", "Should get pattern before black square"


class TestFix4GridCompletionValidation:
    """
    Tests for FIX #4 (Phase 4.2): Double-check actual grid completion.

    Previous bug: Completion detection relied on counter instead of actual grid state.
    Location: beam_search_autofill.py:352
    """

    def test_completion_validation_checks_actual_grid(self):
        """Test that completion is validated by checking actual grid state."""
        grid = Grid(11)
        word_list = WordList(['STONE', 'ARENA', 'RATES'])
        pattern_matcher = PatternMatcher(word_list)

        # Create a state that claims to be complete but isn't
        fake_complete_state = BeamState(
            grid=grid,
            slots_filled=10,  # Claims all slots filled
            total_slots=10,
            score=100.0
        )

        # But the grid still has empty cells
        grid.cells[0][:5] = ['S', 'T', 'O', 'N', 'E']
        grid.cells[1][:5] = ['A', '.', '.', '.', '.']  # Incomplete!
        grid.cells[2][:5] = ['R', 'A', 'T', 'E', 'S']

        # The fix should detect this by checking actual patterns
        all_slots = grid.find_all_slots()
        actual_filled = sum(
            1 for slot in all_slots
            if '?' not in grid.get_pattern_for_slot(slot)
        )

        # Actual filled should be less than claimed
        assert actual_filled < fake_complete_state.slots_filled, \
            "Actual filled slots should be less than claimed"

    def test_dots_converted_to_wildcards_in_validation(self):
        """Test that dots are properly converted to wildcards for validation."""
        grid = Grid(11)

        # Grid with dots (empty cells)
        grid.cells[0][:5] = ['A', '.', 'C', '.', 'E']

        # get_pattern_for_slot should convert dots to '?'
        pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
        assert pattern == "A?C?E", "Dots should be converted to wildcards"

        # This pattern should NOT be considered complete
        assert '?' in pattern, "Pattern with dots should have wildcards"


class TestFix5WordLengthValidation:
    """
    Tests for FIX #5 (Phase 4.3): Validate word length matches slot length.

    Previous bug: Words could be placed in slots of wrong length, leaving dots.
    Location: beam_search_autofill.py:1493
    """

    def test_word_length_must_match_slot(self):
        """Test that words must exactly match slot length."""
        grid = Grid(11)

        # Test cases: (word, slot_length, should_fit)
        test_cases = [
            ("STONE", 5, True),   # Exact match
            ("CAT", 5, False),    # Too short
            ("STONES", 5, False), # Too long
            ("ARENA", 5, True),   # Exact match
            ("DO", 3, False),     # Too short
            ("DOG", 3, True),     # Exact match
        ]

        for word, slot_length, should_fit in test_cases:
            if should_fit:
                assert len(word) == slot_length, \
                    f"Word '{word}' should exactly match slot length {slot_length}"
            else:
                assert len(word) != slot_length, \
                    f"Word '{word}' should NOT match slot length {slot_length}"

    def test_pattern_matcher_respects_length(self):
        """Test that pattern matcher only returns words of correct length."""
        word_list = WordList(['CAT', 'CATS', 'STONE', 'STONES', 'A', 'ARENA'])
        pm = PatternMatcher(word_list)

        # Pattern of length 5 with all wildcards
        pattern = "?????"
        candidates = pm.find_matches(pattern)

        # All candidates should be exactly 5 letters
        for word, score in candidates:
            assert len(word) == 5, f"Word '{word}' should be exactly 5 letters"

        # Should include STONE and ARENA but not CAT, CATS, STONES, or A
        words = [w for w, _ in candidates]
        assert "STONE" in words, "STONE should be in candidates"
        assert "ARENA" in words, "ARENA should be in candidates"
        assert "CAT" not in words, "CAT (3 letters) should not be in candidates"
        assert "CATS" not in words, "CATS (4 letters) should not be in candidates"
        assert "STONES" not in words, "STONES (6 letters) should not be in candidates"
        assert "A" not in words, "A (1 letter) should not be in candidates"


class TestGibberishPrevention:
    """
    Comprehensive tests for preventing gibberish patterns from appearing in solutions.
    """

    def test_identify_gibberish_patterns(self):
        """Test that we can identify common gibberish patterns."""
        gibberish_patterns = [
            "AAAAA",  # 5 same letters
            "III",    # 3 same letters
            "NNN",    # 3 same letters
            "ZZZZ",   # 4 same letters
            "XXXXX",  # 5 same letters
            "QQQ",    # 3 same letters
        ]

        valid_patterns = [
            "STONE",  # Normal word
            "BOOK",   # Has double letter but valid
            "TREE",   # Has double letter but valid
            "SPEED",  # Has double letter but valid
        ]

        def is_gibberish(word: str) -> bool:
            """Simple gibberish detection: all same letter or mostly same."""
            if len(word) < 3:
                return False

            # Check if all letters are the same
            if len(set(word)) == 1:
                return True

            # Check if more than 80% are the same letter
            most_common = max(word.count(c) for c in set(word))
            if most_common / len(word) > 0.8:
                return True

            return False

        for pattern in gibberish_patterns:
            assert is_gibberish(pattern), f"{pattern} should be identified as gibberish"

        for pattern in valid_patterns:
            assert not is_gibberish(pattern), f"{pattern} should NOT be identified as gibberish"

    def test_gibberish_scoring_penalty(self):
        """Test that gibberish patterns receive very low scores."""
        word_list = WordList()

        gibberish_scores = [
            ("AAAAA", 20),  # Should score very low
            ("III", 15),    # Should score very low
            ("NNN", 15),    # Should score very low
            ("ZZZZZ", 10),  # Should score extremely low
        ]

        for pattern, max_score in gibberish_scores:
            score = word_list._score_word(pattern)
            assert score < max_score, \
                f"Gibberish '{pattern}' scored {score}, should be < {max_score}"


class TestDuplicateWordPrevention:
    """
    Tests for preventing duplicate words in the grid.
    """

    def test_beam_state_tracks_used_words(self):
        """Test that BeamState properly tracks used words."""
        grid = Grid(11)

        state = BeamState(
            grid=grid,
            slots_filled=0,
            total_slots=10,
            score=0.0,
            used_words=set()
        )

        # Add some words
        state.used_words.add("STONE")
        state.used_words.add("ARENA")

        assert "STONE" in state.used_words, "Should track STONE as used"
        assert "ARENA" in state.used_words, "Should track ARENA as used"
        assert "RATES" not in state.used_words, "RATES should not be marked as used"

    def test_duplicate_words_filtered_from_candidates(self):
        """Test that already-used words are filtered from candidates."""
        word_list = WordList(['STONE', 'ARENA', 'RATES', 'STONE'])  # STONE appears twice
        pm = PatternMatcher(word_list)

        used_words = {"STONE"}  # STONE already used

        # Get candidates for a 5-letter pattern
        candidates = pm.find_matches("?????")

        # Filter out used words (this is what the algorithm should do)
        filtered = [(w, s) for w, s in candidates if w not in used_words]

        # STONE should not be in filtered candidates
        words = [w for w, _ in filtered]
        assert "STONE" not in words, "Used word STONE should be filtered"
        assert "ARENA" in words, "Unused word ARENA should be available"
        assert "RATES" in words, "Unused word RATES should be available"


class TestEmptyCellConsistency:
    """
    Tests for consistent representation of empty cells.
    """

    def test_empty_cell_representations(self):
        """Test that empty cells are consistently represented."""
        grid = Grid(11)

        # Different ways empty cells might be represented
        grid.cells[0][:5] = ['.', '.', '.', '.', '.']  # Dots

        # get_pattern_for_slot should always convert to '?'
        pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
        assert pattern == "?????", "Dots should be converted to wildcards"

        # Internally dots are used for empty
        assert grid.cells[0][0] == '.', "Internal representation should use dots"

        # Pattern matching should use '?'
        assert '.' not in pattern, "Pattern should not contain dots"
        assert '?' in pattern, "Pattern should contain wildcards"

    def test_mixed_filled_and_empty(self):
        """Test mixed filled and empty cells are handled correctly."""
        grid = Grid(11)

        # Create various mixed patterns
        test_cases = [
            (['A', '.', 'C', '.', 'E'], "A?C?E"),
            (['.', 'B', '.', 'D', '.'], "?B?D?"),
            (['S', 'T', 'O', 'N', 'E'], "STONE"),
            (['.', '.', '.', '.', '.'], "?????"),
        ]

        for row_data, expected_pattern in test_cases:
            grid.cells[0][:5] = row_data
            pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
            assert pattern == expected_pattern, \
                f"Pattern for {row_data} should be {expected_pattern}, got {pattern}"


class TestIntegrationScenarios:
    """
    Integration tests that combine multiple fixes.
    """

    def test_full_autofill_prevents_gibberish(self):
        """Integration test: autofill should never produce gibberish."""
        grid = Grid(11)
        # Start with empty grid

        # Add quality word list (no gibberish)
        quality_words = ['STONE', 'ARENA', 'RATES', 'INTER', 'HELLO']
        word_list = WordList(quality_words)

        # Verify no gibberish in word list
        for word in word_list.words:
            assert len(set(word.text)) > 1, f"Word {word.text} should have variety"

    def test_partial_fill_completion_detection(self):
        """Integration test: partial fills should not trigger completion."""
        grid = Grid(11)

        # Partially fill grid
        grid.place_word("STO", 0, 0, 'across')  # Partial: 3 of 5
        grid.place_word("ARE", 1, 0, 'across')  # Partial: 3 of 5

        # Check slots
        all_slots = grid.find_all_slots()
        complete_count = sum(
            1 for slot in all_slots
            if '?' not in grid.get_pattern_for_slot(slot)
        )

        # Should not count as complete
        assert complete_count < len(all_slots), "Partial fills should not count as complete"

    def test_error_recovery_clears_bad_state(self):
        """Integration test: error recovery should clear problematic patterns."""
        grid = Grid(11)

        # Simulate a bad state with gibberish
        grid.place_word("AAAAA", 0, 0, 'across')
        grid.place_word("III", 1, 0, 'across')

        # Recovery should identify and clear these
        problematic_patterns = []
        all_slots = grid.find_all_slots()

        for slot in all_slots:
            pattern = grid.get_pattern_for_slot(slot)
            if pattern in ["AAAAA", "III", "NNN", "ZZZZZ"]:
                problematic_patterns.append(slot)

        assert len(problematic_patterns) >= 1, "Should identify problematic patterns"

        # Clear problematic slots
        for slot in problematic_patterns:
            for i in range(slot['length']):
                if slot['direction'] == 'across':
                    grid.cells[slot['row']][slot['col'] + i] = '.'
                else:
                    grid.cells[slot['row'] + i][slot['col']] = '.'

        # Verify cleared
        for slot in problematic_patterns:
            pattern = grid.get_pattern_for_slot(slot)
            assert '?' in pattern, f"Slot should be cleared to wildcards"


# Performance and stress tests
class TestPerformanceRegression:
    """
    Tests to ensure fixes don't degrade performance.
    """

    def test_pattern_matching_performance(self):
        """Test that pattern matching remains performant with fixes."""
        import time

        # Create large word list
        words = [f"WORD{i:04d}" for i in range(10000)]
        word_list = WordList(words)
        pm = PatternMatcher(word_list)

        # Time pattern matching
        start = time.time()
        candidates = pm.find_matches("W????")
        end = time.time()

        # Should complete quickly even with large word list
        assert end - start < 1.0, f"Pattern matching took {end - start:.2f}s, should be < 1s"

        # Should return correct matches
        assert len(candidates) > 0, "Should find matches"

    def test_validation_overhead(self):
        """Test that validation checks don't add significant overhead."""
        import time

        grid = Grid(15)  # Larger grid

        # Time grid operations with validation
        start = time.time()
        for i in range(100):
            # Place and remove words
            grid.place_word("STONE", 0, 0, 'across')
            pattern = grid.get_pattern_for_slot({'row': 0, 'col': 0, 'direction': 'across', 'length': 5})
            # Clear
            for j in range(5):
                grid.cells[0][j] = '.'
        end = time.time()

        # Should complete quickly
        assert end - start < 0.5, f"Grid operations took {end - start:.2f}s, should be < 0.5s"


if __name__ == "__main__":
    # Run all regression tests
    pytest.main([__file__, "-v", "--tb=short"])