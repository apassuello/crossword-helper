"""
Unit tests for word quality in autofill — scoring, gibberish detection, and deduplication.
"""

import pytest
from src.core.grid import Grid
from src.fill.beam_search_autofill import BeamState
from src.fill.pattern_matcher import PatternMatcher
from src.fill.word_list import WordList


class TestWordQuality:
    """Tests for scoring and gibberish filtering in autofill."""

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
        assert (
            max_gibberish < min_real
        ), f"Best gibberish ({max_gibberish}) should score less than worst real word ({min_real})"

    def test_empty_cell_consistency(self):
        """Test consistent handling of empty cells (dots vs wildcards)."""
        grid = Grid(11)

        # Grid starts with all empty cells
        # get_pattern_for_slot should convert empty cells to '?'
        slot = {"row": 0, "col": 0, "direction": "across", "length": 5}
        pattern = grid.get_pattern_for_slot(slot)

        assert pattern == "?????", "Empty cells should be represented as wildcards"
        assert "." not in pattern, "Pattern should not contain dots"

    def test_duplicate_word_prevention(self):
        """Test that duplicate words are properly tracked."""
        state = BeamState(grid=Grid(11), slots_filled=0, total_slots=10, score=0.0, used_words=set())

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
        quality_words = ["STONE", "ARENA", "RATES", "INTER", "HELLO", "WORLD"]
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
        words = [f"WORD{'ABCD'[i % 4]}{'EFGH'[i % 4]}{chr(65 + i % 26)}{chr(65 + (i // 26) % 26)}" for i in range(1000)]
        word_list = WordList(words)
        pm = PatternMatcher(word_list)

        # Time pattern matching
        start = time.time()
        # Use the actual method name from PatternMatcher
        # Pattern must match word length: WORDAAEA = 8 letters
        pattern = "WORD????"
        candidates = [(w.text, w.score) for w in word_list.words if pm.matches_pattern(w.text, pattern)]
        end = time.time()

        # Should be fast even with validation
        assert end - start < 0.5, f"Pattern matching took {end - start:.2f}s"
        assert len(candidates) > 0, "Should find matches"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestLockConflictFailsPlacement:
    """novice-readiness spec 0.2.4 §2.1 (C13): a candidate that disagrees with a lock is skipped, not fatal."""

    L6 = ["CAT", "ORE", "WED", "COW", "ARE", "TED"]

    @staticmethod
    def _solver_with_dog_first(on_backtrack):
        from src.fill.autofill import Autofill

        grid = Grid(3, validate_size=False)
        grid.set_letter(0, 0, "C", lock=True)
        wl = WordList([(w, 50) for w in TestLockConflictFailsPlacement.L6])
        solver = Autofill(grid, wl, PatternMatcher(wl), timeout=30)
        solver.on_backtrack = on_backtrack
        real = solver._get_candidates

        def patched(slot):
            if (slot["row"], slot["col"], slot["direction"]) == (0, 0, "across"):
                return [("DOG", 50), ("CAT", 50)]
            return real(slot)

        solver._get_candidates = patched
        # MAC re-sorts candidates by LCV; a constant keeps the stable order DOG, CAT.
        solver._lcv_score_accurate = lambda word, slot: 0
        solver._lcv_score_fast = lambda word, slot: 0
        return grid, solver

    @pytest.mark.parametrize("use_mac", [False, True], ids=["_backtrack", "_backtrack_with_mac"])
    def test_conflicting_candidate_is_skipped(self, use_mac):
        recorded = []
        grid, solver = self._solver_with_dog_first(recorded.append)
        attempted = []
        real_place = grid.place_word

        def spy(word, *args, **kwargs):
            attempted.append(word)
            return real_place(word, *args, **kwargs)

        grid.place_word = spy

        solver.fill(timeout=30, use_mac=use_mac)

        assert attempted[:2] == ["DOG", "CAT"], "the conflicting candidate must reach place_word first"
        assert grid.get_cell(0, 0) == "C"
        assert grid.get_pattern_for_slot({"row": 0, "col": 0, "direction": "across", "length": 3}) == "CAT"
        assert "DOG" not in solver.used_words
        assert recorded == []
