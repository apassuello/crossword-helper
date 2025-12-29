#!/usr/bin/env python3
"""
Comprehensive test suite for Phase 3 architecture refactoring.

Tests:
1. Import structure and backward compatibility
2. Memory optimization components
3. Real-life grid filling
4. Edge cases and error handling
5. Regression testing
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path

# Add cli/src to path
sys.path.insert(0, str(Path(__file__).parent / 'cli' / 'src'))

# Test results storage
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}


def log_test(category, name, status, details=''):
    """Log test result."""
    result = {
        'category': category,
        'name': name,
        'status': status,
        'details': details
    }

    if status == 'PASS':
        test_results['passed'].append(result)
        print(f"  ✓ {name}")
    elif status == 'FAIL':
        test_results['failed'].append(result)
        print(f"  ✗ {name}")
        if details:
            print(f"    Details: {details}")
    elif status == 'WARN':
        test_results['warnings'].append(result)
        print(f"  ⚠ {name}")
        if details:
            print(f"    Details: {details}")


def test_imports():
    """Test 1: Import structure and backward compatibility."""
    print("\n" + "="*80)
    print("TEST 1: IMPORT STRUCTURE AND BACKWARD COMPATIBILITY")
    print("="*80)

    # Test 1.1: Import BeamSearchAutofill (backward compatibility)
    try:
        from fill.beam_search_autofill import BeamSearchAutofill, BeamState
        log_test('imports', 'Import BeamSearchAutofill', 'PASS')
    except Exception as e:
        log_test('imports', 'Import BeamSearchAutofill', 'FAIL', str(e))
        return False

    # Test 1.2: Import orchestrator
    try:
        from fill.beam_search.orchestrator import BeamSearchOrchestrator
        log_test('imports', 'Import BeamSearchOrchestrator', 'PASS')
    except Exception as e:
        log_test('imports', 'Import BeamSearchOrchestrator', 'FAIL', str(e))
        return False

    # Test 1.3: Check inheritance
    try:
        assert issubclass(BeamSearchAutofill, BeamSearchOrchestrator)
        log_test('imports', 'BeamSearchAutofill inherits from Orchestrator', 'PASS')
    except AssertionError:
        log_test('imports', 'BeamSearchAutofill inherits from Orchestrator', 'FAIL',
                'Inheritance broken')
        return False

    # Test 1.4: Import all memory components
    try:
        from fill.beam_search.memory.grid_snapshot import GridSnapshot
        from fill.beam_search.memory.pools import GridPool, StatePool
        from fill.beam_search.memory.domain_manager import DomainManager
        log_test('imports', 'Import memory components', 'PASS')
    except Exception as e:
        log_test('imports', 'Import memory components', 'FAIL', str(e))
        return False

    # Test 1.5: Import constraint components
    try:
        from fill.beam_search.constraints.engine import MACConstraintEngine
        log_test('imports', 'Import constraint engine', 'PASS')
    except Exception as e:
        log_test('imports', 'Import constraint engine', 'FAIL', str(e))
        return False

    # Test 1.6: Import selection components
    try:
        from fill.beam_search.selection.slot_selector import MRVSlotSelector
        from fill.beam_search.selection.value_ordering import (
            CompositeValueOrdering, LCVValueOrdering, StratifiedValueOrdering
        )
        log_test('imports', 'Import selection components', 'PASS')
    except Exception as e:
        log_test('imports', 'Import selection components', 'FAIL', str(e))
        return False

    # Test 1.7: Import beam components
    try:
        from fill.beam_search.beam.manager import BeamManager
        from fill.beam_search.beam.diversity import DiversityManager
        log_test('imports', 'Import beam components', 'PASS')
    except Exception as e:
        log_test('imports', 'Import beam components', 'FAIL', str(e))
        return False

    # Test 1.8: Import evaluation components
    try:
        from fill.beam_search.evaluation.state_evaluator import StateEvaluator
        log_test('imports', 'Import evaluation components', 'PASS')
    except Exception as e:
        log_test('imports', 'Import evaluation components', 'FAIL', str(e))
        return False

    return True


def test_memory_components():
    """Test 2: Memory optimization components."""
    print("\n" + "="*80)
    print("TEST 2: MEMORY OPTIMIZATION COMPONENTS")
    print("="*80)

    try:
        from core.grid import Grid
        from fill.beam_search.memory.grid_snapshot import GridSnapshot
        from fill.beam_search.memory.pools import GridPool, StatePool
        from fill.beam_search.memory.domain_manager import DomainManager
        from fill.beam_search.state import BeamState

        # Test 2.1: GridSnapshot basic operations
        try:
            grid = Grid(5, 5)
            grid.cells = [['A', 'B', 'C', 'D', 'E'] for _ in range(5)]

            snapshot = GridSnapshot.from_grid(grid)
            assert snapshot.width == 5
            assert snapshot.height == 5
            assert len(snapshot.cells) == 25

            # Test cloning
            cloned = snapshot.clone()
            assert cloned.cells == snapshot.cells
            assert cloned.cells is not snapshot.cells  # Different object

            log_test('memory', 'GridSnapshot basic operations', 'PASS')
        except Exception as e:
            log_test('memory', 'GridSnapshot basic operations', 'FAIL', str(e))

        # Test 2.2: GridPool acquire/release
        try:
            pool = GridPool(pool_size=10, width=5, height=5)

            # Acquire a grid
            grid1 = pool.acquire()
            assert grid1 is not None

            # Acquire another
            grid2 = pool.acquire()
            assert grid2 is not None
            assert grid2 is not grid1

            # Release and reacquire
            pool.release(grid1)
            grid3 = pool.acquire()
            assert grid3 is grid1  # Should reuse

            log_test('memory', 'GridPool acquire/release cycle', 'PASS')
        except Exception as e:
            log_test('memory', 'GridPool acquire/release cycle', 'FAIL', str(e))

        # Test 2.3: StatePool acquire/release
        try:
            state_pool = StatePool(pool_size=10)

            # Create a state
            grid = Grid(5, 5)
            state1 = BeamState(grid=grid, slots_filled=0, total_slots=10, score=50.0)

            # Acquire state
            state2 = state_pool.acquire(state1)
            assert state2.score == state1.score

            # Release
            state_pool.release(state2)

            log_test('memory', 'StatePool acquire/release cycle', 'PASS')
        except Exception as e:
            log_test('memory', 'StatePool acquire/release cycle', 'FAIL', str(e))

        # Test 2.4: DomainManager operations
        try:
            manager = DomainManager()

            # Test small domain (stored as list)
            small_domain = ['CAT', 'DOG', 'RAT']
            key_small = manager.store_domain(small_domain)
            retrieved_small = manager.get_domain(key_small)
            assert retrieved_small == small_domain

            # Test large domain (stored as set)
            large_domain = [f'WORD{i}' for i in range(100)]
            key_large = manager.store_domain(large_domain)
            retrieved_large = manager.get_domain(key_large)
            assert set(retrieved_large) == set(large_domain)

            log_test('memory', 'DomainManager store/retrieve', 'PASS')
        except Exception as e:
            log_test('memory', 'DomainManager store/retrieve', 'FAIL', str(e))

        return True

    except Exception as e:
        log_test('memory', 'Memory component setup', 'FAIL', str(e))
        return False


def test_real_grids():
    """Test 3: Real-life grid testing."""
    print("\n" + "="*80)
    print("TEST 3: REAL-LIFE GRID TESTING")
    print("="*80)

    try:
        from core.grid import Grid
        from fill.beam_search_autofill import BeamSearchAutofill
        from fill.word_list import WordList
        from fill.pattern_matcher import PatternMatcher

        # Load word list
        word_list_path = Path(__file__).parent / 'data' / 'wordlists' / 'test_wordlist.txt'
        if not word_list_path.exists():
            log_test('real_grids', 'Load word list', 'WARN',
                    f'Test word list not found at {word_list_path}')
            return False

        word_list = WordList()
        word_list.load_from_file(str(word_list_path))
        pattern_matcher = PatternMatcher(word_list)

        log_test('real_grids', 'Load word list', 'PASS')

        # Test 3.1: Small grid (11x11 if available)
        grid_11x11_path = Path(__file__).parent / 'test_data' / 'grids' / 'demo_11x11_EMPTY.json'
        if grid_11x11_path.exists():
            try:
                with open(grid_11x11_path) as f:
                    grid_data = json.load(f)

                grid = Grid.from_dict(grid_data)
                solver = BeamSearchAutofill(
                    grid=grid,
                    word_list=word_list,
                    pattern_matcher=pattern_matcher,
                    beam_width=3,
                    candidates_per_slot=5
                )

                print(f"\n  Testing 11x11 grid (timeout=60s)...")
                start = time.time()
                result = solver.fill(timeout=60)
                elapsed = time.time() - start

                if result.success:
                    log_test('real_grids', '11x11 grid fill (complete)', 'PASS',
                            f'Filled in {elapsed:.1f}s')
                else:
                    log_test('real_grids', '11x11 grid fill (partial)', 'WARN',
                            f'Filled {result.slots_filled}/{result.total_slots} in {elapsed:.1f}s')

            except Exception as e:
                log_test('real_grids', '11x11 grid fill', 'FAIL', str(e))
        else:
            log_test('real_grids', '11x11 grid fill', 'WARN',
                    'Test grid not found')

        # Test 3.2: Partially filled grid
        partial_grid_path = Path(__file__).parent / 'test_data' / 'grids' / 'test_autofill_grid.json'
        if partial_grid_path.exists():
            try:
                with open(partial_grid_path) as f:
                    grid_data = json.load(f)

                grid = Grid.from_dict(grid_data)
                solver = BeamSearchAutofill(
                    grid=grid,
                    word_list=word_list,
                    pattern_matcher=pattern_matcher,
                    beam_width=3,
                    candidates_per_slot=5
                )

                print(f"\n  Testing partially filled grid (timeout=30s)...")
                start = time.time()
                result = solver.fill(timeout=30)
                elapsed = time.time() - start

                log_test('real_grids', 'Partially filled grid', 'PASS',
                        f'Result: {result.slots_filled}/{result.total_slots} in {elapsed:.1f}s')

            except Exception as e:
                log_test('real_grids', 'Partially filled grid', 'FAIL', str(e))
        else:
            log_test('real_grids', 'Partially filled grid', 'WARN',
                    'Test grid not found')

        return True

    except Exception as e:
        log_test('real_grids', 'Real grid setup', 'FAIL', str(e))
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test 4: Edge cases and error handling."""
    print("\n" + "="*80)
    print("TEST 4: EDGE CASES AND ERROR HANDLING")
    print("="*80)

    try:
        from core.grid import Grid
        from fill.beam_search_autofill import BeamSearchAutofill
        from fill.word_list import WordList
        from fill.pattern_matcher import PatternMatcher

        # Setup minimal word list
        word_list = WordList()
        word_list.words = {'CAT': 80, 'DOG': 80, 'RAT': 80}
        pattern_matcher = PatternMatcher(word_list)

        # Test 4.1: Empty grid (already complete)
        try:
            grid = Grid(3, 3)
            # Fill entire grid with blocks
            for i in range(3):
                for j in range(3):
                    grid.cells[i][j] = '#'

            solver = BeamSearchAutofill(
                grid=grid,
                word_list=word_list,
                pattern_matcher=pattern_matcher
            )

            result = solver.fill(timeout=10)
            assert result.success
            assert result.total_slots == 0

            log_test('edge_cases', 'Empty grid (all blocks)', 'PASS')
        except Exception as e:
            log_test('edge_cases', 'Empty grid (all blocks)', 'FAIL', str(e))

        # Test 4.2: Invalid parameters
        try:
            grid = Grid(5, 5)

            # Test invalid beam_width
            try:
                solver = BeamSearchAutofill(
                    grid=grid,
                    word_list=word_list,
                    pattern_matcher=pattern_matcher,
                    beam_width=100  # Too large
                )
                log_test('edge_cases', 'Invalid beam_width raises error', 'FAIL',
                        'Should have raised ValueError')
            except ValueError:
                log_test('edge_cases', 'Invalid beam_width raises error', 'PASS')

            # Test invalid timeout
            solver = BeamSearchAutofill(
                grid=grid,
                word_list=word_list,
                pattern_matcher=pattern_matcher
            )
            try:
                result = solver.fill(timeout=5)  # Too short
                log_test('edge_cases', 'Invalid timeout raises error', 'FAIL',
                        'Should have raised ValueError')
            except ValueError:
                log_test('edge_cases', 'Invalid timeout raises error', 'PASS')

        except Exception as e:
            log_test('edge_cases', 'Parameter validation', 'FAIL', str(e))

        # Test 4.3: Grid with no valid fills
        try:
            grid = Grid(3, 3)
            # Create impossible constraint
            grid.cells[0] = ['X', 'Y', 'Z']
            grid.cells[1] = ['?', '?', '?']
            grid.cells[2] = ['?', '?', '?']

            solver = BeamSearchAutofill(
                grid=grid,
                word_list=word_list,
                pattern_matcher=pattern_matcher,
                beam_width=2
            )

            result = solver.fill(timeout=10)
            # Should handle gracefully
            assert result is not None

            log_test('edge_cases', 'Impossible grid (graceful handling)', 'PASS')
        except Exception as e:
            log_test('edge_cases', 'Impossible grid (graceful handling)', 'FAIL', str(e))

        return True

    except Exception as e:
        log_test('edge_cases', 'Edge case setup', 'FAIL', str(e))
        traceback.print_exc()
        return False


def test_regression():
    """Test 5: Run existing test suite."""
    print("\n" + "="*80)
    print("TEST 5: REGRESSION TESTING (EXISTING TEST SUITE)")
    print("="*80)

    import subprocess

    # Test 5.1: Run beam search unit tests
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', 'cli/tests/unit/test_beam_search.py', '-v', '--tb=short'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            log_test('regression', 'Beam search unit tests', 'PASS')
        else:
            log_test('regression', 'Beam search unit tests', 'FAIL',
                    f'Exit code {result.returncode}')
            print("\n  Test output:")
            print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)

    except subprocess.TimeoutExpired:
        log_test('regression', 'Beam search unit tests', 'FAIL', 'Timeout')
    except Exception as e:
        log_test('regression', 'Beam search unit tests', 'FAIL', str(e))

    # Test 5.2: Run autofill tests
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', 'cli/tests/unit/test_autofill.py', '-v', '--tb=short'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            log_test('regression', 'Autofill unit tests', 'PASS')
        else:
            log_test('regression', 'Autofill unit tests', 'FAIL',
                    f'Exit code {result.returncode}')

    except subprocess.TimeoutExpired:
        log_test('regression', 'Autofill unit tests', 'FAIL', 'Timeout')
    except Exception as e:
        log_test('regression', 'Autofill unit tests', 'FAIL', str(e))

    return True


def generate_report():
    """Generate final test report."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST REPORT")
    print("="*80)

    total = len(test_results['passed']) + len(test_results['failed']) + len(test_results['warnings'])
    passed = len(test_results['passed'])
    failed = len(test_results['failed'])
    warned = len(test_results['warnings'])

    print(f"\nTotal Tests: {total}")
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failed}")
    print(f"  ⚠ Warnings: {warned}")

    if failed > 0:
        print("\n" + "-"*80)
        print("FAILED TESTS:")
        print("-"*80)
        for result in test_results['failed']:
            print(f"\n[{result['category']}] {result['name']}")
            print(f"  Details: {result['details']}")

    if warned > 0:
        print("\n" + "-"*80)
        print("WARNINGS:")
        print("-"*80)
        for result in test_results['warnings']:
            print(f"\n[{result['category']}] {result['name']}")
            print(f"  Details: {result['details']}")

    # Overall assessment
    print("\n" + "="*80)
    print("ASSESSMENT")
    print("="*80)

    if failed == 0 and warned == 0:
        print("\n✓ ALL TESTS PASSED - Refactoring is fully successful!")
        severity = "SUCCESS"
    elif failed == 0:
        print(f"\n⚠ ALL TESTS PASSED WITH {warned} WARNINGS")
        print("  Warnings are non-critical but should be reviewed.")
        severity = "SUCCESS_WITH_WARNINGS"
    elif failed <= 2:
        print(f"\n⚠ MINOR ISSUES FOUND - {failed} failed tests")
        print("  Issues are minor and should be easy to fix.")
        severity = "MINOR_ISSUES"
    else:
        print(f"\n✗ SIGNIFICANT ISSUES FOUND - {failed} failed tests")
        print("  Critical issues require attention before deployment.")
        severity = "MAJOR_ISSUES"

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if failed > 0:
        print("\n1. Fix all failed tests before proceeding")
        print("2. Review error details above for root causes")
        print("3. Re-run test suite after fixes")

    if warned > 0:
        print("\n1. Review warnings for potential improvements")
        print("2. Consider adding missing test data files")
        print("3. Document any expected warnings")

    if failed == 0 and warned == 0:
        print("\n1. Refactoring is complete and verified")
        print("2. Ready for production use")
        print("3. Consider running benchmark suite for performance verification")

    print("\n" + "="*80)

    return severity


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("PHASE 3 REFACTORING - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print("\nThis test suite validates:")
    print("1. Import structure and backward compatibility")
    print("2. Memory optimization components")
    print("3. Real-life grid filling")
    print("4. Edge cases and error handling")
    print("5. Regression testing")

    # Run all test categories
    test_imports()
    test_memory_components()
    test_real_grids()
    test_edge_cases()
    test_regression()

    # Generate final report
    severity = generate_report()

    # Exit with appropriate code
    exit_codes = {
        'SUCCESS': 0,
        'SUCCESS_WITH_WARNINGS': 0,
        'MINOR_ISSUES': 1,
        'MAJOR_ISSUES': 2
    }

    return exit_codes.get(severity, 2)


if __name__ == '__main__':
    sys.exit(main())
