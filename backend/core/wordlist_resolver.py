"""
Wordlist Path Resolution Utility

Provides shared logic for resolving wordlist names to absolute file paths.
Eliminates code duplication across route handlers.
"""

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def resolve_wordlist_paths(wordlist_names: List[str], data_dir: Path = None) -> List[str]:
    """
    Resolve wordlist names to absolute file paths.

    Supports:
    - Simple names: "comprehensive" → "data/wordlists/comprehensive.txt"
    - Category paths: "core/common_3_letter" → "data/wordlists/core/common_3_letter.txt"
    - Absolute paths: "/abs/path/to/wordlist.txt" (passed through)

    Args:
        wordlist_names: List of wordlist names or paths
        data_dir: Base directory for wordlists (defaults to project data/wordlists/)

    Returns:
        List of absolute paths to existing wordlist files

    Example:
        >>> resolve_wordlist_paths(["comprehensive", "core/standard"])
        ['/path/to/data/wordlists/comprehensive.txt',
         '/path/to/data/wordlists/core/standard.txt']
    """
    if data_dir is None:
        # Default to project data/wordlists directory
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / "data" / "wordlists"

    wordlist_paths = []

    for wordlist_name in wordlist_names:
        resolved_path = _resolve_single_wordlist(wordlist_name, data_dir)
        if resolved_path:
            wordlist_paths.append(str(resolved_path))
        else:
            logger.warning(f"Wordlist not found: {wordlist_name}")

    return wordlist_paths


def _resolve_single_wordlist(wordlist_name: str, data_dir: Path) -> Path:
    """
    Resolve a single wordlist name to an absolute path.

    Args:
        wordlist_name: Wordlist name or path
        data_dir: Base wordlist directory

    Returns:
        Absolute path to wordlist file, or None if not found
    """
    # Handle absolute paths (pass through if they exist)
    if Path(wordlist_name).is_absolute():
        path = Path(wordlist_name)
        if path.exists():
            return path
        else:
            return None

    # Handle paths with category (e.g., "core/standard")
    if "/" in wordlist_name or "\\" in wordlist_name:
        # Treat as relative path from data_dir
        wordlist_path = data_dir / f"{wordlist_name}.txt"
        if wordlist_path.exists():
            return wordlist_path
        else:
            # Try as absolute path (fallback)
            path = Path(wordlist_name)
            if path.exists():
                return path
            return None

    # Simple name without category
    # Try in root first
    wordlist_path = data_dir / f"{wordlist_name}.txt"
    if wordlist_path.exists():
        return wordlist_path

    # Try in common locations (core/, themed/, etc.)
    common_categories = ["core", "themed", "external", "custom"]
    for category in common_categories:
        wordlist_path = data_dir / category / f"{wordlist_name}.txt"
        if wordlist_path.exists():
            return wordlist_path

    # Not found
    return None


def get_default_wordlist_paths(data_dir: Path = None) -> List[str]:
    """
    Get paths to default wordlists (comprehensive.txt).

    Args:
        data_dir: Base directory for wordlists

    Returns:
        List containing path to comprehensive.txt, or empty list if not found
    """
    return resolve_wordlist_paths(["comprehensive"], data_dir)
