# Performance & Benchmark Tests

This directory contains **manual performance benchmarks** for the crossword autofill system.

⚠️ **Note:** These are standalone Python scripts, **not automated CI tests**. They must be run manually when needed.

## Files

- **benchmark_algorithms.py** - Algorithm performance benchmarks
  - Compares Regex vs Trie pattern matching
  - Measures time and memory usage
  - Generates detailed performance reports

- **benchmark_memory_optimization.py** - Memory optimization benchmarks
  - Tests memory usage during autofill
  - Validates memory optimization strategies
  - Monitors memory leaks

## Running Benchmarks

These are **standalone scripts** that should be run directly with Python:

```bash
# Run algorithm benchmarks
python cli/tests/performance/benchmark_algorithms.py

# Run memory benchmarks
python cli/tests/performance/benchmark_memory_optimization.py
```

**Note:** Do NOT run with pytest - these are not pytest tests.

## Performance Targets

- 11×11 grid: <30 seconds, 90%+ completion
- 15×15 grid: <180 seconds, 85%+ completion
- Memory: <500MB peak usage for 15×15 grids

## Notes

- Benchmarks may take several minutes to complete
- Results are affected by system load and hardware
- Run benchmarks on a quiet system for accurate results
