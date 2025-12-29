"""
Performance benchmarks for Phase 3 memory optimizations.

Measures memory usage and performance improvements from Days 9-10:
- GridSnapshot (copy-on-write grid cloning)
- GridPool (object pooling for grids)
- StatePool (object pooling for states)
- DomainManager (bitset domain representation)

Usage:
    python -m cli.tests.benchmark_memory_optimization
    python -m cli.tests.benchmark_memory_optimization --verbose
"""

import sys
import time
import gc
from typing import List, Tuple
import tracemalloc

# Add project root to path
sys.path.insert(0, '/Users/apa/projects/untitled_project/crossword-helper')

from cli.src.core.grid import Grid
from cli.src.fill.beam_search.state import BeamState
from cli.src.fill.beam_search.memory import (
    GridSnapshot,
    GridPool,
    StatePool,
    DomainManager,
    SetDomain,
    BitsetDomain
)


class BenchmarkResults:
    """Container for benchmark results."""

    def __init__(self):
        self.results = {}

    def add_result(self, name: str, value: float, unit: str):
        """Add a benchmark result."""
        self.results[name] = {'value': value, 'unit': unit}

    def print_summary(self):
        """Print formatted summary of results."""
        print("\n" + "=" * 70)
        print(" MEMORY OPTIMIZATION BENCHMARK RESULTS")
        print("=" * 70)

        for name, data in self.results.items():
            print(f"{name:50s} {data['value']:>10.2f} {data['unit']}")

        print("=" * 70)

    def calculate_improvements(self):
        """Calculate percentage improvements."""
        improvements = {}

        # Grid cloning memory improvement
        if 'Traditional Grid Clone Memory (KB)' in self.results and \
           'GridSnapshot Clone Memory (KB)' in self.results:
            traditional = self.results['Traditional Grid Clone Memory (KB)']['value']
            snapshot = self.results['GridSnapshot Clone Memory (KB)']['value']
            if traditional > 0:
                improvement = ((traditional - snapshot) / traditional) * 100
                improvements['Grid Clone Memory Reduction'] = f"{improvement:.1f}%"

        # Grid pool hit rate
        if 'GridPool Hit Rate' in self.results:
            hit_rate = self.results['GridPool Hit Rate']['value']
            improvements['GridPool Cache Efficiency'] = f"{hit_rate:.1f}%"

        # State pool hit rate
        if 'StatePool Hit Rate' in self.results:
            hit_rate = self.results['StatePool Hit Rate']['value']
            improvements['StatePool Cache Efficiency'] = f"{hit_rate:.1f}%"

        # Domain memory improvement
        if 'SetDomain Memory (bytes)' in self.results and \
           'BitsetDomain Memory (bytes)' in self.results:
            set_mem = self.results['SetDomain Memory (bytes)']['value']
            bitset_mem = self.results['BitsetDomain Memory (bytes)']['value']
            if set_mem > 0:
                improvement = ((set_mem - bitset_mem) / set_mem) * 100
                improvements['Domain Memory Reduction'] = f"{improvement:.1f}%"

        if improvements:
            print("\n" + "-" * 70)
            print(" KEY IMPROVEMENTS")
            print("-" * 70)
            for name, value in improvements.items():
                print(f"{name:50s} {value:>19s}")
            print("-" * 70)


def benchmark_grid_cloning(results: BenchmarkResults, grid_size: int = 15, num_clones: int = 100):
    """
    Benchmark grid cloning: traditional vs GridSnapshot.

    Args:
        results: BenchmarkResults to update
        grid_size: Grid size (NxN)
        num_clones: Number of clones to create
    """
    print(f"\n[1/5] Benchmarking grid cloning ({grid_size}x{grid_size}, {num_clones} clones)...")

    # GridSnapshot cloning (copy-on-write)
    gc.collect()
    tracemalloc.start()

    # Create grid data for snapshot (simulate a filled grid)
    grid_data = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
    for i in range(min(grid_size, 10)):
        grid_data[i][i] = 'A'

    snapshot = GridSnapshot(data=grid_data)

    start_memory = tracemalloc.get_traced_memory()[0]
    start_time = time.time()

    snapshots = []
    for _ in range(num_clones):
        snapshots.append(snapshot.clone())

    end_time = time.time()
    end_memory = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()

    snapshot_time = (end_time - start_time) * 1000  # ms
    snapshot_memory = (end_memory - start_memory) / 1024  # KB

    results.add_result('GridSnapshot Clone Time (ms)', snapshot_time, 'ms')
    results.add_result('GridSnapshot Clone Memory (KB)', snapshot_memory, 'KB')

    # Estimate traditional cloning (based on grid size)
    # Traditional: each clone stores full 15x15 = 225 cells
    # GridSnapshot: each clone stores only parent reference + empty modifications dict
    traditional_memory_estimate = (grid_size * grid_size * num_clones) / 1024  # KB (rough estimate)

    results.add_result('Traditional Grid Clone Memory (est. KB)', traditional_memory_estimate, 'KB')

    print(f"  GridSnapshot: {snapshot_memory:.2f} KB, {snapshot_time:.2f} ms")
    print(f"  Traditional (estimated): {traditional_memory_estimate:.2f} KB")
    print(f"  Memory reduction (est.): {((traditional_memory_estimate - snapshot_memory) / traditional_memory_estimate * 100):.1f}%")


def benchmark_grid_pool(results: BenchmarkResults, grid_size: int = 15, num_operations: int = 500):
    """
    Benchmark grid pooling efficiency.

    Args:
        results: BenchmarkResults to update
        grid_size: Grid size (NxN)
        num_operations: Number of acquire/release operations
    """
    print(f"\n[2/5] Benchmarking grid pooling ({num_operations} operations)...")

    pool = GridPool(grid_size=grid_size, pool_size=50)

    # Simulate realistic usage pattern
    active_grids = []

    for i in range(num_operations):
        # Acquire grids
        if i % 3 == 0 and len(active_grids) < 20:
            grid = pool.acquire()
            active_grids.append(grid)

        # Release grids
        if i % 5 == 0 and active_grids:
            grid = active_grids.pop(0)
            pool.release(grid)

    # Release remaining
    for grid in active_grids:
        pool.release(grid)

    stats = pool.get_stats()
    results.add_result('GridPool Created', stats['total_created'], 'grids')
    results.add_result('GridPool Reused', stats['total_reused'], 'grids')
    results.add_result('GridPool Hit Rate', stats['hit_rate'], '%')

    print(f"  Created: {stats['total_created']}, Reused: {stats['total_reused']}")
    print(f"  Hit rate: {stats['hit_rate']:.1f}%")


def benchmark_state_pool(results: BenchmarkResults, num_operations: int = 1000):
    """
    Benchmark state pooling efficiency.

    Args:
        results: BenchmarkResults to update
        num_operations: Number of acquire/release operations
    """
    print(f"\n[3/5] Benchmarking state pooling ({num_operations} operations)...")

    pool = StatePool(pool_size=100)

    # Create template state (use GridSnapshot instead of Grid)
    grid_data = [['.' for _ in range(15)] for _ in range(15)]
    grid_snapshot = GridSnapshot(data=grid_data)

    template = BeamState(
        grid=grid_snapshot,
        slots_filled=10,
        total_slots=76,
        score=850.0,
        used_words={'HELLO', 'WORLD', 'TEST'},
        slot_assignments={(0, 0, 'across'): 'HELLO'}
    )

    # Simulate usage
    active_states = []

    for i in range(num_operations):
        # Acquire states
        if i % 2 == 0 and len(active_states) < 50:
            state = pool.acquire_from_template(template)
            active_states.append(state)

        # Release states
        if i % 7 == 0 and active_states:
            state = active_states.pop(0)
            pool.release(state)

    # Release remaining
    for state in active_states:
        pool.release(state)

    stats = pool.get_stats()
    results.add_result('StatePool Created', stats['total_created'], 'states')
    results.add_result('StatePool Reused', stats['total_reused'], 'states')
    results.add_result('StatePool Hit Rate', stats['hit_rate'], '%')

    print(f"  Created: {stats['total_created']}, Reused: {stats['total_reused']}")
    print(f"  Hit rate: {stats['hit_rate']:.1f}%")


def benchmark_domain_manager(results: BenchmarkResults):
    """
    Benchmark domain manager (bitset vs set).

    Args:
        results: BenchmarkResults to update
    """
    print(f"\n[4/5] Benchmarking domain manager (bitset vs set)...")

    # Mock word list for testing
    class MockWordList:
        def find(self, pattern, min_score=0):
            # Return mock candidates
            if len(pattern) <= 5:
                return [('CAT', 50), ('BAT', 45), ('RAT', 40), ('HAT', 38), ('MAT', 35)]
            else:
                # Return 100 words for large domain test
                return [(f'WORD{i:03d}', 50 - i) for i in range(100)]

    word_list = MockWordList()
    manager = DomainManager(word_list)

    # Benchmark small domain (bitset)
    gc.collect()
    tracemalloc.start()

    start_memory = tracemalloc.get_traced_memory()[0]
    small_domain = manager.create_domain_for_pattern('?AT', min_score=0)
    end_memory = tracemalloc.get_traced_memory()[0]

    bitset_memory = end_memory - start_memory
    tracemalloc.stop()

    results.add_result('BitsetDomain Memory (bytes)', bitset_memory, 'bytes')
    print(f"  BitsetDomain (5 words): {bitset_memory} bytes")

    # Benchmark large domain (set)
    gc.collect()
    tracemalloc.start()

    start_memory = tracemalloc.get_traced_memory()[0]
    large_domain = manager.create_domain_for_pattern('???????', min_score=0)
    end_memory = tracemalloc.get_traced_memory()[0]

    set_memory = end_memory - start_memory
    tracemalloc.stop()

    results.add_result('SetDomain Memory (bytes)', set_memory, 'bytes')
    print(f"  SetDomain (100 words): {set_memory} bytes")

    # Get manager stats
    stats = manager.get_stats()
    results.add_result('DomainManager Cache Hits', stats['cache_hits'], 'hits')

    print(f"  Cache hits: {stats['cache_hits']}")


def benchmark_overall_memory_impact(results: BenchmarkResults):
    """
    Benchmark overall memory impact of all optimizations combined.

    Args:
        results: BenchmarkResults to update
    """
    print(f"\n[5/5] Benchmarking overall memory impact...")

    # Simulate realistic beam search scenario
    grid_size = 15
    beam_width = 5
    num_iterations = 50

    # Estimate traditional approach memory
    # Each iteration creates beam_width new grid clones (15x15 = 225 bytes each)
    # Plus beam_width new states (~200 bytes each)
    traditional_total_memory = (num_iterations * beam_width * (grid_size * grid_size + 200)) / 1024  # KB estimate

    results.add_result('Traditional Beam Search Memory (est. KB)', traditional_total_memory, 'KB')
    print(f"  Traditional approach (estimated): {traditional_total_memory:.2f} KB")

    # With optimizations
    gc.collect()
    tracemalloc.start()

    start_memory = tracemalloc.get_traced_memory()[0]

    grid_pool = GridPool(grid_size=grid_size, pool_size=50)
    state_pool = StatePool(pool_size=100)

    # Create initial beam with snapshots
    beam_optimized = []
    root_snapshot = GridSnapshot(height=grid_size, width=grid_size)

    for _ in range(beam_width):
        snapshot = root_snapshot.clone()
        state = state_pool.acquire()
        state.grid = snapshot  # Use snapshot instead of grid
        state.slots_filled = 0
        state.total_slots = 76
        state.score = 0.0
        state.used_words = set()
        state.slot_assignments = {}
        beam_optimized.append(state)

    # Simulate iterations with pooling
    for iteration in range(num_iterations):
        new_beam = []
        for state in beam_optimized:
            # Clone snapshot (copy-on-write)
            new_snapshot = state.grid.clone()
            new_state = state_pool.acquire_from_template(state)
            new_state.grid = new_snapshot
            new_beam.append(new_state)

        # Release old states
        for state in beam_optimized:
            state_pool.release(state)

        beam_optimized = new_beam[:beam_width]

    # Cleanup
    for state in beam_optimized:
        state_pool.release(state)

    end_memory = tracemalloc.get_traced_memory()[0]
    optimized_total_memory = (end_memory - start_memory) / 1024  # KB
    tracemalloc.stop()

    results.add_result('Optimized Beam Search Memory (KB)', optimized_total_memory, 'KB')
    print(f"  Optimized approach: {optimized_total_memory:.2f} KB")

    # Calculate overall improvement
    if traditional_total_memory > 0:
        overall_improvement = ((traditional_total_memory - optimized_total_memory) / traditional_total_memory) * 100
        results.add_result('Overall Memory Reduction', overall_improvement, '%')
        print(f"  Overall improvement: {overall_improvement:.1f}%")


def main():
    """Run all benchmarks."""
    print("\n" + "=" * 70)
    print(" PHASE 3 MEMORY OPTIMIZATION BENCHMARKS")
    print("=" * 70)
    print("\nTesting memory improvements from Days 9-10:")
    print("  - GridSnapshot (copy-on-write)")
    print("  - GridPool (object pooling)")
    print("  - StatePool (object pooling)")
    print("  - DomainManager (bitset domains)")
    print("\nTarget: 70% memory reduction")

    results = BenchmarkResults()

    try:
        benchmark_grid_cloning(results)
        benchmark_grid_pool(results)
        benchmark_state_pool(results)
        benchmark_domain_manager(results)
        benchmark_overall_memory_impact(results)

        results.print_summary()
        results.calculate_improvements()

        print("\n✅ All benchmarks completed successfully!")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
