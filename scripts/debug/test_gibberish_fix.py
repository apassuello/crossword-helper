#!/usr/bin/env python3
"""
Demonstration of the gibberish scoring fix.

Shows how the improved algorithm properly distinguishes between
real words and gibberish patterns.
"""

from src.fill.word_list import WordList as OldWordList
from src.fill.word_list_improved import WordList as NewWordList


def demonstrate_fix():
    """Show the before and after scoring comparison."""

    # Test words including gibberish and real words
    test_words = [
        # Gibberish patterns
        'AAAAA', 'III', 'NNN', 'ZZZ', 'XXXX', 'EEEEE',

        # Real words with various quality levels
        'ARENA', 'STONE', 'RATES', 'INTER', 'HELLO',

        # Edge cases - valid words with doubles
        'AAH', 'ADD', 'ALL', 'BOOK', 'TREE',

        # Uncommon letter words
        'JAZZ', 'QUIZ', 'JINX', 'QUEEN',
    ]

    old_wl = OldWordList()
    new_wl = NewWordList()

    print("=" * 70)
    print("GIBBERISH SCORING FIX DEMONSTRATION")
    print("=" * 70)
    print()

    print(f"{'Word':<10} {'Old Score':>12} {'New Score':>12} {'Change':>10} {'Status':<20}")
    print("-" * 70)

    improvements = []
    fixes = []

    for word in test_words:
        old_score = old_wl._score_word(word)
        new_score = new_wl._score_word(word)
        change = new_score - old_score

        # Determine status
        is_gibberish = len(set(word)) == 1 or len(set(word)) / len(word) < 0.4

        if is_gibberish:
            if old_score > 30 and new_score < 20:
                status = "✓ FIXED (gibberish)"
                fixes.append(word)
            elif new_score < 20:
                status = "Already low"
            else:
                status = "Needs work"
        else:
            if new_score > old_score:
                status = "✓ Improved"
                improvements.append(word)
            elif new_score == old_score:
                status = "Unchanged"
            else:
                status = "Lowered"

        # Format output with color codes
        color = ""
        if "FIXED" in status:
            color = "\033[92m"  # Green
        elif "Improved" in status:
            color = "\033[94m"  # Blue
        elif change < -10:
            color = "\033[91m"  # Red
        reset = "\033[0m" if color else ""

        print(f"{color}{word:<10} {old_score:>12} {new_score:>12} {change:>+10} {status:<20}{reset}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Test quality filtering
    all_words = ['ARENA', 'AAAAA', 'STONE', 'III', 'RATES', 'ZZZ']
    old_list = OldWordList(all_words)
    new_list = NewWordList(all_words)

    old_quality = old_list.get_all(min_score=30)
    new_quality = new_list.get_all(min_score=30)

    print(f"\nQuality words (score >= 30):")
    print(f"  Old algorithm: {[w.text for w in old_quality]}")
    print(f"  New algorithm: {[w.text for w in new_quality]}")

    print(f"\n✓ Fixed {len(fixes)} gibberish patterns: {fixes}")
    print(f"✓ Improved {len(improvements)} real words: {improvements[:5]}...")

    # Key metric: gibberish vs real word scoring
    print(f"\nKey Test Case:")
    print(f"  AAAAA (gibberish): {old_wl._score_word('AAAAA')} → {new_wl._score_word('AAAAA')}")
    print(f"  ARENA (real word): {old_wl._score_word('ARENA')} → {new_wl._score_word('ARENA')}")
    print(f"  Real word scores {new_wl._score_word('ARENA') - new_wl._score_word('AAAAA')} points higher (was {old_wl._score_word('ARENA') - old_wl._score_word('AAAAA')})")


if __name__ == "__main__":
    demonstrate_fix()