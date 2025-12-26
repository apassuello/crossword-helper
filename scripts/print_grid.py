#!/usr/bin/env python3
"""
Grid Visualization Utility

Reads crossword grid JSON files and prints them as visual grids.
Supports both compact and detailed views for easy visualization.

Usage:
    python scripts/print_grid.py <grid_file.json>
    python scripts/print_grid.py <grid_file.json> --compact
    python scripts/print_grid.py <grid_file.json> --detailed
"""

import json
import sys
from pathlib import Path


def load_grid(file_path):
    """Load grid from JSON file."""
    with open(file_path) as f:
        data = json.load(f)
    return data['grid'], data.get('title', 'Untitled Grid')


def analyze_grid(grid):
    """Analyze grid and return statistics."""
    size = len(grid)
    total_cells = size * size
    black_squares = sum(1 for row in grid for cell in row if cell == '#')
    fillable_cells = total_cells - black_squares

    filled_cells = sum(1 for row in grid for cell in row
                      if cell not in ['.', '#', '?'])
    empty_cells = fillable_cells - filled_cells

    fill_percentage = (filled_cells / fillable_cells * 100) if fillable_cells > 0 else 0

    return {
        'size': size,
        'total_cells': total_cells,
        'black_squares': black_squares,
        'fillable_cells': fillable_cells,
        'filled_cells': filled_cells,
        'empty_cells': empty_cells,
        'fill_percentage': fill_percentage
    }


def get_words_from_grid(grid):
    """Extract all words from grid (horizontal and vertical)."""
    words = []
    size = len(grid)

    # Horizontal words
    for row in grid:
        word = ""
        for cell in row:
            if cell == '#':
                if len(word) >= 3:  # Only words 3+ letters
                    words.append(word)
                word = ""
            elif cell not in ['.', '?']:
                word += cell
            else:
                if len(word) >= 3:
                    words.append(word)
                word = ""
        if len(word) >= 3:
            words.append(word)

    # Vertical words
    for col in range(size):
        word = ""
        for row in range(size):
            cell = grid[row][col]
            if cell == '#':
                if len(word) >= 3:
                    words.append(word)
                word = ""
            elif cell not in ['.', '?']:
                word += cell
            else:
                if len(word) >= 3:
                    words.append(word)
                word = ""
        if len(word) >= 3:
            words.append(word)

    return words


def print_compact(grid, title="Grid"):
    """Print compact grid view using symbols."""
    size = len(grid)

    print(f"\n{'='*60}")
    print(f" {title} ({size}×{size}) - COMPACT VIEW")
    print('='*60)

    # Column numbers
    print("   ", end="")
    for col in range(size):
        print(f" {col:2d}", end="")
    print()

    # Top border
    print("  ┌" + "─" * (size * 3 + 1) + "┐")

    # Grid rows
    for row_idx, row in enumerate(grid):
        print(f"{row_idx:2d} │", end="")
        for cell in row:
            if cell == '#':
                print(" ██", end="")
            elif cell == '.' or cell == '?':
                print("  ·", end="")
            else:
                print(f"  {cell}", end="")
        print(" │")

    # Bottom border
    print("  └" + "─" * (size * 3 + 1) + "┘")


def print_detailed(grid, title="Grid"):
    """Print detailed grid view with full box drawing."""
    size = len(grid)

    print(f"\n{'='*60}")
    print(f" {title} ({size}×{size}) - DETAILED VIEW")
    print('='*60)

    # Top border with column numbers
    print("    ", end="")
    for col in range(size):
        print(f"  {col:2d} ", end="")
    print()

    print("   ┌", end="")
    for col in range(size):
        print("────", end="")
        if col < size - 1:
            print("┬", end="")
    print("┐")

    # Grid rows
    for row_idx, row in enumerate(grid):
        # Row number + cells
        print(f"{row_idx:2d} │", end="")
        for cell in row:
            if cell == '#':
                print(" ██ ", end="")
            elif cell == '.' or cell == '?':
                print("  · ", end="")
            else:
                print(f"  {cell} ", end="")
            print("│", end="")
        print()

        # Inter-row border (except after last row)
        if row_idx < size - 1:
            print("   ├", end="")
            for col in range(size):
                print("────", end="")
                if col < size - 1:
                    print("┼", end="")
            print("┤")

    # Bottom border
    print("   └", end="")
    for col in range(size):
        print("────", end="")
        if col < size - 1:
            print("┴", end="")
    print("┘")


def print_statistics(grid, title="Grid"):
    """Print grid statistics."""
    stats = analyze_grid(grid)
    words = get_words_from_grid(grid)

    # Sort words by length (longest first)
    words_sorted = sorted(set(words), key=len, reverse=True)

    print(f"\n{'='*60}")
    print(f" {title} - STATISTICS")
    print('='*60)
    print(f"Grid size:        {stats['size']}×{stats['size']}")
    print(f"Total cells:      {stats['total_cells']}")
    print(f"Black squares:    {stats['black_squares']}")
    print(f"Fillable cells:   {stats['fillable_cells']}")
    print(f"Filled cells:     {stats['filled_cells']}")
    print(f"Empty cells:      {stats['empty_cells']}")
    print(f"Fill percentage:  {stats['fill_percentage']:.1f}%")
    print(f"Total words:      {len(words)}")
    print(f"Unique words:     {len(words_sorted)}")

    if words_sorted:
        print(f"\nSample words (10 longest):")
        for i, word in enumerate(words_sorted[:10], 1):
            print(f"  {i:2d}. {word} ({len(word)} letters)")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/print_grid.py <grid_file.json> [--compact|--detailed]")
        print("\nOptions:")
        print("  --compact   Show only compact view")
        print("  --detailed  Show only detailed view")
        print("  (default)   Show both views + statistics")
        sys.exit(1)

    grid_file = sys.argv[1]

    if not Path(grid_file).exists():
        print(f"Error: File not found: {grid_file}")
        sys.exit(1)

    # Load grid
    grid, title = load_grid(grid_file)

    # Determine what to show
    show_compact = "--detailed" not in sys.argv
    show_detailed = "--compact" not in sys.argv
    show_stats = len(sys.argv) == 2  # Show stats if no specific view requested

    # Print views
    if show_compact:
        print_compact(grid, title)

    if show_detailed:
        print_detailed(grid, title)

    if show_stats:
        print_statistics(grid, title)

    print()  # Final newline


if __name__ == '__main__':
    main()
