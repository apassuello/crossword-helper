#!/usr/bin/env python3
"""
Script to normalize external wordlists into the project's standard format.

Handles various input formats:
- Plain text (one word per line)
- Semicolon-delimited (word;score)
- Comma-delimited CSV (word,score)
- OWL format (word,score with header)

Output formats:
- Plain text: uppercase, one word per line (3-21 letters, alpha only)
- Scored text: WORD;score format for preserving external scores
"""

import re
from pathlib import Path
from typing import Tuple, Optional


def parse_line(line: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parse a line that may contain word and optional score.

    Supports formats:
    - "word" -> (WORD, None)
    - "word;50" -> (WORD, 50)
    - "word,50" -> (WORD, 50)
    - "WORD;50" -> (WORD, 50)

    Returns (None, None) if line is invalid.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None

    # Skip header lines
    if line.lower() in ('word', 'word,score', 'word;score'):
        return None, None

    score = None
    word = None

    # Try semicolon delimiter first
    if ';' in line:
        parts = line.split(';', 1)
        word = parts[0].strip()
        if len(parts) > 1 and parts[1].strip().isdigit():
            score = int(parts[1].strip())
    # Try comma delimiter
    elif ',' in line:
        parts = line.split(',', 1)
        word = parts[0].strip()
        if len(parts) > 1 and parts[1].strip().isdigit():
            score = int(parts[1].strip())
    else:
        word = line

    if not word:
        return None, None

    # Normalize: uppercase, strip non-alpha characters
    word = word.upper()
    # Remove spaces, hyphens, apostrophes (common in phrase entries)
    word = re.sub(r'[^A-Z]', '', word)

    # Validate: 3-21 letters
    if len(word) < 3 or len(word) > 21:
        return None, None

    return word, score


def normalize_wordlist(
    input_path: str,
    output_path: str,
    preserve_scores: bool = False,
    progress_callback=None
) -> Tuple[int, int]:
    """
    Normalize a wordlist file to the project's standard format.

    Args:
        input_path: Path to input wordlist file
        output_path: Path for normalized output file
        preserve_scores: If True, output WORD;score format; else plain WORD
        progress_callback: Optional callback(current, total)

    Returns:
        Tuple of (total_processed, unique_words)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Read all lines
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    total = len(lines)
    seen = set()
    output_lines = []

    for idx, line in enumerate(lines):
        word, score = parse_line(line)

        if word is None or word in seen:
            continue

        seen.add(word)

        if preserve_scores and score is not None:
            output_lines.append(f"{word};{score}\n")
        else:
            output_lines.append(f"{word}\n")

        if progress_callback and idx > 0 and idx % 10000 == 0:
            progress_callback(idx, total)

    if progress_callback:
        progress_callback(total, total)

    # Sort alphabetically
    output_lines.sort()

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    return total, len(seen)


def normalize_all_external():
    """Normalize all external wordlists in the external/ directory."""
    base_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'wordlists'
    external_dir = base_dir / 'external'
    normalized_dir = external_dir / 'normalized'
    normalized_dir.mkdir(exist_ok=True)

    # Wordlist configurations
    # Format: (input_file, output_file, preserve_scores)
    wordlists = [
        ('christophsjones_scored.txt', 'christophsjones.txt', True),
        ('ben_crosshatch_scored.txt', 'crosshatch.txt', True),
        ('broda.owl', 'peter_broda.txt', True),
        ('common.owl', 'common_5k.txt', False),
        ('enable1.txt', 'enable.txt', False),
        ('ospd.txt', 'ospd.txt', False),
        ('rifkin_300k.txt', 'rifkin_300k.txt', False),
        ('crossword_nexus.dict', 'crossword_nexus.txt', True),
    ]

    results = []

    for input_file, output_file, preserve_scores in wordlists:
        input_path = external_dir / input_file
        if not input_path.exists():
            print(f"Skipping {input_file} (not found)")
            continue

        output_path = normalized_dir / output_file

        print(f"Processing {input_file}...")

        def progress(current, total):
            pct = current * 100 // total
            print(f"  {pct}% ({current}/{total})", end='\r')

        total, unique = normalize_wordlist(
            str(input_path),
            str(output_path),
            preserve_scores=preserve_scores,
            progress_callback=progress
        )

        print(f"  Done: {unique:,} unique words from {total:,} lines")
        results.append((output_file, unique))

    print("\nSummary:")
    for name, count in results:
        print(f"  {name}: {count:,} words")

    return results


if __name__ == '__main__':
    normalize_all_external()
