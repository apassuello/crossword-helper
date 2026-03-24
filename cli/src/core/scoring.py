"""
Word and grid scoring algorithms.

This module provides scoring functions for evaluating word quality,
grid fill difficulty, and overall crossword construction metrics.
"""

# Letter frequency categories based on crossword fill difficulty
COMMON_LETTERS = set("EARIOTNS")
UNCOMMON_LETTERS = set("JQXZ")


def score_word(word: str) -> int:
    """
    Score word for crossword-ability based on letter frequency.

    Algorithm:
    1. Count common letters (E, A, R, I, O, T, N, S) → +10 each
    2. Count regular letters → +5 each
    3. Count uncommon letters (J, Q, X, Z) → -15 each
    4. Length bonus → +2 per letter
    5. Clamp to 1-100

    Args:
        word: Word to score (should be uppercase)

    Returns:
        Score from 1-100 (higher = more crossword-friendly)

    Examples:
        >>> score_word('AREA')
        48  # 4 common (40) + 0 uncommon + length 4 (8) = 48
        >>> score_word('QUIZ')
        1   # 1 common (10) + 1 regular (5) + 2 uncommon (-30) + length 4 (8) = -7 → 1
        >>> score_word('YOGA')
        33  # 1 common (10) + 3 regular (15) + 0 uncommon + length 4 (8) = 33
    """
    word = word.upper()

    common_count = sum(1 for c in word if c in COMMON_LETTERS)
    uncommon_count = sum(1 for c in word if c in UNCOMMON_LETTERS)
    regular_count = len(word) - common_count - uncommon_count

    base_score = (common_count * 10) + (regular_count * 5) - (uncommon_count * 15)
    length_bonus = len(word) * 2

    final_score = base_score + length_bonus
    return max(1, min(100, final_score))


def analyze_letters(word: str) -> dict:
    """
    Analyze letter quality distribution for a word.

    Args:
        word: Word to analyze (should be uppercase)

    Returns:
        Dictionary with letter counts:
        {
            'common': count of E/A/R/I/O/T/N/S,
            'uncommon': count of J/Q/X/Z,
            'regular': count of other letters
        }

    Example:
        >>> analyze_letters('QUIZ')
        {'common': 1, 'uncommon': 2, 'regular': 1}
    """
    word = word.upper()

    common_count = sum(1 for c in word if c in COMMON_LETTERS)
    uncommon_count = sum(1 for c in word if c in UNCOMMON_LETTERS)
    regular_count = len(word) - common_count - uncommon_count

    return {
        "common": common_count,
        "uncommon": uncommon_count,
        "regular": regular_count,
    }
