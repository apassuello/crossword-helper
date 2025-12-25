#!/usr/bin/env python3
"""
Filter obvious gibberish from wordlist.

Conservative approach:
- Remove slam-dunk gibberish only (AAAAA, NNN, BRNNN)
- Keep known abbreviations (AAA, NBA, FBI, etc.)
- Keep valid words that happen to have patterns (BOOK, ZOO)

Usage:
    python3 scripts/filter_gibberish.py
"""

import re
from pathlib import Path
from collections import defaultdict


# Known abbreviations to preserve (even if they match gibberish patterns)
KNOWN_ABBREVIATIONS = {
    'AAA',  # American Automobile Association
    'AAAA', # Quad-A (minor league baseball)
    'NBA', 'NFL', 'MLB', 'NHL', 'MLS',  # Sports
    'FBI', 'CIA', 'NSA', 'DEA',  # Government
    'USA', 'UK', 'EU',  # Countries
    'IBM', 'ATT', 'GE',  # Companies
    'DVD', 'CD', 'TV', 'PC',  # Technology
    'PhD', 'MD', 'RN', 'CEO', 'CFO',  # Titles
    'III', 'II', 'IV', 'VI', 'VII', 'VIII', 'IX',  # Roman numerals (common in names)
}


def is_slam_dunk_gibberish(word: str) -> bool:
    """
    Detect obvious gibberish patterns.

    ULTRA-CONSERVATIVE rules (only remove absolute gibberish):
    - All same letter (AAAAA, NNN, but NOT AAA if it's an abbreviation)
    - No vowels in word >= 5 letters (BRNNN, LGBTQ)
    - Alternating repeated pattern (GOGOGO, HAHAHA, XOXOXO)

    REMOVED RULES (too many false positives):
    - 4+ consecutive repeated letters → KEEPS humor misspellings (BOOOOOORING, WELLLL)
    - Consonant clusters → KEEPS legitimate words (AMETHYST, RHYTHM, ANALYSTS)
    """
    # Check known abbreviations first
    if word in KNOWN_ABBREVIATIONS:
        return False

    # Rule 1: All same letter (but allow 2-3 letter versions as they might be valid)
    if len(word) >= 4 and len(set(word)) == 1:
        return True  # AAAA, NNNN, etc.

    # Rule 2: No vowels in word >= 5 letters (excluding Y as vowel)
    # Increased threshold from 4 to 5 to keep common 4-letter abbreviations
    if len(word) >= 5:
        vowels = set('AEIOUY')
        if not any(c in vowels for c in word):
            return True  # BRNNN, LGBTQ, etc.

    # Rule 3: Alternating repeated pattern (ABABAB, but only if 6+ chars)
    if len(word) >= 6:
        # Check for exact alternating pairs
        if all(word[i] == word[i % 2] for i in range(len(word))):
            # But allow real words like BANANA
            if len(set(word)) <= 2:
                return True  # ABABAB, ACACAC with only 2 unique letters

    return False


def count_pattern_score(word: str) -> int:
    """
    Calculate a pattern quality score.
    Lower score = more likely gibberish.
    """
    score = 100

    # Penalty for high repetition
    max_repeat = max((word.count(c) for c in set(word)), default=0)
    if max_repeat > len(word) * 0.5:  # Over 50% same letter
        score -= 30

    # Bonus for having vowels
    vowels = sum(1 for c in word if c in 'AEIOUY')
    if vowels == 0 and len(word) > 2:
        score -= 40

    # Bonus for normal letter distribution
    unique_letters = len(set(word))
    if unique_letters >= len(word) * 0.5:
        score += 20

    return score


def filter_wordlist(input_file: Path, output_file: Path, report_file: Path):
    """Filter gibberish from wordlist and generate report."""

    print(f"Reading wordlist from {input_file}...")
    with open(input_file, 'r') as f:
        words = [line.strip().upper() for line in f if line.strip()]

    print(f"Total words: {len(words)}")

    # Filter words
    kept = []
    removed = defaultdict(list)

    for word in words:
        if is_slam_dunk_gibberish(word):
            # Categorize by reason (matching the 3 rules in is_slam_dunk_gibberish)
            if len(set(word)) == 1:
                removed['all_same_letter'].append(word)
            elif len(word) >= 5 and not any(c in 'AEIOUY' for c in word):
                removed['no_vowels'].append(word)
            elif len(word) >= 6 and all(word[i] == word[i % 2] for i in range(len(word))) and len(set(word)) <= 2:
                removed['alternating_pattern'].append(word)
            else:
                removed['other_pattern'].append(word)
        else:
            kept.append(word)

    # Write filtered wordlist
    print(f"\nWriting filtered wordlist to {output_file}...")
    with open(output_file, 'w') as f:
        for word in sorted(kept):
            f.write(f"{word}\n")

    # Generate report
    print(f"Writing report to {report_file}...")
    total_removed = sum(len(words) for words in removed.values())

    with open(report_file, 'w') as f:
        f.write("# Gibberish Filter Report\n\n")
        f.write(f"**Input:** {input_file}\n")
        f.write(f"**Output:** {output_file}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Total words in:** {len(words)}\n")
        f.write(f"- **Words kept:** {len(kept)} ({len(kept)/len(words)*100:.1f}%)\n")
        f.write(f"- **Words removed:** {total_removed} ({total_removed/len(words)*100:.1f}%)\n\n")

        f.write(f"## Removed by Category\n\n")
        for category, words_list in sorted(removed.items()):
            f.write(f"### {category.replace('_', ' ').title()} ({len(words_list)} words)\n\n")
            # Show first 20 examples
            examples = words_list[:20]
            f.write(f"Examples: {', '.join(examples)}\n")
            if len(words_list) > 20:
                f.write(f"... and {len(words_list) - 20} more\n")
            f.write("\n")

        f.write(f"## Known Abbreviations Preserved\n\n")
        preserved_abbrevs = [word for word in kept if word in KNOWN_ABBREVIATIONS]
        if preserved_abbrevs:
            f.write(f"The following {len(preserved_abbrevs)} abbreviations were kept:\n")
            f.write(f"{', '.join(sorted(preserved_abbrevs))}\n")
        else:
            f.write("None of the known abbreviations were in the wordlist.\n")

    # Print summary
    print(f"\n{'='*60}")
    print(f"FILTERING COMPLETE")
    print(f"{'='*60}")
    print(f"Words in:      {len(words):,}")
    print(f"Words kept:    {len(kept):,} ({len(kept)/len(words)*100:.1f}%)")
    print(f"Words removed: {total_removed:,} ({total_removed/len(words)*100:.1f}%)")
    print(f"\nRemoved by category:")
    for category, words_list in sorted(removed.items(), key=lambda x: -len(x[1])):
        print(f"  {category.replace('_', ' ').title():30s} {len(words_list):5,} words")
    print(f"\nOutput: {output_file}")
    print(f"Report: {report_file}")
    print(f"{'='*60}")


if __name__ == '__main__':
    # Paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / 'data/wordlists/comprehensive.txt'
    output_file = project_root / 'data/wordlists/comprehensive_filtered.txt'
    report_file = project_root / 'data/wordlists/filter_report.md'

    # Check input exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        exit(1)

    # Run filter
    filter_wordlist(input_file, output_file, report_file)
