#!/usr/bin/env python3
"""
Phase 5.1 Demo Runner

Automated script for running Phase 5.1 beam search demonstrations on any grid.
Supports custom parameters, multiple runs for diversity testing, and automatic
visualization of results.

Usage:
    # Basic demo
    python scripts/demo_phase5.py test_data/grids/demo_11x11_EMPTY.json

    # Custom parameters
    python scripts/demo_phase5.py grid.json --timeout 60 --min-score 40

    # Diversity test (3 runs)
    python scripts/demo_phase5.py grid.json --runs 3

    # Save output with custom name
    python scripts/demo_phase5.py grid.json --output my_result.json
"""

import json
import time
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator


def load_grid_from_file(file_path, size=None):
    """Load grid from JSON file."""
    with open(file_path) as f:
        data = json.load(f)

    grid_data = data['grid']
    grid_size = len(grid_data)

    if size and size != grid_size:
        raise ValueError(f"Grid size mismatch: file has {grid_size}×{grid_size}, expected {size}×{size}")

    grid = Grid(size=grid_size)
    for r, row in enumerate(grid_data):
        for c, cell in enumerate(row):
            if cell == '#':
                grid.set_black_square(r, c, enforce_symmetry=False)
            elif cell not in ['.', '?']:
                # Pre-filled cell
                grid.set_letter(r, c, cell)

    title = data.get('title', f'{grid_size}×{grid_size} Grid')
    return grid, grid_size, title


def run_demo(grid_file, word_list, pattern_matcher, timeout=120, min_score=30,
             beam_width=10, candidates_per_slot=20, verbose=True):
    """Run Phase 5.1 beam search on a grid."""

    # Load grid
    grid, grid_size, title = load_grid_from_file(grid_file)

    if verbose:
        print(f"\n{'='*70}")
        print(f" Phase 5.1 Demo: {title}")
        print(f"{'='*70}")
        print()
        print(f"Grid size: {grid_size}×{grid_size}")
        print(f"Parameters:")
        print(f"  - Beam width: {beam_width}")
        print(f"  - Candidates per slot: {candidates_per_slot}")
        print(f"  - Min score: {min_score}")
        print(f"  - Timeout: {timeout}s")
        print(f"  - Temperature: 0.8 (high exploration)")
        print(f"  - LCV: adjusted scores")
        print(f"  - Pattern tracking: bigram diversity")
        print()

    # Create orchestrator
    orchestrator = BeamSearchOrchestrator(
        grid=grid,
        word_list=word_list,
        pattern_matcher=pattern_matcher,
        beam_width=beam_width,
        candidates_per_slot=candidates_per_slot,
        min_score=min_score
    )

    # Run beam search
    if verbose:
        print(f"Running beam search... (timeout={timeout}s)")
        print()

    start_time = time.time()
    result = orchestrator.fill(timeout=timeout)
    elapsed = time.time() - start_time

    # Calculate statistics
    final_grid = result.grid
    total_cells = sum(1 for r in range(grid_size) for c in range(grid_size)
                     if final_grid.get_cell(r, c) != '#')
    filled_cells = sum(1 for r in range(grid_size) for c in range(grid_size)
                      if final_grid.get_cell(r, c) not in ['.', '?', '#'])
    fill_pct = 100 * filled_cells / total_cells if total_cells > 0 else 0

    if verbose:
        print(f"{'='*70}")
        print(f" RESULTS")
        print(f"{'='*70}")
        print(f"Time elapsed:     {elapsed:.2f}s / {timeout}s")
        print(f"Iterations:       {result.iterations}")
        print(f"Cells filled:     {filled_cells}/{total_cells} ({fill_pct:.1f}%)")
        print(f"Slots filled:     {result.slots_filled}/{result.total_slots}")

        if grid_size == 11:
            print(f"Target (90%+):    {'YES ✅' if fill_pct >= 90 else 'NO ❌'}")
        elif grid_size == 15:
            print(f"Target (85-90%):  {'YES ✅' if fill_pct >= 85 else 'NO ❌'}")

        print(f"Success (100%):   {'YES ✅' if fill_pct >= 100 else 'NO'}")
        print()

    # Get sample words
    words = []
    for slot in final_grid.get_word_slots():
        pattern = final_grid.get_pattern_for_slot(slot)
        if '?' not in pattern and '.' not in pattern and len(pattern) >= 5:
            words.append(pattern)

    words_sorted = sorted(set(words), key=len, reverse=True)

    if verbose and words_sorted:
        print(f"Sample words placed (5+ letters, {len(words_sorted)} unique):")
        for i, word in enumerate(words_sorted[:10], 1):
            print(f"  {i:2d}. {word} ({len(word)} letters)")
        print()

    return {
        'grid': final_grid,
        'grid_size': grid_size,
        'title': title,
        'time_elapsed': elapsed,
        'iterations': result.iterations,
        'filled_cells': filled_cells,
        'total_cells': total_cells,
        'fill_percentage': fill_pct,
        'slots_filled': result.slots_filled,
        'total_slots': result.total_slots,
        'words': words_sorted
    }


def save_result(result, output_file, verbose=True):
    """Save filled grid to JSON file."""
    grid = result['grid']
    grid_size = result['grid_size']

    output_data = {
        "grid": [[grid.get_cell(r, c) for c in range(grid_size)]
                 for r in range(grid_size)],
        "title": f"{result['title']} ({result['fill_percentage']:.1f}% filled)",
        "metadata": {
            "phase": "5.1",
            "timestamp": datetime.now().isoformat(),
            "time_seconds": result['time_elapsed'],
            "iterations": result['iterations'],
            "fill_percentage": result['fill_percentage'],
            "slots_filled": f"{result['slots_filled']}/{result['total_slots']}"
        }
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    if verbose:
        print(f"Saved result to: {output_file}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Phase 5.1 demo runner for crossword grid filling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic demo
  python scripts/demo_phase5.py test_data/grids/demo_11x11_EMPTY.json

  # Custom timeout and score
  python scripts/demo_phase5.py grid.json --timeout 60 --min-score 40

  # Diversity test (3 runs)
  python scripts/demo_phase5.py grid.json --runs 3

  # Save with custom name
  python scripts/demo_phase5.py grid.json --output my_result.json
        '''
    )

    parser.add_argument('grid_file', help='Input grid JSON file')
    parser.add_argument('--output', '-o', help='Output file for filled grid (default: auto-generated)')
    parser.add_argument('--timeout', '-t', type=int, default=120,
                       help='Timeout in seconds (default: 120)')
    parser.add_argument('--min-score', '-s', type=int, default=30,
                       help='Minimum word score (default: 30)')
    parser.add_argument('--beam-width', '-b', type=int, default=10,
                       help='Beam width (default: 10)')
    parser.add_argument('--candidates', '-c', type=int, default=20,
                       help='Candidates per slot (default: 20)')
    parser.add_argument('--runs', '-r', type=int, default=1,
                       help='Number of runs for diversity testing (default: 1)')
    parser.add_argument('--wordlist', '-w', default='data/wordlists/comprehensive.txt',
                       help='Word list file (default: data/wordlists/comprehensive.txt)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode (minimal output)')

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.grid_file).exists():
        print(f"Error: Grid file not found: {args.grid_file}")
        sys.exit(1)

    if not Path(args.wordlist).exists():
        print(f"Error: Word list file not found: {args.wordlist}")
        sys.exit(1)

    # Load word list once (shared across runs)
    if not args.quiet:
        print("Loading word list...")
    word_list = WordList.from_file(args.wordlist)
    pattern_matcher = PatternMatcher(word_list)

    # Run demo(s)
    results = []
    for run in range(args.runs):
        if args.runs > 1 and not args.quiet:
            print(f"\n{'='*70}")
            print(f" RUN {run + 1}/{args.runs}")
            print(f"{'='*70}")

        result = run_demo(
            args.grid_file,
            word_list,
            pattern_matcher,
            timeout=args.timeout,
            min_score=args.min_score,
            beam_width=args.beam_width,
            candidates_per_slot=args.candidates,
            verbose=not args.quiet
        )

        results.append(result)

        # Save result
        if args.output:
            output_file = args.output if args.runs == 1 else f"{args.output}.run{run+1}.json"
        else:
            # Auto-generate output filename
            input_stem = Path(args.grid_file).stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"test_data/grids/{input_stem}_PHASE5_{timestamp}"
            if args.runs > 1:
                output_file += f"_run{run+1}"
            output_file += ".json"

        save_result(result, output_file, verbose=not args.quiet)

        # Visualize if requested (only for single runs)
        if args.runs == 1 and not args.quiet:
            print(f"\nTo visualize:")
            print(f"  python scripts/print_grid.py {output_file}")
            print()

    # Diversity summary for multiple runs
    if args.runs > 1 and not args.quiet:
        print(f"\n{'='*70}")
        print(f" DIVERSITY SUMMARY ({args.runs} runs)")
        print(f"{'='*70}")

        for i, result in enumerate(results, 1):
            print(f"\nRun {i}:")
            print(f"  Time: {result['time_elapsed']:.2f}s")
            print(f"  Fill: {result['fill_percentage']:.1f}%")
            print(f"  Words (5+ letters): {', '.join(result['words'][:5])}")

        # Check uniqueness
        all_words = [set(r['words']) for r in results]
        common = set.intersection(*all_words) if all_words else set()
        unique_per_run = [len(words - common) for words in all_words]

        print(f"\nDiversity Analysis:")
        print(f"  Common to all runs: {len(common)}")
        for i, unique_count in enumerate(unique_per_run, 1):
            print(f"  Unique to run {i}: {unique_count}")

        diversity_pct = sum(unique_per_run) / sum(len(w) for w in all_words) * 100 if all_words else 0
        print(f"  Overall diversity: {diversity_pct:.1f}%")
        print()


if __name__ == '__main__':
    main()
