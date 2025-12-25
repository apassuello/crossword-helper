#!/usr/bin/env python3
"""
Script to print crossword grid JSON files as actual grids.

Usage:
    python3 print_grid.py grid_file.json
"""

import json
import sys


def print_grid(grid_data, show_stats=True):
    """Print a crossword grid in a readable format."""
    grid = grid_data['grid']
    size = len(grid)

    if show_stats:
        # Count cell types
        letters = sum(1 for row in grid for cell in row if cell not in ['#', '.'])
        dots = sum(1 for row in grid for cell in row if cell == '.')
        blacks = sum(1 for row in grid for cell in row if cell == '#')
        total_fillable = letters + dots

        print(f"Grid: {size}×{size}")
        print(f"Letters: {letters}, Dots: {dots}, Black: {blacks}")
        if total_fillable > 0:
            print(f"Fill: {letters}/{total_fillable} ({letters/total_fillable*100:.1f}%)")
        print()

    # Print column numbers
    print("    ", end="")
    for col in range(size):
        print(f"{col:2d}", end=" ")
    print()

    # Print separator
    print("   +" + "---" * size + "+")

    # Print rows
    for row_idx, row in enumerate(grid):
        print(f"{row_idx:2d} |", end="")
        for cell in row:
            if cell == '#':
                print(" █ ", end="")
            elif cell == '.':
                print(" · ", end="")
            else:
                print(f" {cell} ", end="")
        print("|")

    # Print bottom separator
    print("   +" + "---" * size + "+")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 print_grid.py grid_file.json")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename) as f:
            data = json.load(f)

        print(f"=== {filename} ===")
        print()
        print_grid(data)

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filename}': {e}")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required key in JSON: {e}")
        sys.exit(1)
