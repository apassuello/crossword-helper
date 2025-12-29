"""
Test-Driven Development tests for gibberish detection in word_list module.

This test suite follows the Red-Green-Refactor cycle:
1. RED: Write failing tests that expose the gibberish scoring bug
2. GREEN: Implement minimal code to make tests pass
3. REFACTOR: Clean up and optimize the implementation

Current Bug: Gibberish like 'AAAAA' scores 40 points, passing quality filters.
Goal: Ensure real words score significantly higher than gibberish patterns.
"""

from src.fill.word_list_improved import WordList


class TestGibberishDetection:
    """Test suite for detecting and penalizing gibberish words."""

    def test_simple_repeated_letters_score_low(self):
        """Test that simple repeated letter patterns score very low."""
        wl = WordList()

        # These should all score VERY low (< 20)
        gibberish_patterns = [
            'AAAAA',  # 5 A's
            'III',    # 3 I's
            'NNN',    # 3 N's
            'EEEE',   # 4 E's
            'SSSS',   # 4 S's
            'ZZZ',    # 3 Z's
            'XXX',    # 3 X's
            'QQQ',    # 3 Q's
        ]

        for pattern in gibberish_patterns:
            score = wl._score_word(pattern)
            assert score < 20, f"Gibberish '{pattern}' scored {score}, expected < 20"

    def test_real_words_score_higher_than_gibberish(self):
        """Test that real words consistently score higher than gibberish."""
        wl = WordList()

        # Real words and their expected minimum scores
        real_words = {
            'ARENA': 50,   # Common letters, good length
            'HELLO': 45,   # Common word, has double L
            'STONE': 55,   # Common letters, no repeats
            'INTER': 60,   # Very common letters
            'RATES': 65,   # Excellent crossword word
            'EATEN': 60,   # Common letters
        }

        # Gibberish patterns and their expected maximum scores
        gibberish = {
            'AAAAA': 15,
            'III': 10,
            'EEE': 10,
            'NNN': 10,
            'SSSS': 12,
        }

        # Check real words score appropriately
        for word, min_score in real_words.items():
            score = wl._score_word(word)
            assert score >= min_score, f"Real word '{word}' scored {score}, expected >= {min_score}"

        # Check gibberish scores low
        for pattern, max_score in gibberish.items():
            score = wl._score_word(pattern)
            assert score <= max_score, f"Gibberish '{pattern}' scored {score}, expected <= {max_score}"

        # Every real word should score higher than every gibberish pattern
        for real_word in real_words:
            real_score = wl._score_word(real_word)
            for gib_pattern in gibberish:
                gib_score = wl._score_word(gib_pattern)
                assert real_score > gib_score, \
                    f"Real word '{real_word}' ({real_score}) should score higher than gibberish '{gib_pattern}' ({gib_score})"

    def test_valid_double_letter_words_not_penalized_excessively(self):
        """Test that valid words with double letters still score reasonably."""
        wl = WordList()

        # Valid words with double letters
        double_letter_words = {
            'BOOK': 35,    # Double O, but real word
            'TREE': 40,    # Double E, common word
            'SPEED': 45,   # Double E, good word
            'LETTER': 35,  # Double T and E, but real
            'COFFEE': 35,  # Double F and E, real word
            'BALLOON': 30,  # Double L and O, real word
        }

        for word, min_score in double_letter_words.items():
            score = wl._score_word(word)
            assert score >= min_score, \
                f"Valid word '{word}' with double letters scored {score}, expected >= {min_score}"

    def test_three_letter_edge_cases(self):
        """Test edge cases for 3-letter words."""
        wl = WordList()

        # Valid 3-letter words that might have repeats
        valid_three_letter = {
            'AAH': 25,   # Valid interjection, double A
            'AAL': 20,   # Valid word (type of tree)
            'ADD': 25,   # Valid word, double D
            'ALL': 30,   # Very common word
            'BEE': 30,   # Common word, double E
            'EGG': 25,   # Common word, double G
            'ILL': 25,   # Common word
            'ODD': 25,   # Common word
            'TOO': 30,   # Very common word
            'ZOO': 20,   # Common word with Z
        }

        # Invalid 3-letter patterns
        invalid_three_letter = {
            'AAA': 10,   # Pure repetition
            'BBB': 10,   # Pure repetition
            'III': 8,    # Pure repetition
            'ZZZ': 5,    # Pure repetition with uncommon letter
        }

        for word, min_score in valid_three_letter.items():
            score = wl._score_word(word)
            assert score >= min_score, \
                f"Valid 3-letter word '{word}' scored {score}, expected >= {min_score}"

        for pattern, max_score in invalid_three_letter.items():
            score = wl._score_word(pattern)
            assert score <= max_score, \
                f"Invalid pattern '{pattern}' scored {score}, expected <= {max_score}"

    def test_progressive_repetition_penalty(self):
        """Test that penalty increases with more repetition."""
        wl = WordList()

        # As repetition increases, score should decrease dramatically
        patterns = [
            ('A', None),      # Too short, won't be scored
            ('AA', None),     # Too short, won't be scored
            ('AAA', 10),      # 3 same letters - very low
            ('AAAA', 8),      # 4 same letters - even lower or same (minimum)
            ('AAAAA', 5),     # 5 same letters - extremely low or same (minimum)
            ('AAAAAA', 3),    # 6 same letters - near minimum or same (minimum)
        ]

        previous_score = 100  # Start with max possible
        for pattern, expected_max in patterns:
            if expected_max is None:
                continue  # Skip patterns that are too short

            score = wl._score_word(pattern)
            assert score <= expected_max, \
                f"Pattern '{pattern}' scored {score}, expected <= {expected_max}"
            # Check that score doesn't increase (can be same due to floor at 1)
            assert score <= previous_score, \
                f"Pattern '{pattern}' ({score}) should score <= than shorter pattern ({previous_score})"
            previous_score = score

    def test_quality_filter_method(self):
        """Test the quality filter method rejects gibberish."""
        wl = WordList()

        # Add a quality check method (to be implemented)
        # This tests the PUBLIC interface for filtering

        good_words = ['ARENA', 'STONE', 'INTER', 'HELLO', 'RATES']
        bad_words = ['AAAAA', 'III', 'NNN', 'ZZZ', 'XXXX']

        for word in good_words:
            assert wl._is_quality_word(word), \
                f"Quality word '{word}' should pass filter"

        for word in bad_words:
            assert not wl._is_quality_word(word), \
                f"Gibberish '{word}' should fail filter"

    def test_get_by_length_with_quality_filter(self):
        """Test that get_by_length can filter out low-quality words."""
        words = ['ARENA', 'AAAAA', 'STONE', 'SSSSS', 'HELLO']
        wl = WordList(words)

        # Get 5-letter words with minimum quality
        quality_words = wl.get_by_length(5, min_score=30)

        # Should include ARENA, STONE, HELLO but not AAAAA or SSSSS
        word_texts = [w.text for w in quality_words]
        assert 'ARENA' in word_texts, "ARENA should be in quality words"
        assert 'STONE' in word_texts, "STONE should be in quality words"
        assert 'HELLO' in word_texts, "HELLO should be in quality words"
        assert 'AAAAA' not in word_texts, "AAAAA should be filtered out"
        assert 'SSSSS' not in word_texts, "SSSSS should be filtered out"

    def test_scoring_consistency_across_lengths(self):
        """Test that scoring is consistent across different word lengths."""
        wl = WordList()

        # Good words of different lengths should score proportionally
        test_cases = [
            ('CAT', 35),      # 3 letters, common
            ('RATE', 50),     # 4 letters, excellent
            ('STONE', 55),    # 5 letters, excellent
            ('MASTER', 60),   # 6 letters, excellent
            ('ENTERED', 65),  # 7 letters, excellent
        ]

        for word, min_score in test_cases:
            score = wl._score_word(word)
            assert score >= min_score, \
                f"Word '{word}' scored {score}, expected >= {min_score}"

    def test_uncommon_letter_patterns(self):
        """Test that uncommon letter combinations score appropriately."""
        wl = WordList()

        # Test cases - these are valid words with uncommon letters
        # The algorithm recognizes them as valid despite uncommon letters
        test_cases = [
            ('JAZZ', 10, 20),     # J and double Z - very low due to double Z and poor diversity
            ('QUIZ', 35, 20),     # Q, U, I, Z - boosted by perfect diversity
            ('JINX', 50, 20),     # J, X - boosted by perfect diversity
            ('ZEPHYR', 50, 20),   # Z but otherwise good letters and perfect diversity
            ('XENON', 60, 20),    # X but otherwise decent with good diversity
            ('QUEEN', 55, 20),    # Q but common other letters
        ]

        for word, expected_score_range, tolerance in test_cases:
            score = wl._score_word(word)
            # Allow specified tolerance for these edge cases
            assert expected_score_range - tolerance <= score <= expected_score_range + tolerance, \
                f"Word '{word}' scored {score}, expected {expected_score_range} ±{tolerance}"

        # More importantly, verify that uncommon words still score lower than common ones
        common_word_score = wl._score_word('RATES')  # Common letters, good diversity
        uncommon_word_score = wl._score_word('JAZZ')  # Very uncommon
        assert common_word_score > uncommon_word_score, \
            f"Common word 'RATES' ({common_word_score}) should score higher than 'JAZZ' ({uncommon_word_score})"


class TestGibberishRejection:
    """Test that gibberish is rejected at add time with proper validation."""

    def test_add_words_rejects_extreme_gibberish(self):
        """Test that extreme gibberish can be rejected during word addition."""
        wl = WordList()

        # If we implement a stricter validation, these should be rejected
        gibberish = ['AAAAA', 'ZZZZZ', 'IIIII', 'XXXXX']
        real_words = ['ARENA', 'STONE', 'HELLO']

        # Add both sets
        wl.add_words(gibberish + real_words)

        # Only real words should be added if strict validation is enabled
        word_texts = [w.text for w in wl.words]

        # Real words should be present
        for word in real_words:
            assert word in word_texts, f"Real word '{word}' should be added"

        # Gibberish should either be absent OR score very low
        for gib in gibberish:
            if gib in word_texts:
                # If it was added, it should score extremely low
                word_obj = next(w for w in wl.words if w.text == gib)
                assert word_obj.score < 20, \
                    f"Gibberish '{gib}' was added but should score < 20, got {word_obj.score}"

    def test_minimum_quality_threshold(self):
        """Test that words below a quality threshold can be filtered."""
        words = ['ARENA', 'AAAAA', 'STONE', 'III', 'RATES', 'ZZZ', 'INTER']
        wl = WordList(words)

        # Get only quality words (score >= 40)
        quality_words = wl.get_all(min_score=40)

        quality_texts = [w.text for w in quality_words]

        # These should be included
        assert 'ARENA' in quality_texts
        assert 'STONE' in quality_texts
        assert 'RATES' in quality_texts
        assert 'INTER' in quality_texts

        # These should be excluded
        assert 'AAAAA' not in quality_texts
        assert 'III' not in quality_texts
        assert 'ZZZ' not in quality_texts


class TestScoringAlgorithmImprovements:
    """Test improvements to the scoring algorithm."""

    def test_letter_diversity_bonus(self):
        """Test that words with more unique letters score higher."""
        wl = WordList()

        # More diverse letters should score higher
        test_cases = [
            ('RATES', 'TTTTT'),  # RATES has 5 unique, TTTTT has 1
            ('STONE', 'SSSSS'),  # STONE has 5 unique, SSSSS has 1
            ('BREAD', 'BBBBB'),  # BREAD has 5 unique, BBBBB has 1
        ]

        for diverse, repetitive in test_cases:
            diverse_score = wl._score_word(diverse)
            repetitive_score = wl._score_word(repetitive)
            assert diverse_score > repetitive_score + 20, \
                f"Diverse '{diverse}' ({diverse_score}) should score much higher than repetitive '{repetitive}' ({repetitive_score})"

    def test_extreme_repetition_penalty(self):
        """Test that extreme repetition gets heavily penalized."""
        wl = WordList()

        # Words with high repetition should score low
        extreme_patterns = [
            ('AAAAA', 5),     # 100% same - minimum score
            ('AAAAB', 25),    # 80% same - very low but not minimum
            ('III', 5),       # 100% same - minimum score
            ('IIIJ', 15),     # 75% same - low score
        ]

        for pattern, max_score in extreme_patterns:
            score = wl._score_word(pattern)
            assert score <= max_score, \
                f"Extreme pattern '{pattern}' scored {score}, should be <= {max_score}"

    def test_common_word_bonus(self):
        """Test that common crossword words get bonus points."""
        wl = WordList()

        # These are known excellent crossword words
        premium_words = {
            'AREA': 60,
            'ERIE': 65,    # Lake Erie - super common in crosswords
            'ARIA': 60,
            'OREO': 55,    # Cookie brand - common
            'ESTATE': 65,
            'AERATE': 70,
        }

        for word, min_score in premium_words.items():
            score = wl._score_word(word)
            # These should score very well due to excellent letter distribution
            assert score >= min_score - 10, \
                f"Premium crossword word '{word}' scored {score}, expected >= {min_score - 10}"
