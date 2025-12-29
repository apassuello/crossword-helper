"""
Wordlist management and search utilities.

This module handles loading, caching, and searching local wordlist files
for pattern matching and word validation operations. Enhanced to support
categories, metadata, and advanced operations.
"""

import os
import json
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter
from pathlib import Path


class WordListManager:
    """Enhanced wordlist manager with metadata and category support."""

    def __init__(self, wordlist_dir: str = 'data/wordlists'):
        """
        Initialize word list manager.

        Args:
            wordlist_dir: Root directory containing wordlist categories
        """
        self.wordlist_dir = Path(wordlist_dir)
        self._cache: Dict[str, List[str]] = {}
        self._metadata: Optional[Dict[str, Any]] = None
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata.json file."""
        metadata_path = self.wordlist_dir / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self._metadata = json.load(f)
        else:
            self._metadata = {'wordlists': {}, 'categories': {}, 'tags': {}}

    def save_metadata(self) -> None:
        """Save metadata back to file."""
        metadata_path = self.wordlist_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(self._metadata, f, indent=2)

    def load(self, name: str) -> List[str]:
        """
        Load word list from file (with caching).
        Supports category paths like 'core/common_3_letter'.

        Args:
            name: Wordlist name (can include category path)

        Returns:
            List of words (uppercase)

        Raises:
            FileNotFoundError: If wordlist doesn't exist
        """
        # Return cached version if available
        if name in self._cache:
            return self._cache[name]

        # Try direct path first, then with .txt extension
        filepath = self.wordlist_dir / name
        if not filepath.suffix:
            filepath = filepath.with_suffix('.txt')

        # Also try legacy flat structure for backward compatibility
        if not filepath.exists():
            filepath = self.wordlist_dir / f"{name}.txt"

        if not filepath.exists():
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

    def list_all(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available wordlists with metadata.

        Args:
            category: Optional category filter

        Returns:
            List of wordlist info dictionaries
        """
        wordlists = []

        # Walk through directory structure
        for root, dirs, files in os.walk(self.wordlist_dir):
            root_path = Path(root)

            # Skip metadata.json
            txt_files = [f for f in files if f.endswith('.txt')]

            for filename in txt_files:
                # Get relative path from wordlist_dir
                rel_path = root_path.relative_to(self.wordlist_dir)

                # Construct wordlist key
                if rel_path == Path('.'):
                    wordlist_key = filename[:-4]
                else:
                    wordlist_key = str(rel_path / filename[:-4])

                # Normalize path separators
                wordlist_key = wordlist_key.replace('\\', '/')

                # Get metadata if available, with defaults for missing fields
                default_metadata = {
                    'name': filename[:-4].replace('_', ' ').title(),
                    'category': str(rel_path) if rel_path != Path('.') else 'uncategorized',
                    'description': 'No description available'
                }
                actual_metadata = self._metadata['wordlists'].get(wordlist_key, {})
                # Merge defaults with actual metadata (actual takes precedence)
                metadata = {**default_metadata, **actual_metadata}

                # Apply category filter if specified
                if category and metadata.get('category') != category:
                    continue

                # Add file info
                filepath = root_path / filename
                metadata['key'] = wordlist_key
                metadata['filepath'] = str(filepath)
                metadata['word_count'] = len(self.load(wordlist_key)) if wordlist_key in self._cache else None

                wordlists.append(metadata)

        return wordlists

    def list_available(self) -> List[str]:
        """
        List all available wordlist keys (backward compatibility).

        Returns:
            List of wordlist keys
        """
        return [wl['key'] for wl in self.list_all()]

    def get_categories(self) -> Dict[str, Any]:
        """Get all category definitions."""
        return self._metadata.get('categories', {})

    def get_tags(self) -> Dict[str, Any]:
        """Get all tag definitions."""
        return self._metadata.get('tags', {})

    def get_wordlist_info(self, name: str) -> Dict[str, Any]:
        """Get metadata for a specific wordlist."""
        info = self._metadata['wordlists'].get(name, {})
        info['key'] = name
        info['word_count'] = len(self.load(name))

        # Ensure 'name' field exists (generate from key if missing)
        if 'name' not in info:
            # Generate human-readable name from key
            # e.g., "top_200k" -> "Top 200k", "core/standard" -> "Standard"
            display_name = name.split('/')[-1]  # Remove path prefix
            display_name = display_name.replace('_', ' ').title()
            info['name'] = display_name

        return info

    def analyze_words(self, name: str) -> Dict[str, Any]:
        """
        Analyze a wordlist for statistics.

        Args:
            name: Wordlist name

        Returns:
            Dictionary with word statistics
        """
        words = self.load(name)

        # Length distribution
        length_dist = Counter(len(word) for word in words)

        # Letter frequency
        letter_freq = Counter()
        for word in words:
            letter_freq.update(word)

        # Common starting/ending letters
        start_letters = Counter(word[0] for word in words if word)
        end_letters = Counter(word[-1] for word in words if word)

        return {
            'total_words': len(words),
            'length_distribution': dict(length_dist),
            'letter_frequency': dict(letter_freq.most_common(26)),
            'most_common_starts': dict(start_letters.most_common(10)),
            'most_common_ends': dict(end_letters.most_common(10)),
            'average_length': sum(len(w) for w in words) / len(words) if words else 0,
            'unique_letters': len(letter_freq)
        }

    def search_pattern(self, pattern: str, wordlists: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """
        Search for words matching a pattern across wordlists.

        Args:
            pattern: Pattern with ? for wildcards
            wordlists: List of wordlist names to search (None = all)

        Returns:
            List of (word, source_wordlist) tuples
        """
        if wordlists is None:
            wordlists = self.list_available()

        results = []
        pattern_upper = pattern.upper()
        pattern_len = len(pattern)

        for wordlist_name in wordlists:
            try:
                words = self.load(wordlist_name)
                for word in words:
                    if len(word) != pattern_len:
                        continue

                    # Check pattern match
                    if all(p == '?' or p == w for p, w in zip(pattern_upper, word)):
                        results.append((word, wordlist_name))
            except FileNotFoundError:
                continue

        return results

    def add_words(self, name: str, words: List[str], create: bool = False) -> None:
        """
        Add words to a wordlist.

        Args:
            name: Wordlist name
            words: Words to add
            create: Create wordlist if it doesn't exist
        """
        filepath = self.wordlist_dir / name
        if not filepath.suffix:
            filepath = filepath.with_suffix('.txt')

        if not filepath.exists() and not create:
            raise FileNotFoundError(f"Wordlist '{name}' not found")

        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Load existing words or start empty
        existing = set(self.load(name)) if filepath.exists() else set()

        # Add new words
        new_words = set(word.upper() for word in words)
        combined = existing | new_words

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            for word in sorted(combined):
                f.write(f"{word}\n")

        # Update cache
        self._cache[name] = sorted(combined)

        # Update metadata
        if name not in self._metadata['wordlists']:
            self._metadata['wordlists'][name] = {
                'name': name.replace('_', ' ').title(),
                'category': str(filepath.parent.relative_to(self.wordlist_dir)),
                'description': 'User-created wordlist',
                'created': str(Path(filepath).stat().st_mtime if filepath.exists() else 'now')
            }
        self._metadata['wordlists'][name]['last_modified'] = 'now'
        self.save_metadata()
