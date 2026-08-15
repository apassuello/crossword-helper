# Backend Test Suite

Comprehensive test suite for the crossword helper backend, with special focus on CLI integration and data transformation validation.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Critical Tests](#critical-tests)
- [Writing New Tests](#writing-new-tests)

---

## Overview

This test suite is designed to catch integration bugs, particularly around:

1. **Grid data format transformation** (frontend → CLI)
2. **CLI subprocess execution and communication**
3. **API endpoint validation and error handling**
4. **Progress tracking and SSE endpoints**

### Why These Tests Exist

A critical bug was missed where the frontend sent grid data in this format:
```json
{"letter": "A", "isBlack": false}
```

But the CLI expected:
```json
"A"
```

This caused an immediate crash with `AttributeError` when the CLI tried to process the grid. **These tests are designed to catch such bugs.**

---

## Test Structure

```
backend/tests/
├── README.md                           # This file
├── TEST_COVERAGE_ANALYSIS.md          # Detailed coverage analysis
├── conftest.py                        # Pytest configuration
├── fixtures/
│   ├── __init__.py
│   └── grid_fixtures.py               # Test data in various formats
├── unit/
│   └── test_grid_transformation.py    # Fast transformation tests
├── integration/
│   ├── test_api.py                    # Existing API tests
│   ├── test_cli_integration.py        # NEW: CLI integration tests
│   └── test_progress_integration.py   # NEW: Progress endpoint tests
└── test_api.py                        # Legacy test location
```

### Test Types

#### Unit Tests (`unit/`)
- **Fast**: Run in <1 second
- **Isolated**: No external dependencies (no CLI, no network)
- **Focused**: Test single functions or classes
- **Example**: Grid transformation logic

#### Integration Tests (`integration/`)
- **Slower**: May take 5-30 seconds
- **Real execution**: Actually spawn CLI subprocess
- **End-to-end**: Test full request/response cycle
- **Example**: POST /api/fill with real CLI

---

## Running Tests

### Run All Tests
```bash
pytest backend/tests/
```

### Run Only Fast Tests (Skip Slow Integration Tests)
```bash
pytest backend/tests/ -m "not slow"
```

### Run Only Integration Tests
```bash
pytest backend/tests/integration/
```

### Run Only Unit Tests
```bash
pytest backend/tests/unit/
```

### Run Specific Test File
```bash
pytest backend/tests/integration/test_cli_integration.py
```

### Run Specific Test
```bash
pytest backend/tests/integration/test_cli_integration.py::TestFillEndpointIntegration::test_fill_endpoint_with_empty_grid
```

### Run With Coverage Report
```bash
pytest backend/tests/ --cov=backend --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Run With Verbose Output
```bash
pytest backend/tests/ -v
```

### Run With Extra Debugging
```bash
pytest backend/tests/ -vv -s
```

---

## Test Coverage

### Current Coverage Goals

| Component | Target | Status |
|-----------|--------|--------|
| Grid transformation | 95% | ✅ Achieved |
| API routes | 85% | ✅ Achieved |
| CLI integration | 80% | ✅ Achieved |
| Progress tracking | 70% | ✅ Achieved |
| Error handling | 90% | ✅ Achieved |

### What Is Tested

✅ **Grid Format Transformation**
- Empty cells → "."
- Black cells → "#"
- Filled cells → letter (uppercased)
- Mixed formats
- Edge cases

✅ **CLI Integration**
- Health checks
- Pattern search
- Grid numbering
- Autofill operations
- Timeout handling
- Error handling

✅ **API Endpoints**
- /api/fill
- /api/fill/with-progress
- /api/pattern/with-progress
- All validation logic
- Error responses

✅ **Data Format Bug Regression**
- Specific tests that catch the original bug
- Would fail if transformation code is removed

---

## Critical Tests

### 🔴 Most Important Tests (Do NOT Skip)

#### 1. Grid Transformation Tests
**File**: `backend/tests/unit/test_grid_transformation.py`

**Key Test**:
```python
test_bug_frontend_dict_format_is_transformed()
```

This test verifies that `{"letter": "A", "isBlack": false}` is correctly transformed to `"A"`.

**Why Critical**: This is the EXACT bug that was missed. If this test fails, the bug is back.

#### 2. CLI Integration Tests
**File**: `backend/tests/integration/test_cli_integration.py`

**Key Test**:
```python
test_fill_command_with_real_grid()
```

This test actually executes the CLI with a grid and verifies it doesn't crash.

**Why Critical**: This catches the bug at integration level with real CLI execution.

#### 3. API Endpoint Tests
**File**: `backend/tests/integration/test_cli_integration.py`

**Key Test**:
```python
test_fill_endpoint_with_empty_grid()
```

This test sends a frontend-format grid through the API to the CLI.

**Why Critical**: End-to-end test that catches the bug in production scenario.

### How to Verify Bug Is Fixed

Run these three tests:
```bash
pytest backend/tests/unit/test_grid_transformation.py::TestGridTransformationBugRegression::test_bug_frontend_dict_format_is_transformed -v

pytest backend/tests/integration/test_cli_integration.py::TestCLIAdapterIntegration::test_fill_command_with_real_grid -v

pytest backend/tests/integration/test_cli_integration.py::TestFillEndpointIntegration::test_fill_endpoint_with_empty_grid -v
```

All three should pass. If any fail, the bug exists.

---

## Writing New Tests

### Test Naming Convention

```python
# Unit test
def test_grid_transformation_handles_empty_cells():
    """Test that empty cells become '.' in CLI format."""
    ...

# Integration test
@pytest.mark.slow
def test_fill_endpoint_with_real_cli():
    """Test /api/fill with actual CLI execution."""
    ...
```

### Using Test Fixtures

```python
from backend.tests.fixtures import EMPTY_3X3_FRONTEND, EMPTY_3X3_CLI

def test_transformation():
    frontend_grid = EMPTY_3X3_FRONTEND["grid"]
    expected_cli = EMPTY_3X3_CLI["grid"]
    # ... test logic
```

Available fixtures:
- `EMPTY_3X3_FRONTEND`, `EMPTY_3X3_CLI`
- `PARTIALLY_FILLED_3X3_FRONTEND`, `PARTIALLY_FILLED_3X3_CLI`
- `PATTERN_3X3_FRONTEND`, `PATTERN_3X3_CLI`
- `MIXED_3X3_FRONTEND`, `MIXED_3X3_CLI`
- `EMPTY_5X5_FRONTEND`, `EMPTY_5X5_CLI`
- And more... (see `fixtures/grid_fixtures.py`)

### Marking Slow Tests

```python
import pytest

@pytest.mark.slow
def test_large_grid_fill():
    """Test that takes >5 seconds."""
    ...
```

### Marking Integration Tests

```python
import pytest

@pytest.mark.integration
def test_api_endpoint():
    """Integration test."""
    ...
```

### Skipping Tests Without CLI

```python
@pytest.mark.slow
def test_requires_cli(skip_if_no_cli):
    """This test requires CLI to be installed."""
    # Test will auto-skip if CLI not available
    ...
```

---

## Test Data

### Frontend Format (What API Receives)

```python
{
    "size": 3,
    "grid": [
        [{"letter": "A", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": True}, {"letter": "B", "isBlack": False}]
    ]
}
```

### CLI Format (What CLI Expects)

```python
{
    "size": 3,
    "grid": [
        ["A", "."],
        ["#", "B"]
    ]
}
```

### Transformation Rules

| Frontend | CLI | Note |
|----------|-----|------|
| `{"letter": "A", "isBlack": false}` | `"A"` | Filled cell |
| `{"letter": "", "isBlack": false}` | `"."` | Empty cell |
| `{"letter": "", "isBlack": true}` | `"#"` | Black square |
| `{"letter": "a", "isBlack": false}` | `"A"` | Uppercased |

---

## Debugging Failed Tests

### Test Failed: "AttributeError"

**Likely cause**: Grid format transformation is broken.

**Check**:
1. Look at routes.py lines 204-218 (transformation code)
2. Run: `pytest backend/tests/unit/test_grid_transformation.py -v`
3. Verify transformation logic is correct

### Test Failed: "CLI not found"

**Likely cause**: CLI is not installed or path is wrong.

**Fix**:
```bash
# Check CLI path
ls -la cli/crossword

# Rebuild CLI if needed
cd cli
python -m pip install -e .
```

### Test Failed: "Timeout"

**Likely cause**: Grid is too large or CLI is slow.

**Fix**: Increase timeout or use smaller test grid.

### Test Failed: "Wordlist not found"

**Likely cause**: Test wordlist doesn't exist.

**Fix**: Use "comprehensive" wordlist or create test wordlist.

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd cli && pip install -e .

      - name: Run fast tests
        run: pytest backend/tests/ -m "not slow" --cov=backend

      - name: Run slow tests
        run: pytest backend/tests/ -m "slow" --cov=backend --cov-append

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Maintenance

### When to Update Tests

1. **Adding new API endpoint**: Add integration test
2. **Changing grid format**: Update fixtures and transformation tests
3. **Modifying CLI interface**: Update CLI integration tests
4. **Bug fix**: Add regression test

### Review Checklist

Before merging code:
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Coverage maintained or improved
- [ ] No skipped tests without good reason
- [ ] Slow tests marked with `@pytest.mark.slow`

---

## Additional Resources

- **Coverage Analysis**: See `TEST_COVERAGE_ANALYSIS.md`
- **Fixtures Documentation**: See `fixtures/grid_fixtures.py`
- **Pytest Docs**: https://docs.pytest.org/

---

## Quick Reference

### Common Commands

```bash
# Fast tests only
pytest backend/tests/ -m "not slow"

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Specific file
pytest backend/tests/integration/test_cli_integration.py

# Verbose output
pytest backend/tests/ -vv -s

# Stop on first failure
pytest backend/tests/ -x

# Run last failed tests
pytest backend/tests/ --lf
```

### Test Markers

- `@pytest.mark.slow` - Test takes >5 seconds
- `@pytest.mark.integration` - Integration test (uses real CLI)
- `@pytest.mark.unit` - Unit test (no external dependencies)

### Exit Codes

- `0` - All tests passed
- `1` - Tests failed
- `2` - Test execution was interrupted
- `3` - Internal error
- `4` - pytest command line usage error
- `5` - No tests collected

---

**Last Updated**: 2025-12-26
**Test Suite Version**: 1.0.0
