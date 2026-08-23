# Test Files Organization

## Summary of Cleanup

This document describes the test file organization after cleanup on 2024-12-25.

## Directory Structure

```
crossword-helper/
├── backend/tests/          # Backend (web app) tests
│   ├── unit/              # Unit tests for backend modules
│   ├── integration/       # API integration tests
│   └── test_api.py        # Main API test suite
│
├── cli/tests/             # CLI tool tests
│   ├── unit/              # Unit tests for CLI modules
│   │   ├── test_autofill.py
│   │   ├── test_beam_search.py
│   │   ├── test_cell_types.py
│   │   ├── test_grid.py
│   │   ├── test_pattern_matcher.py
│   │   ├── test_phase4_regression.py
│   │   ├── test_phase4_regression_simplified.py
│   │   ├── test_word_list.py
│   │   ├── test_word_list_gibberish.py
│   │   └── ...
│   └── integration/       # CLI integration tests
│       └── test_phase2_fixes.py
│
├── test_data/             # Test data files (JSON)
│   ├── grids/            # Test grid files
│   │   ├── demo_11x11_*.json
│   │   ├── test_grid_*.json
│   │   └── ...
│   ├── phase4/           # Phase 4 specific test data
│   │   ├── phase4_*.json
│   │   └── ...
│   └── results/          # Test results
│
└── scripts/debug/         # Debug and analysis scripts
    ├── analyze_test_result.py
    ├── debug_fill.py
    ├── debug_fill_simple.py
    └── test_gibberish_fix.py
```

## Changes Made

### 1. Moved Test Data Files
- **Before**: 24 JSON test files scattered in root directory
- **After**: Organized into `test_data/grids/` and `test_data/phase4/`

### 2. Moved Debug Scripts
- **Before**: Debug scripts in root and `cli/` directory
- **After**: Consolidated in `scripts/debug/`

### 3. Consolidated Backend Tests
- **Before**: Tests split between `tests/` and `backend/tests/`
- **After**: All backend tests in `backend/tests/`
- **Removed**: Empty `tests/` directory

### 4. Preserved Test Separation
- Backend tests: `backend/tests/` (for web app)
- CLI tests: `cli/tests/` (for command-line tool)

## Test Statistics

### CLI Tests
- **Unit Tests**: 15 test files, 288 tests total
  - 269 passing
  - 19 failing (mostly due to recent refactoring)
- **Integration Tests**: 1 test file, 10 tests passing

### Backend Tests
- **Unit Tests**: 5 test files (need import fixes)
- **Integration Tests**: 1 test file (mostly empty)
- **API Tests**: 1 comprehensive test file (434 lines)

## Files Removed/Moved

### From Root Directory
- `debug_fill.py` → `scripts/debug/`
- `analyze_test_result.py` → `scripts/debug/`
- All `.json` test files → `test_data/`

### From CLI Directory
- `cli/debug_fill_simple.py` → `scripts/debug/`
- `cli/test_gibberish_fix.py` → `scripts/debug/`
- `cli/test_*.json` → `test_data/grids/`

## Running Tests

### CLI Tests
```bash
# Run all CLI tests
pytest cli/tests/

# Run unit tests only
pytest cli/tests/unit/

# Run integration tests only
pytest cli/tests/integration/

# Run with coverage
pytest cli/tests/ --cov=cli/src
```

### Backend Tests
```bash
# Run all backend tests
pytest backend/tests/

# Run API tests
pytest backend/tests/test_api.py

# Note: Some unit tests need import fixes after refactoring
```

## Next Steps

1. Fix failing tests in `cli/tests/unit/` (19 failures)
2. Fix import errors in `backend/tests/unit/`
3. Consider removing duplicate/obsolete test files:
   - `test_phase4_regression.py` vs `test_phase4_regression_simplified.py`
4. Add more integration tests for both backend and CLI
5. Set up CI/CD to run all tests automatically

## Test Coverage Goals

- CLI: Target >90% coverage for core modules
- Backend: Target >80% coverage for API routes
- Integration: Cover all critical user workflows