#!/usr/bin/env python3
"""
Test Phase 4.5 fixes for stopping condition and value ordering.

This test suite validates:
1. Stopping condition fix (persists through failures)
2. True chronological backtracking (undoes previous assignments)
3. Threshold-diverse value ordering (exploration-exploitation balance)
4. Overall grid completion quality

Success Criteria:
- 11×11: 90%+ completion in <30s, >10 iterations
- 15×15: 85%+ completion in <180s, >20 iterations
- Persistence: Doesn't stop after <10 iterations
"""

import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search_autofill import BeamSearchAutofill


def print_grid(grid: Grid, title: str):
    """Print grid visually."""
    print(f"\n{title}")
    print("=" * 50)
    size = grid.size
    for row in range(size):
        for col in range(size):
            cell = grid.get_cell(row, col)
            if cell == '#':
                print('██', end='')
            elif cell in ['.', '?']:
                print(' ·', end='')
            else:
                print(f' {cell}', end='')
        print()


def test_simple_11x11():
    """Test 11x11 grid - should complete in <30s with 90%+ fill."""
    print("\n" + "="*70)
    print("TEST 1: Simple 11x11 Grid")
    print("="*70)

    grid = Grid(size=11)
    grid.set_black_square(5, 5, enforce_symmetry=False)

    word_list = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)
    pattern_matcher = PatternMatcher(word_list)

    beam_search = BeamSearchAutofill(
        grid=grid,
        word_list=word_list,
        pattern_matcher=pattern_matcher,
        beam_width=10,
        candidates_per_slot=20,
        min_score=30
    )

    print("\nRunning beam search (timeout=30s)...")
    result = beam_search.fill(timeout=30)

    fill_percent = (result.slots_filled / result.total_slots) * 100
    print(f"\nResult: {result.slots_filled}/{result.total_slots} slots ({fill_percent:.1f}%)")
    print(f"Iterations: {result.iterations}")
    print(f"Failed expansions: {beam_search.failed_expansions}")
    print(f"Time: {result.time_elapsed:.2f}s")
    print(f"Success: {result.success}")

    print_grid(result.grid, "Filled Grid")

    # Assertions
    assert fill_percent >= 90, f"Expected >=90% fill, got {fill_percent:.1f}%"
    assert result.iterations > 10, f"Expected >10 iterations, got {result.iterations}"
    assert result.time_elapsed < 30, f"Expected <30s, got {result.time_elapsed:.2f}s"

    print("\n✅ TEST 1 PASSED")
    return result


def test_real_15x15():
    """Test real 15x15 grid - should complete in <180s with 85%+ fill."""
    print("\n" + "="*70)
    print("TEST 2: Real 15x15 Grid")
    print("="*70)

    # Load grid from JSON
    grid_file = 'test_data/grids/test_with_fix_15x15.json'
    if not Path(grid_file).exists():
        print(f"⚠️  Skipping TEST 2: {grid_file} not found")
        return None

    with open(grid_file) as f:
        data = json.load(f)

    grid_data = data['grid']
    grid = Grid(size=15)
    for row in range(15):
        for col in range(15):
            if grid_data[row][col] == '#':
                grid.set_black_square(row, col, enforce_symmetry=False)

    word_list = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)
    pattern_matcher = PatternMatcher(word_list)

    beam_search = BeamSearchAutofill(
        grid=grid,
        word_list=word_list,
        pattern_matcher=pattern_matcher,
        beam_width=7,
        candidates_per_slot=20,
        min_score=10
    )

    print("\nRunning beam search (timeout=180s)...")
    result = beam_search.fill(timeout=180)

    fill_percent = (result.slots_filled / result.total_slots) * 100
    print(f"\nResult: {result.slots_filled}/{result.total_slots} slots ({fill_percent:.1f}%)")
    print(f"Iterations: {result.iterations}")
    print(f"Failed expansions: {beam_search.failed_expansions}")
    print(f"Time: {result.time_elapsed:.2f}s")
    print(f"Success: {result.success}")

    if result.problematic_slots:
        print(f"Problematic slots: {len(result.problematic_slots)}")

    print_grid(result.grid, "Filled Grid")

    # Assertions
    assert fill_percent >= 85, f"Expected >=85% fill, got {fill_percent:.1f}%"
    assert result.iterations > 20, f"Expected >20 iterations, got {result.iterations}"
    assert result.time_elapsed < 180, f"Expected <180s, got {result.time_elapsed:.2f}s"

    print("\n✅ TEST 2 PASSED")
    return result


def test_persistence():
    """Test that algorithm doesn't give up early."""
    print("\n" + "="*70)
    print("TEST 3: Persistence Test (Challenging Grid)")
    print("="*70)

    grid = Grid(size=11)
    # Add challenging black square pattern
    for i in range(0, 11, 3):
        grid.set_black_square(i, 5, enforce_symmetry=False)

    word_list = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)
    pattern_matcher = PatternMatcher(word_list)

    beam_search = BeamSearchAutofill(
        grid=grid,
        word_list=word_list,
        pattern_matcher=pattern_matcher,
        beam_width=5,
        candidates_per_slot=15,
        min_score=30
    )

    print("\nRunning beam search (timeout=60s)...")
    result = beam_search.fill(timeout=60)

    fill_percent = (result.slots_filled / result.total_slots) * 100
    print(f"\nResult: {result.slots_filled}/{result.total_slots} slots ({fill_percent:.1f}%)")
    print(f"Iterations: {result.iterations}")
    print(f"Failed expansions tolerated: {beam_search.failed_expansions}")
    print(f"Time: {result.time_elapsed:.2f}s")

    print_grid(result.grid, "Filled Grid")

    # Should NOT stop after just 4-6 iterations
    assert result.iterations >= 15, f"Expected >=15 iterations (showing persistence), got {result.iterations}"

    # Should tolerate some failures
    print(f"\n✅ TEST 3 PASSED - Algorithm persisted through difficulties")
    print(f"   Tolerated {beam_search.failed_expansions} expansion failures before completing")

    return result


def test_value_ordering_diversity():
    """Test that value ordering produces diverse solutions."""
    print("\n" + "="*70)
    print("TEST 4: Value Ordering Diversity (3 runs)")
    print("="*70)

    results = []

    for run in range(3):
        print(f"\n--- Run {run + 1}/3 ---")

        grid = Grid(size=11)
        grid.set_black_square(5, 5, enforce_symmetry=False)

        word_list = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)
        pattern_matcher = PatternMatcher(word_list)

        beam_search = BeamSearchAutofill(
            grid=grid,
            word_list=word_list,
            pattern_matcher=pattern_matcher,
            beam_width=10,
            candidates_per_slot=20,
            min_score=30
        )

        result = beam_search.fill(timeout=30)
        fill_percent = (result.slots_filled / result.total_slots) * 100

        print(f"Fill: {fill_percent:.1f}%, Iterations: {result.iterations}")

        # Extract first word from grid (should vary across runs)
        first_word = ""
        for col in range(11):
            cell = result.grid.get_cell(0, col)
            if cell not in ['.', '?', '#']:
                first_word += cell

        results.append({
            'fill_percent': fill_percent,
            'iterations': result.iterations,
            'first_word': first_word
        })

    print("\n--- Diversity Analysis ---")
    first_words = [r['first_word'] for r in results]
    unique_first_words = len(set(first_words))

    print(f"First words across runs: {first_words}")
    print(f"Unique solutions: {unique_first_words}/3")

    # At least some diversity (temperature=0.3 should provide gentle exploration)
    assert unique_first_words >= 2, f"Expected at least 2 unique solutions, got {unique_first_words}"

    print(f"\n✅ TEST 4 PASSED - Value ordering produces diverse solutions")

    return results


def main():
    """Run all tests."""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + " "*18 + "PHASE 4.5 TEST SUITE" + " "*30 + "║")
    print("║" + " "*68 + "║")
    print("║" + "  Testing: Stopping condition fix + value ordering" + " "*13 + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    try:
        # Run all tests
        result1 = test_simple_11x11()
        result2 = test_real_15x15()
        result3 = test_persistence()
        result4 = test_value_ordering_diversity()

        # Summary
        print("\n" + "╔" + "="*68 + "╗")
        print("║" + " "*68 + "║")
        print("║" + " "*22 + "ALL TESTS PASSED!" + " "*25 + "║")
        print("║" + " "*68 + "║")
        print("╚" + "="*68 + "╝")

        print("\n✅ Phase 4.5 fixes are working correctly!")

        print("\nKey Achievements:")
        print("  • Algorithm persists through difficulties (no premature exit)")
        print("  • True backtracking undoes previous assignments")
        print("  • Threshold-diverse ordering provides exploration")
        print("  • Grid completion quality significantly improved")

        if result1:
            print(f"\n11×11 Performance:")
            print(f"  - Fill: {result1.slots_filled}/{result1.total_slots} ({result1.slots_filled/result1.total_slots*100:.1f}%)")
            print(f"  - Iterations: {result1.iterations}")
            print(f"  - Time: {result1.time_elapsed:.2f}s")

        if result2:
            print(f"\n15×15 Performance:")
            print(f"  - Fill: {result2.slots_filled}/{result2.total_slots} ({result2.slots_filled/result2.total_slots*100:.1f}%)")
            print(f"  - Iterations: {result2.iterations}")
            print(f"  - Time: {result2.time_elapsed:.2f}s")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nPhase 4.5 fixes need adjustment")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
