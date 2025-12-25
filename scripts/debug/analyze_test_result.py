#!/usr/bin/env python3
"""Analyze crossword test grid results."""

import json
import sys
from collections import Counter

def analyze_grid(filepath, test_name):
    with open(filepath) as f:
        result = json.load(f)

    grid = result['grid']

    print('=' * 70)
    print(f'{test_name}')
    print('=' * 70)

    # Display grid
    print('\nFilled Grid:')
    print('   ' + ' '.join(str(i) for i in range(len(grid[0]))))
    for i, row in enumerate(grid):
        print(f'{i:2d} {" ".join(row)}')

    # Extract words
    words_across = []
    words_down = []

    # Horizontal words
    for i, row in enumerate(grid):
        word = ''.join(row).replace('#', ' ')
        for w in word.split():
            if len(w) > 1:
                words_across.append((i, w))

    # Vertical words
    for col_idx in range(len(grid[0])):
        word = ''.join(row[col_idx] for row in grid).replace('#', ' ')
        for w in word.split():
            if len(w) > 1:
                words_down.append((col_idx, w))

    all_words = [w for _, w in words_across] + [w for _, w in words_down]

    print(f'\n' + '=' * 70)
    print('KEY LONG WORDS')
    print('=' * 70)

    eleven_across = [(r, w) for r, w in words_across if len(w) == 11]
    eleven_down = [(c, w) for c, w in words_down if len(w) == 11]

    print(f'\n11-letter ACROSS ({len(eleven_across)}):')
    for row, word in eleven_across:
        print(f'  Row {row:2d}: {word}')

    print(f'\n11-letter DOWN ({len(eleven_down)}):')
    for col, word in eleven_down:
        print(f'  Col {col:2d}: {word}')

    # Check duplicates
    word_counts = Counter(all_words)
    duplicates = {word: count for word, count in word_counts.items() if count > 1}

    print(f'\n' + '=' * 70)
    print('STATISTICS')
    print('=' * 70)
    print(f'Total words: {len(all_words)}')
    print(f'Unique words: {len(set(all_words))}')
    print(f'ACROSS words: {len(words_across)}')
    print(f'DOWN words: {len(words_down)}')
    print(f'Direction ratio: {len(words_across) / len(words_down):.2f}:1')

    if duplicates:
        print(f'\n⚠️ DUPLICATES ({len(duplicates)}):')
        for word, count in sorted(duplicates.items()):
            print(f'  {word}: {count} times')
        print('❌ FAIL: Duplicates detected')
    else:
        print(f'\n✅ PASS: No duplicates')

    print(f'\n' + '=' * 70)
    print('ALL WORDS')
    print('=' * 70)

    print(f'\nACROSS ({len(words_across)}):')
    for row, word in sorted(words_across):
        marker = '⭐' if len(word) >= 11 else '  '
        print(f'{marker} Row {row:2d} ({len(word):2d}): {word}')

    print(f'\nDOWN ({len(words_down)}):')
    for col, word in sorted(words_down):
        marker = '⭐' if len(word) >= 11 else '  '
        print(f'{marker} Col {col:2d} ({len(word):2d}): {word}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        analyze_grid(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'TEST ANALYSIS')
    else:
        print('Usage: python analyze_test_result.py <result_file> [test_name]')
