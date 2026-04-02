# Known Issues

**Last Updated**: April 2, 2026
**Status**: All critical issues resolved

---

## Resolved Issues

### 1. Custom Wordlists Not Displaying in UI - FIXED

**Status**: FIXED (December 28, 2025)
**Root Cause**: Missing `name` field in wordlist metadata caused silent frontend crash.
**Fix**: `backend/data/wordlist_manager.py` lines 121-129 — always merge default metadata.

### 2. `--theme-entries` CLI Flag - FIXED

**Status**: FIXED (March 2026)
**Root Cause**: The canary test was passing raw JSON instead of a file path. The feature itself worked correctly.
**Fix**: Corrected the test in commit `5717495`.

### 3. `--adaptive` CLI Flag - FIXED

**Status**: FIXED (March 2026)
**Root Cause**: Previously reported as non-functional, but the feature started working after performance fixes (trie score bound initialization, beam timeout scaling). The canary test now passes — adaptive mode successfully adds black squares to empty grids.
**Verified**: Canary test `test_adaptive_mode_adds_black_squares` passes (7x7 grid, beam algorithm).

### 4. Hardcoded Developer Paths in Tests - FIXED

**Status**: FIXED (April 2, 2026)
**Root Cause**: `cli/tests/unit/test_analyze_command.py` and `cli/tests/performance/benchmark_memory_optimization.py` contained hardcoded `/Users/apa/projects/...` paths.
**Fix**: Replaced with dynamic project root detection using `os.path.dirname`.

---

## Remaining Minor Issues

### pytest.ini Coverage Flags

**Status**: FIXED (April 2, 2026)
**Problem**: `addopts` included `--cov` flags that required `pytest-cov` to be installed. Bare `pytest` would fail without it.
**Fix**: Moved coverage flags out of `addopts`. Run coverage explicitly: `pytest --cov=backend --cov=cli`.

### Theme Word Priority - Untested End-to-End

**Status**: Code complete, not verified end-to-end
**Impact**: Low — unit tests pass, algorithm integration exists, but no full workflow test confirming theme words appear preferentially in filled grids.

---

## What Works

- Custom wordlist upload and management
- Pattern matching (regex, trie algorithms)
- Grid validation and auto-numbering
- Autofill (CSP, Beam Search, Hybrid algorithms)
- Pause/resume autofill with grid edits
- Adaptive autofill with automatic black square placement
- Theme entry locking (CLI and web UI)
- Constraint analysis and crossing quality heatmap
- Export (HTML, JSON)
- Real-time progress tracking via SSE
