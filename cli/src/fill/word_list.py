"""
Word list management with crossword-ability scoring.

Manages word lists, scores words based on letter frequency and commonality,
and provides efficient lookup operations for autofill.
"""

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

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
    """

    def __init__(self, words: List[Union[str, Tuple[str, Optional[int]]]] = None, progress_callback=None):
        """
        Initialize word list.

        Args:
            words: List of words to include (will be uppercased and validated).
                Entries may be plain strings or (word, score) tuples; a tuple's
                score (e.g. from a scored wordlist file) overrides the computed
                letter-frequency score.
            progress_callback: Optional callback(current, total) for progress updates
        """
        self.words: List[ScoredWord] = []
        self._length_index: Dict[int, List[ScoredWord]] = {}
        self._first_letter_index: Dict[str, List[ScoredWord]] = {}

        if words:
            self.add_words(words, progress_callback)

    def add_words(self, words: List[Union[str, Tuple[str, Optional[int]]]], progress_callback=None) -> None:
        """
        Add words to list with automatic scoring.

        Args:
            words: Words to add (will be uppercased and validated). Entries may
                be plain strings or (word, score) tuples; a tuple's score (e.g.
                from a scored wordlist file) overrides the computed score.
            progress_callback: Optional callback(current, total) for progress updates
        """
        total = len(words)
        # Start with existing words to prevent duplicates
        seen = {sw.text for sw in self.words}

        for idx, item in enumerate(words):
            if isinstance(item, tuple):
                word, file_score = item
            else:
                word, file_score = item, None
            word = word.upper().strip()

            # Validate word
            if not self._is_valid_word(word):
                continue

            # Skip if already exists (O(1) with set)
            if word in seen:
                continue
            seen.add(word)

            # Score and add (file-supplied score wins over computed score)
            score = file_score if file_score is not None else self._score_word(word)
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

    def _score_word(self, word: str) -> int:
        """
        Score word for crossword-ability.

        Scoring formula:
        - Common letters: +10 each
        - Regular letters: +5 each
        - Uncommon letters: -15 each
        - Length bonus: +2 per letter
        - Repeated letter penalty: -10 per repetition
        - Adjacent repeat penalty: -20 per instance (penalizes TT, SS, etc.)

        Final score clamped to 1-150.

        Args:
            word: Word to score (must be uppercase)

        Returns:
            Score from 1-150
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
        score -= repetitions * 10

        # Heavy penalty for adjacent repeated letters
        # Words like AIRMATTRESS (has TT, SS) are constraining for crossings
        adjacent_repeats = sum(1 for i in range(len(word) - 1) if word[i] == word[i + 1])
        score -= adjacent_repeats * 20  # Each double letter: -20 points

        score = max(1, min(150, score))

        return score

    def __len__(self) -> int:
        """Get number of words in list."""
        return len(self.words)

    def __repr__(self) -> str:
        """String representation."""
        return f"WordList(words={len(self.words)})"

    @staticmethod
    def parse_line(line: str) -> Optional[Tuple[str, Optional[int]]]:
        """
        Parse a single wordlist line.

        Supported formats:
        - Plain: "WORD"
        - Semicolon-scored: "WORD;50" (comprehensive_scored.txt, *.dict files)
        - Comma-scored: "word,50" (broda.owl style CSV)

        Args:
            line: Stripped, non-empty, non-comment line

        Returns:
            (word, score) tuple where score is None for plain lines, or
            None if the line is malformed (e.g. a "word,score" CSV header
            or a scored line with a non-numeric score).
        """
        for sep in (";", ","):
            if sep in line:
                parts = line.split(sep)
                word = parts[0].strip()
                try:
                    score = int(float(parts[1].strip()))
                except (ValueError, IndexError):
                    # Malformed scored line (e.g. CSV header "word,score") - skip
                    return None
                return (word, score)
        return (line, None)

    @classmethod
    def from_file(cls, filepath: str, progress_callback=None, use_cache=True) -> "WordList":
        """
        Load word list from file, using cache if available.

        Supports plain wordlists (one word per line), semicolon-scored
        ("WORD;50"), and comma-scored ("word,50") formats. Scores from
        scored files are kept and override the computed letter score.

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
                raise ValueError(f"Word list file too large (max 100MB): {file_size / 1024 / 1024:.1f}MB")

            # Read with proper error handling
            # Parses plain, "WORD;SCORE" and "word,score" line formats
            words = []
            with open(resolved_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parsed = cls.parse_line(line)
                    if parsed:
                        words.append(parsed)

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
                raise ValueError(f"Cache missing required keys: {required_keys - cache_data.keys()}")

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
