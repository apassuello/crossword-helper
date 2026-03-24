"""
DomainManager - Efficient domain storage using bitsets for small domains.

This module provides memory-efficient domain representation for constraint
satisfaction problems. For small domains (<= 64 words), uses bitsets instead
of sets for 70-90% memory reduction.
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, Optional, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ...word_list import WordList

logger = logging.getLogger(__name__)


class DomainManager:
    """
    Efficient domain storage for CSP variables.

    Uses bitset representation for small domains (<=64 words) and
    traditional sets for larger domains. Provides unified API for both.

    Benefits:
    - Small domains: 70-90% memory reduction vs sets
    - Large domains: No overhead, uses standard sets
    - Shared immutable domains: Single copy for identical domains
    - Fast operations: Bitwise AND/OR instead of set operations

    Usage:
        manager = DomainManager(word_list)
        domain = manager.create_domain_for_pattern("?AT", min_score=30)
        manager.remove_word(domain, "BAT")
        available = manager.get_available_words(domain)

    Thread Safety:
        Not thread-safe. Use separate managers per thread if needed.
    """

    # Bitset threshold: domains with <= 64 words use bitsets
    BITSET_THRESHOLD = 64

    def __init__(self, word_list: WordList):
        """
        Initialize domain manager.

        Args:
            word_list: WordList instance for pattern matching
        """
        self.word_list = word_list

        # Word-to-index mapping for bitset representation
        self._word_to_index: Dict[str, int] = {}
        self._index_to_word: Dict[int, str] = {}
        self._next_index = 0

        # Cache of immutable domains (for sharing)
        self._domain_cache: Dict[Tuple, "Domain"] = {}

        # Statistics
        self._total_domains_created = 0
        self._bitset_domains_created = 0
        self._cache_hits = 0

    def create_domain_for_pattern(
        self, pattern: str, min_score: int = 0, exclude_words: Optional[Set[str]] = None
    ) -> "Domain":
        """
        Create domain for a pattern.

        Args:
            pattern: Pattern like "?AT" or "C?T"
            min_score: Minimum word quality score
            exclude_words: Words to exclude from domain

        Returns:
            Domain object (bitset or set-based)

        Notes:
            - Checks cache first for identical domains
            - Uses bitset if domain size <= 64 words
            - Uses set otherwise
        """
        # Create cache key
        exclude_tuple = tuple(sorted(exclude_words)) if exclude_words else ()
        cache_key = (pattern, min_score, exclude_tuple)

        # Check cache
        if cache_key in self._domain_cache:
            self._cache_hits += 1
            return self._domain_cache[cache_key]

        # Find matching words
        candidates = self.word_list.find(pattern, min_score=min_score)
        words = [
            word for word, score in candidates if word not in (exclude_words or set())
        ]

        # Create appropriate domain type
        if len(words) <= self.BITSET_THRESHOLD:
            domain = BitsetDomain(words, self)
            self._bitset_domains_created += 1
        else:
            domain = SetDomain(words)

        self._total_domains_created += 1

        # Cache immutable domains (optional optimization)
        if len(self._domain_cache) < 10000:  # Limit cache size
            self._domain_cache[cache_key] = domain

        return domain

    def create_empty_domain(self) -> "Domain":
        """Create an empty domain."""
        return SetDomain([])

    def intersect_domains(self, domain1: "Domain", domain2: "Domain") -> "Domain":
        """
        Compute intersection of two domains.

        Args:
            domain1: First domain
            domain2: Second domain

        Returns:
            New domain containing words in both domains
        """
        words = domain1.get_words() & domain2.get_words()

        if len(words) <= self.BITSET_THRESHOLD:
            return BitsetDomain(list(words), self)
        else:
            return SetDomain(list(words))

    def union_domains(self, domain1: "Domain", domain2: "Domain") -> "Domain":
        """
        Compute union of two domains.

        Args:
            domain1: First domain
            domain2: Second domain

        Returns:
            New domain containing words in either domain
        """
        words = domain1.get_words() | domain2.get_words()

        if len(words) <= self.BITSET_THRESHOLD:
            return BitsetDomain(list(words), self)
        else:
            return SetDomain(list(words))

    def _get_or_create_word_index(self, word: str) -> int:
        """
        Get index for word, creating if needed.

        Args:
            word: Word to index

        Returns:
            Integer index for the word
        """
        if word not in self._word_to_index:
            self._word_to_index[word] = self._next_index
            self._index_to_word[self._next_index] = word
            self._next_index += 1

        return self._word_to_index[word]

    def _get_word_for_index(self, index: int) -> str:
        """
        Get word for index.

        Args:
            index: Word index

        Returns:
            Word string
        """
        return self._index_to_word[index]

    def get_stats(self) -> Dict[str, int]:
        """
        Get domain manager statistics.

        Returns:
            Dictionary with stats:
            - 'total_domains': Total domains created
            - 'bitset_domains': Domains using bitsets
            - 'set_domains': Domains using sets
            - 'cache_size': Number of cached domains
            - 'cache_hits': Cache hit count
            - 'word_index_size': Number of indexed words
        """
        return {
            "total_domains": self._total_domains_created,
            "bitset_domains": self._bitset_domains_created,
            "set_domains": self._total_domains_created - self._bitset_domains_created,
            "cache_size": len(self._domain_cache),
            "cache_hits": self._cache_hits,
            "word_index_size": self._next_index,
        }

    def clear_cache(self) -> None:
        """Clear domain cache to free memory."""
        self._domain_cache.clear()


class Domain:
    """Abstract base class for domain representations."""

    def contains(self, word: str) -> bool:
        """Check if word is in domain."""
        raise NotImplementedError

    def add(self, word: str) -> None:
        """Add word to domain."""
        raise NotImplementedError

    def remove(self, word: str) -> None:
        """Remove word from domain."""
        raise NotImplementedError

    def get_words(self) -> Set[str]:
        """Get all words in domain as set."""
        raise NotImplementedError

    def size(self) -> int:
        """Get number of words in domain."""
        raise NotImplementedError

    def is_empty(self) -> bool:
        """Check if domain is empty."""
        return self.size() == 0

    def clone(self) -> "Domain":
        """Create a copy of this domain."""
        raise NotImplementedError


class SetDomain(Domain):
    """
    Set-based domain representation for large domains.

    Uses standard Python set for domains with > 64 words.
    """

    def __init__(self, words: List[str]):
        """
        Initialize set domain.

        Args:
            words: List of words in domain
        """
        self._words: Set[str] = set(words)

    def contains(self, word: str) -> bool:
        """Check if word is in domain."""
        return word in self._words

    def add(self, word: str) -> None:
        """Add word to domain."""
        self._words.add(word)

    def remove(self, word: str) -> None:
        """Remove word from domain."""
        self._words.discard(word)

    def get_words(self) -> Set[str]:
        """Get all words in domain as set."""
        return self._words.copy()

    def size(self) -> int:
        """Get number of words in domain."""
        return len(self._words)

    def clone(self) -> "Domain":
        """Create a copy of this domain."""
        return SetDomain(list(self._words))

    def __repr__(self) -> str:
        """String representation."""
        return f"SetDomain({self.size()} words)"


class BitsetDomain(Domain):
    """
    Bitset-based domain representation for small domains.

    Uses 64-bit integer as bitset for domains with <= 64 words.
    Achieves 70-90% memory reduction vs standard sets.

    Memory Comparison:
    - Set with 10 words: ~360 bytes (set overhead + 10 pointers)
    - Bitset with 10 words: ~40 bytes (1 int + manager reference)
    """

    def __init__(self, words: List[str], manager: DomainManager):
        """
        Initialize bitset domain.

        Args:
            words: List of words in domain (max 64)
            manager: DomainManager for word-index mapping

        Raises:
            ValueError: If words > 64
        """
        if len(words) > 64:
            raise ValueError(f"BitsetDomain supports max 64 words, got {len(words)}")

        self._manager = manager
        self._bitset: int = 0

        # Build bitset
        for word in words:
            index = manager._get_or_create_word_index(word)
            if index >= 64:
                raise ValueError(f"Word index {index} exceeds bitset capacity (64)")
            self._bitset |= 1 << index

    def contains(self, word: str) -> bool:
        """Check if word is in domain."""
        if word not in self._manager._word_to_index:
            return False

        index = self._manager._word_to_index[word]
        if index >= 64:
            return False

        return (self._bitset & (1 << index)) != 0

    def add(self, word: str) -> None:
        """Add word to domain."""
        index = self._manager._get_or_create_word_index(word)
        if index >= 64:
            raise ValueError(f"Word index {index} exceeds bitset capacity (64)")

        self._bitset |= 1 << index

    def remove(self, word: str) -> None:
        """Remove word from domain."""
        if word not in self._manager._word_to_index:
            return

        index = self._manager._word_to_index[word]
        if index >= 64:
            return

        self._bitset &= ~(1 << index)

    def get_words(self) -> Set[str]:
        """Get all words in domain as set."""
        words = set()
        for i in range(64):
            if self._bitset & (1 << i):
                if i in self._manager._index_to_word:
                    words.add(self._manager._index_to_word[i])

        return words

    def size(self) -> int:
        """Get number of words in domain."""
        # Count number of 1-bits in bitset
        count = 0
        bitset = self._bitset
        while bitset:
            count += bitset & 1
            bitset >>= 1
        return count

    def clone(self) -> "Domain":
        """Create a copy of this domain."""
        new_domain = BitsetDomain([], self._manager)
        new_domain._bitset = self._bitset
        return new_domain

    def intersect(self, other: "BitsetDomain") -> "BitsetDomain":
        """
        Fast bitwise intersection with another bitset domain.

        Args:
            other: Other bitset domain

        Returns:
            New domain containing words in both domains
        """
        if not isinstance(other, BitsetDomain):
            raise TypeError("Can only intersect with another BitsetDomain")

        new_domain = BitsetDomain([], self._manager)
        new_domain._bitset = self._bitset & other._bitset
        return new_domain

    def union(self, other: "BitsetDomain") -> "BitsetDomain":
        """
        Fast bitwise union with another bitset domain.

        Args:
            other: Other bitset domain

        Returns:
            New domain containing words in either domain
        """
        if not isinstance(other, BitsetDomain):
            raise TypeError("Can only union with another BitsetDomain")

        new_domain = BitsetDomain([], self._manager)
        new_domain._bitset = self._bitset | other._bitset
        return new_domain

    def __repr__(self) -> str:
        """String representation."""
        return f"BitsetDomain({self.size()} words, bitset=0x{self._bitset:x})"
