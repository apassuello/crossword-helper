#!/usr/bin/env python3
"""
Quick integration test for Phase 3 refactoring.

Tests end-to-end beam search filling to ensure all components work together.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search_autofill import BeamSearchAutofill

def test_integration():
    """Test basic integration - components work together."""
    print("="*80)
    print("QUICK INTEGRATION TEST")
    print("="*80)

    # Load word list
    word_list_path = Path(__file__).parent / 'data' / 'wordlists' / 'test_wordlist.txt'
    if not word_list_path.exists():
        print(f"\nWARNING: Test word list not found at {word_list_path}")
        print("Skipping integration test")
        return False

    print("\n1. Loading word list...")
    word_list = WordList()
    word_list.load_from_file(str(word_list_path))
    print(f"   Loaded {len(word_list.words)} words")

    # Create pattern matcher
    print("\n2. Creating pattern matcher...")
    pattern_matcher = PatternMatcher(word_list)
    print("   Pattern matcher created")

    # Load test grid
    grid_path = Path(__file__).parent.parent / 'fixtures' / 'test_data' / 'grids' / 'demo_11x11_EMPTY.json'
    if not grid_path.exists():
        print(f"\nWARNING: Test grid not found at {grid_path}")
        print("Creating simple test grid instead")
        grid = Grid(11)
        # Add some blocks
        grid.set_black_square(3, 3, enforce_symmetry=True)
        grid.set_black_square(1, 5, enforce_symmetry=True)
    else:
        print("\n3. Loading test grid...")
        with open(grid_path) as f:
            grid_data = json.load(f)
        grid = Grid.from_dict(grid_data)
        print(f"   Loaded {grid.size}x{grid.size} grid")

    # Create solver
    print("\n4. Creating BeamSearchAutofill solver...")
    solver = BeamSearchAutofill(
        grid=grid,
        word_list=word_list,
        pattern_matcher=pattern_matcher,
        beam_width=3,
        candidates_per_slot=5
    )
    print("   Solver created successfully")

    # Verify components are initialized
    print("\n5. Verifying component initialization...")
    assert hasattr(solver, 'slot_selector'), "Missing slot_selector"
    assert hasattr(solver, 'constraint_engine'), "Missing constraint_engine"
    assert hasattr(solver, 'value_ordering'), "Missing value_ordering"
    assert hasattr(solver, 'diversity_manager'), "Missing diversity_manager"
    assert hasattr(solver, 'state_evaluator'), "Missing state_evaluator"
    assert hasattr(solver, 'beam_manager'), "Missing beam_manager"
    print("   ✓ All components initialized")

    # Verify backward compatibility methods exist
    print("\n6. Verifying backward compatibility methods...")
    assert hasattr(solver, '_compute_score'), "Missing _compute_score"
    assert hasattr(solver, '_evaluate_state_viability'), "Missing _evaluate_state_viability"
    assert hasattr(solver, '_count_differences'), "Missing _count_differences"
    assert hasattr(solver, '_sort_slots_by_constraint'), "Missing _sort_slots_by_constraint"
    assert hasattr(solver, '_expand_beam'), "Missing _expand_beam"
    assert hasattr(solver, '_prune_beam'), "Missing _prune_beam"
    assert hasattr(solver, '_apply_diversity_bonus'), "Missing _apply_diversity_bonus"
    print("   ✓ All proxy methods present")

    # Run a quick fill (short timeout)
    print("\n7. Running beam search fill (10 second timeout)...")
    try:
        result = solver.fill(timeout=10)
        print(f"   ✓ Fill completed successfully")
        print(f"   - Slots filled: {result.slots_filled}/{result.total_slots}")
        print(f"   - Time elapsed: {result.time_elapsed:.2f}s")
        print(f"   - Iterations: {result.iterations}")
        print(f"   - Success: {result.success}")

        return True

    except Exception as e:
        print(f"   ✗ Fill failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_integration()
    print("\n" + "="*80)
    if success:
        print("✓ INTEGRATION TEST PASSED")
        print("="*80)
        sys.exit(0)
    else:
        print("✗ INTEGRATION TEST FAILED")
        print("="*80)
        sys.exit(1)
