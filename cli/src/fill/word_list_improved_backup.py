"""
Word list management with crossword-ability scoring - IMPROVED VERSION.

Manages word lists, scores words based on letter frequency and commonality,
and provides efficient lookup operations for autofill.

Key improvements:
- Detects and penalizes gibberish patterns (AAAAA, III, etc.)
- Better scoring algorithm that prefers real words
- Quality filtering to exclude low-quality fills
"""

from typing import List, Dict
from dataclasses import dataclass
import pickle
from pathlib import Path

# Letter frequency scoring (based on common crossword usage)
COMMON_LETTERS = set("EARIOTNS")  # Very common, good for crosswords
REGULAR_LETTERS = set("DHCLUMPFGYBWKV")  # Regular usage
UNCOMMON_LETTERS = set("JQXZ")  # Difficult letters


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
    - Gibberish detection (extreme repetition heavily penalized)
    """

    def __init__(self, words: List[str] = None, progress_callback=None):
        """
        Initialize word list.

        Args:
            words: List of words to include (will be uppercased and validated)
            progress_callback: Optional callback(current, total) for progress updates
        """
        self.words: List[ScoredWord] = []
        self._length_index: Dict[int, List[ScoredWord]] = {}
        self._first_letter_index: Dict[str, List[ScoredWord]] = {}

        if words:
            self.add_words(words, progress_callback)

    def add_words(self, words: List[str], progress_callback=None) -> None:
        """
        Add words to list with automatic scoring.

        Args:
            words: Words to add (will be uppercased and validated)
            progress_callback: Optional callback(current, total) for progress updates
        """
        total = len(words)
        seen = set()  # O(1) duplicate checking

        for idx, word in enumerate(words):
            word = word.upper().strip()

            # Validate word
            if not self._is_valid_word(word):
                continue

            # Skip if already exists (O(1) with set)
            if word in seen:
                continue
            seen.add(word)

            # Score and add
            score = self._score_word(word)
            scored_word = ScoredWord(text=word, score=score, length=len(word))

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

            # Report progress every 5000 words
            if progress_callback and idx > 0 and idx % 5000 == 0:
                progress_callback(idx, total)

        # Final progress update
        if progress_callback:
            progress_callback(total, total)

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

    def _is_quality_word(self, word: str) -> bool:
        """
        Check if word meets quality standards (not gibberish).

        Args:
            word: Word to check (must be uppercase)

        Returns:
            True if word passes quality checks
        """
        # Check for extreme repetition (gibberish detection)
        unique_letters = len(set(word))
        repetition_ratio = 1 - (unique_letters / len(word))

        # If more than 66% of letters are the same, it's likely gibberish
        if repetition_ratio > 0.66:
            return False

        # Check if it's all the same letter (AAA, IIII, etc.)
        if unique_letters == 1:
            return False

        # Score-based quality check
        score = self._score_word(word)
        return score >= 20  # Minimum quality threshold

    def _calculate_gibberish_penalty(self, word: str) -> int:
        """
        Calculate penalty for gibberish-like patterns.

        Args:
            word: Word to check (uppercase)

        Returns:
            Penalty value (0 for normal words, high for gibberish)
        """
        unique_letters = len(set(word))
        word_length = len(word)

        # Calculate repetition ratio
        repetition_ratio = 1 - (unique_letters / word_length)

        # Extreme penalty for single-letter words (AAA, III, etc.)
        if unique_letters == 1:
            return 100  # Maximum penalty

        # For 3-letter words, be more lenient with double letters
        if word_length == 3:
            if unique_letters == 2:  # One double letter (like AAH, ADD, ALL)
                return 0  # No penalty for valid 3-letter words with doubles
            elif unique_letters == 1:  # All same (AAA, III)
                return 100  # Maximum penalty

        # High penalty for extreme repetition (>80% same letter) in longer words
        if word_length >= 4 and repetition_ratio > 0.8:
            return 80

        # Moderate penalty for high repetition (>66% same letter) in longer words
        if word_length >= 4 and repetition_ratio > 0.66:
            return 50

        # Check for specific patterns in longer words
        # Count the most frequent letter
        letter_counts = {}
        for letter in word:
            letter_counts[letter] = letter_counts.get(letter, 0) + 1
        max_count = max(letter_counts.values())

        # For words 4+ letters, if one letter appears more than 66% of the time, apply penalty
        if word_length >= 4 and max_count / word_length > 0.66:
            return int(40 * (max_count / word_length))

        return 0  # No gibberish penalty

    def _score_word(self, word: str) -> int:
        """
        Score word for crossword-ability with improved gibberish detection.

        Scoring formula:
        - Base score from letters and length
        - Heavy penalties for gibberish patterns
        - Bonus for letter diversity
        - Special handling for 3-letter words
        - Final score clamped to 1-100

        Args:
            word: Word to score (must be uppercase)

        Returns:
            Score from 1-100
        """
        score = 0
        word_length = len(word)

        # Letter frequency scoring
        common_count = sum(1 for c in word if c in COMMON_LETTERS)
        regular_count = sum(1 for c in word if c in REGULAR_LETTERS)
        uncommon_count = sum(1 for c in word if c in UNCOMMON_LETTERS)

        score += common_count * 10
        score += regular_count * 5

        # Reduced penalty for uncommon letters in short words
        if word_length <= 4:
            score -= uncommon_count * 10  # Less penalty for short words
        else:
            score -= uncommon_count * 15  # Normal penalty

        # Length bonus (longer words are generally better for crosswords)
        score += word_length * 2

        # Calculate letter diversity
        unique_letters = len(set(word))
        diversity_ratio = unique_letters / word_length

        # Special handling for 3-letter words
        if word_length == 3:
            if unique_letters == 2:  # Double letter (AAH, ADD, etc.)
                score += 10  # Bonus for valid 3-letter words
            elif unique_letters == 3:  # All different
                score += 15  # Even better
            # unique_letters == 1 gets gibberish penalty below

        # Diversity bonus/penalty for longer words
        elif word_length >= 4:
            if diversity_ratio >= 0.8:  # Very diverse (80%+ unique)
                score += 15
            elif diversity_ratio >= 0.6:  # Good diversity
                score += 5
            elif diversity_ratio < 0.4:  # Poor diversity
                score -= 20

        # Apply gibberish penalty
        gibberish_penalty = self._calculate_gibberish_penalty(word)
        score -= gibberish_penalty

        # Reduced repetition penalty for valid words
        if gibberish_penalty == 0:  # Only apply if not gibberish
            repetitions = word_length - unique_letters
            score -= repetitions * 2  # Minimal penalty for valid repeated letters

        # Bonus for known good crossword patterns
        # Words with mostly common letters and good diversity get a bonus
        if common_count >= word_length * 0.5 and diversity_ratio > 0.6:
            score += 10

        # Special boost for words with JAZZ-like patterns (valid uncommon combinations)
        # If it has uncommon letters but still good diversity, moderate the penalty
        if uncommon_count >= 2 and diversity_ratio >= 0.75:
            score += 15  # Compensate for uncommon letter penalty

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
    def from_file(
        cls, filepath: str, progress_callback=None, use_cache=True
    ) -> "WordList":
        """
        Load word list from file, using cache if available.

        Args:
            filepath: Path to text file with one word per line
            progress_callback: Optional callback(current, total) for progress updates
            use_cache: If True, check for .pkl cache file first (default: True)

        Returns:
            WordList loaded from file or cache

        Raises:
            ValueError: If filepath is invalid or inaccessible
            FileNotFoundError: If file does not exist
        """
        # Sanitize filepath to prevent path traversal
        try:
            # Resolve to absolute path and normalize
            resolved_path = Path(filepath).resolve()

            # Verify file exists and is a regular file
            if not resolved_path.exists():
                raise FileNotFoundError(f"Word list file not found: {filepath}")

            if not resolved_path.is_file():
                raise ValueError(f"Path is not a regular file: {filepath}")

            # Check for cache file (.pkl)
            if use_cache:
                cache_path = resolved_path.with_suffix(".pkl")

                if cache_path.exists():
                    # Check if cache is newer than source file
                    source_mtime = resolved_path.stat().st_mtime
                    cache_mtime = cache_path.stat().st_mtime

                    if cache_mtime >= source_mtime:
                        # Cache is up-to-date, use it
                        try:
                            return cls.from_cache(str(cache_path))
                        except (ValueError, FileNotFoundError) as e:
                            # Cache is corrupt, fall through to text loading
                            import sys

                            print(
                                f"Warning: Cache corrupted, rebuilding: {e}",
                                file=sys.stderr,
                            )

            # No cache or cache disabled - load from text file
            # Check file size (prevent loading huge files)
            file_size = resolved_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError(
                    f"Word list file too large (max 100MB): {file_size / 1024 / 1024:.1f}MB"
                )

            # Read with proper error handling
            with open(resolved_path, "r", encoding="utf-8") as f:
                words = [line.strip() for line in f if line.strip()]

            return cls(words, progress_callback)

        except (OSError, IOError) as e:
            raise ValueError(f"Failed to read word list from {filepath}: {e}")

    def to_cache(self, cache_path: str) -> None:
        """
        Save word list to binary cache file for fast loading.

        Args:
            cache_path: Path to save cache file (.pkl)

        Raises:
            IOError: If cache file cannot be written
        """
        cache_path = Path(cache_path)

        # Create parent directory if needed
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize entire WordList state
        cache_data = {
            "words": self.words,
            "length_index": self._length_index,
            "first_letter_index": self._first_letter_index,
            "version": "1.0",  # For future compatibility
        }

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except (OSError, IOError) as e:
            raise IOError(f"Failed to write cache to {cache_path}: {e}")

    @classmethod
    def from_cache(cls, cache_path: str) -> "WordList":
        """
        Load word list from binary cache file.

        Args:
            cache_path: Path to cache file (.pkl)

        Returns:
            WordList loaded from cache

        Raises:
            FileNotFoundError: If cache file does not exist
            ValueError: If cache file is invalid or corrupt
        """
        cache_path = Path(cache_path)

        if not cache_path.exists():
            raise FileNotFoundError(f"Cache file not found: {cache_path}")

        if not cache_path.is_file():
            raise ValueError(f"Cache path is not a file: {cache_path}")

        try:
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)

            # Validate cache structure
            if not isinstance(cache_data, dict):
                raise ValueError("Invalid cache format")

            required_keys = {"words", "length_index", "first_letter_index"}
            if not required_keys.issubset(cache_data.keys()):
                raise ValueError(
                    f"Cache missing required keys: {required_keys - cache_data.keys()}"
                )

            # Create instance and restore state
            instance = cls()
            instance.words = cache_data["words"]
            instance._length_index = cache_data["length_index"]
            instance._first_letter_index = cache_data["first_letter_index"]

            return instance

        except (OSError, IOError) as e:
            raise ValueError(f"Failed to read cache from {cache_path}: {e}")
        except pickle.UnpicklingError as e:
            raise ValueError(f"Cache file is corrupt: {e}")
