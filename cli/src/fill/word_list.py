"""
Word list management with crossword-ability scoring.

Manages word lists, scores words based on letter frequency and commonality,
and provides efficient lookup operations for autofill.
"""

from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
import re


# Letter frequency scoring (based on common crossword usage)
COMMON_LETTERS = set('EARIOTNS')  # Very common, good for crosswords
REGULAR_LETTERS = set('DHCLUMPFGYBWKVX')  # Regular usage
UNCOMMON_LETTERS = set('JQZ')  # Difficult letters


@dataclass
class ScoredWord:
    """Word with crossword-ability score."""
    text: str
    score: int
    length: int


class WordList:
    """
    Manages word lists with scoring for crossword fill.

    Scores words based on:
    - Letter frequency (common letters score higher)
    - Word length (longer words score higher)
    - Letter diversity (repeated letters score lower)
    """

    def __init__(self, words: List[str] = None):
        """
        Initialize word list.

        Args:
            words: List of words to include (will be uppercased and validated)
        """
        self.words: List[ScoredWord] = []
        self._length_index: Dict[int, List[ScoredWord]] = {}
        self._first_letter_index: Dict[str, List[ScoredWord]] = {}

        if words:
            self.add_words(words)

    def add_words(self, words: List[str]) -> None:
        """
        Add words to list with automatic scoring.

        Args:
            words: Words to add (will be uppercased and validated)
        """
        for word in words:
            word = word.upper().strip()

            # Validate word
            if not self._is_valid_word(word):
                continue

            # Skip if already exists
            if any(w.text == word for w in self.words):
                continue

            # Score and add
            score = self._score_word(word)
            scored_word = ScoredWord(
                text=word,
                score=score,
                length=len(word)
            )

            self.words.append(scored_word)

            # Update indices
            length = len(word)
            if length not in self._length_index:
                self._length_index[length] = []
            self._length_index[length].append(scored_word)

            first_letter = word[0]
            if first_letter not in self._first_letter_index:
                self._first_letter_index[first_letter] = []
            self._first_letter_index[first_letter].append(scored_word)

        # Sort indices by score (descending)
        for words in self._length_index.values():
            words.sort(key=lambda w: w.score, reverse=True)
        for words in self._first_letter_index.values():
            words.sort(key=lambda w: w.score, reverse=True)

    def get_by_length(self, length: int, min_score: int = 0) -> List[ScoredWord]:
        """
        Get all words of specific length.

        Args:
            length: Word length
            min_score: Minimum crossword-ability score

        Returns:
            Words of specified length, sorted by score descending
        """
        words = self._length_index.get(length, [])
        if min_score > 0:
            words = [w for w in words if w.score >= min_score]
        return words

    def get_all(self, min_score: int = 0) -> List[ScoredWord]:
        """
        Get all words.

        Args:
            min_score: Minimum crossword-ability score

        Returns:
            All words, sorted by score descending
        """
        words = self.words.copy()
        if min_score > 0:
            words = [w for w in words if w.score >= min_score]
        return sorted(words, key=lambda w: w.score, reverse=True)

    def _is_valid_word(self, word: str) -> bool:
        """
        Validate word for crossword use.

        Args:
            word: Word to validate

        Returns:
            True if valid crossword word
        """
        # Must be 3-21 letters
        if len(word) < 3 or len(word) > 21:
            return False

        # Must contain only letters
        if not word.isalpha():
            return False

        # Must be all uppercase (after initial conversion)
        if not word.isupper():
            return False

        return True

    def _score_word(self, word: str) -> int:
        """
        Score word for crossword-ability.

        Scoring formula:
        - Common letters: +10 each
        - Regular letters: +5 each
        - Uncommon letters: -15 each
        - Length bonus: +2 per letter
        - Repeated letter penalty: -5 per repetition

        Final score clamped to 1-100.

        Args:
            word: Word to score (must be uppercase)

        Returns:
            Score from 1-100
        """
        score = 0

        # Letter frequency scoring
        common_count = sum(1 for c in word if c in COMMON_LETTERS)
        regular_count = sum(1 for c in word if c in REGULAR_LETTERS)
        uncommon_count = sum(1 for c in word if c in UNCOMMON_LETTERS)

        score += common_count * 10
        score += regular_count * 5
        score -= uncommon_count * 15

        # Length bonus (longer words are generally better for crosswords)
        score += len(word) * 2

        # Repeated letter penalty (diverse letters are better)
        unique_letters = len(set(word))
        repetitions = len(word) - unique_letters
        score -= repetitions * 5

        # Clamp to 1-100
        score = max(1, min(100, score))

        return score

    def __len__(self) -> int:
        """Get number of words in list."""
        return len(self.words)

    def __repr__(self) -> str:
        """String representation."""
        return f"WordList(words={len(self.words)})"

    @classmethod
    def from_file(cls, filepath: str) -> 'WordList':
        """
        Load word list from file.

        Args:
            filepath: Path to text file with one word per line

        Returns:
            WordList loaded from file
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        return cls(words)
