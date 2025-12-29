# Performance & Benchmark Tests

This directory contains performance benchmarks and stress tests for the crossword autofill system.

## Files

- **benchmark_algorithms.py** - Algorithm performance benchmarks
  - Tests beam search performance on various grid sizes
  - Measures time and memory usage
  - Validates performance targets

- **benchmark_memory_optimization.py** - Memory optimization benchmarks
  - Tests memory usage during autofill
  - Validates memory optimization strategies
  - Monitors memory leaks

## Running Benchmarks

These tests are marked as `slow` and are skipped by default during regular test runs.

```bash
# Run all benchmarks
pytest cli/tests/performance/ -v

# Run specific benchmark
pytest cli/tests/performance/benchmark_algorithms.py -v

# Include benchmarks in full test run
pytest -m slow
```

## Performance Targets

- 11×11 grid: <30 seconds, 90%+ completion
- 15×15 grid: <180 seconds, 85%+ completion
- Memory: <500MB peak usage for 15×15 grids

## Notes

- Benchmarks may take several minutes to complete
- Results are affected by system load and hardware
- Run benchmarks on a quiet system for accurate results
