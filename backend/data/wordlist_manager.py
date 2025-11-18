"""
Wordlist management and search utilities.

This module handles loading, caching, and searching local wordlist files
for pattern matching and word validation operations.
"""

import os
from typing import List, Dict


class WordListManager:
    """Manages loading and caching of word list files."""

    def __init__(self, wordlist_dir: str = 'data/wordlists'):
        """
        Initialize word list manager.

        Args:
            wordlist_dir: Directory containing .txt wordlist files
        """
        self.wordlist_dir = wordlist_dir
        self._cache: Dict[str, List[str]] = {}

    def load(self, name: str) -> List[str]:
        """
        Load word list from file (with caching).

        Args:
            name: Wordlist name (without .txt extension)

        Returns:
            List of words (uppercase)

        Raises:
            FileNotFoundError: If wordlist doesn't exist
        """
        # Return cached version if available
        if name in self._cache:
            return self._cache[name]

        filepath = os.path.join(self.wordlist_dir, f"{name}.txt")

        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Wordlist '{name}' not found at {filepath}"
            )

        words = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    words.append(line.upper())

        self._cache[name] = words
        return words

    def list_available(self) -> List[str]:
        """
        List all available wordlists.

        Returns:
            List of wordlist names (without .txt extension)
        """
        if not os.path.exists(self.wordlist_dir):
            return []

        files = os.listdir(self.wordlist_dir)
        return [
            f[:-4]  # Remove .txt extension
            for f in files
            if f.endswith('.txt')
        ]
