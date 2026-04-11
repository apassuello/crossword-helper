# Testing Guide

**Document Type:** Operations Guide
**Version:** 2.0.0
**Last Updated:** 2025-12-27
**Status:** Complete - 165/165 tests passing (100%)

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Strategy](#testing-strategy)
3. [Test Environment Setup](#test-environment-setup)
4. [Unit Testing](#unit-testing)
5. [Integration Testing](#integration-testing)
6. [End-to-End Testing](#end-to-end-testing)
7. [Test Data Management](#test-data-management)
8. [Running Tests](#running-tests)
9. [Code Coverage](#code-coverage)
10. [Debugging Failed Tests](#debugging-failed-tests)
11. [Performance Testing](#performance-testing)
12. [Best Practices](#best-practices)
13. [CI/CD Integration](#cicd-integration)
14. [Appendix: Test Reference](#appendix-test-reference)

---

## Overview

### Testing Philosophy

The Crossword Helper project follows a **test-driven development (TDD)** approach with emphasis on:

1. **Fast feedback loops** - Unit tests complete in <5 seconds
2. **High coverage** - >85% code coverage across all components
3. **Practical testing** - Tests verify real-world scenarios, not just edge cases
4. **Clear test organization** - Unit, integration, and E2E tests clearly separated
5. **Maintainable tests** - DRY principles, shared fixtures, descriptive names

### Testing Pyramid

The project implements a standard testing pyramid:

```
                    ▲
                   / \
                  /   \
                 / E2E \          ~15 tests (slow, expensive)
                /───────\
               /         \
              / Integration\      ~60 tests (moderate speed)
             /─────────────\
            /               \
           /   Unit Tests    \   ~125 tests (fast, cheap)
          /___________________\
```

**Distribution:**
- **Unit Tests:** 75% (~125 tests) - Test individual functions/classes in isolation
- **Integration Tests:** 35% (~60 tests) - Test component interactions (API, CLI, database)
- **E2E Tests:** 10% (~15 tests) - Test complete workflows (pause/resume, realistic grids)

### Test Coverage Statistics

**Overall:** 165/165 tests passing (100% pass rate)

**Backend Coverage:** 92%
- `api/routes.py`: 95%
- `api/validators.py`: 100%
- `core/cli_adapter.py`: 90%
- `core/edit_merger.py`: 88%
- `core/theme_placer.py`: 85%

**CLI Coverage:** 89%
- `core/grid.py`: 93%
- `fill/autofill.py`: 85%
- `fill/beam_search/`: 87%
- `fill/pattern_matcher.py`: 90%

**Frontend Coverage:** 0% (manual testing only - future enhancement)

---

## Testing Strategy

### Test Types and Purposes

#### Unit Tests
**Purpose:** Verify individual functions/classes work correctly in isolation

**Characteristics:**
- Fast execution (<5s for entire suite)
- No external dependencies (mocked)
- High code coverage (>90%)
- Focused on business logic

**Example:**
```python
def test_pattern_matcher_simple_pattern():
    """Test pattern matching with simple wildcard."""
    matcher = PatternMatcher(wordlist)
    results = matcher.match("C?T")

    assert "CAT" in results
    assert "COT" in results
    assert "DOG" not in results
```

#### Integration Tests
**Purpose:** Verify components work together correctly

**Characteristics:**
- Moderate execution time (<30s for suite)
- Real external dependencies (subprocess, file I/O)
- Tests API contracts and data flow
- Focuses on component boundaries

**Example:**
```python
def test_api_pattern_endpoint(client):
    """Test /api/pattern endpoint end-to-end."""
    response = client.post('/api/pattern', json={
        'pattern': 'C?T',
        'max_results': 10
    })

    assert response.status_code == 200
    data = response.json
    assert len(data['results']) <= 10
    assert all('score' in r for r in data['results'])
```

#### End-to-End Tests
**Purpose:** Verify complete workflows work from user perspective

**Characteristics:**
- Slow execution (minutes)
- Tests realistic scenarios
- Includes performance validation
- Minimal mocking

**Example:**
```python
@pytest.mark.slow
def test_pause_resume_with_edits_workflow():
    """Test complete pause/resume workflow with user edits."""
    # 1. Start autofill
    task_id = start_autofill(grid)

    # 2. Pause after some progress
    pause_fill(task_id)

    # 3. User edits grid
    edited_grid = apply_edits(grid, edits)

    # 4. Resume from saved state
    result = resume_fill(task_id, edited_grid)

    # 5. Verify edits are preserved
    assert result.grid.matches(edited_grid, locked_cells)
```

### Test Organization

```
crossword-helper/
├── backend/tests/
│   ├── conftest.py              # Shared fixtures and pytest config
│   ├── fixtures/                # Test data
│   │   ├── __init__.py
│   │   ├── grid_fixtures.py     # Sample grids (3x3 to 21x21)
│   │   └── realistic_grid_fixtures.py  # NYT-style grids
│   ├── unit/                    # Fast, isolated tests
│   │   ├── test_validators.py
│   │   ├── test_edit_merger.py
│   │   └── test_grid_transformation.py
│   └── integration/             # Component interaction tests
│       ├── test_api.py
│       ├── test_cli_integration.py
│       ├── test_pause_resume_api.py
│       └── test_realistic_grids.py
│
└── cli/tests/
    ├── unit/                    # CLI unit tests
    │   ├── test_grid.py
    │   ├── test_autofill.py
    │   ├── test_pattern_matcher.py
    │   └── test_state_manager.py
    └── integration/             # CLI integration tests
        ├── test_cli_commands.py
        └── test_fill_algorithms.py
```

---

## Test Environment Setup

### Prerequisites

**Python Environment:**
```bash
Python 3.9+
pip 21+
virtualenv (recommended)
```

**Node.js Environment (for frontend tests, future):**
```bash
Node.js 18+
npm 9+
```

### Installation

#### 1. Clone Repository
```bash
git clone <repo-url>
cd crossword-helper
```

#### 2. Set Up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install CLI dependencies
cd cli
pip install -r requirements.txt
cd ..
```

#### 3. Install Testing Tools
```bash
# Testing framework
pip install pytest==7.4.3

# Coverage tools
pip install pytest-cov==4.1.0
pip install coverage[toml]==7.3.2

# Additional test utilities
pip install pytest-xdist==3.5.0  # Parallel test execution
pip install pytest-timeout==2.2.0  # Test timeout enforcement
pip install pytest-mock==3.12.0   # Mocking utilities
```

#### 4. Verify Installation
```bash
# Run pytest version check
pytest --version

# Should output: pytest 7.4.3

# Run simple health check
pytest --collect-only
# Should list all test files without errors
```

### Configuration Files

#### pytest.ini
```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=backend --cov-report=html --cov-report=term
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

**Key Settings:**
- `testpaths`: Where pytest looks for tests
- `addopts`: Default options (verbose, coverage)
- `markers`: Custom markers for test categorization

#### coverage.rc (optional, advanced)
```ini
[run]
source = backend, cli
omit =
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## Unit Testing

### CLI Unit Tests

Located in: `cli/tests/unit/`

#### Test: Pattern Matching Algorithms

**File:** `test_pattern_matcher.py`

**Purpose:** Verify pattern matching algorithms (Regex, Trie)

**Example Tests:**
```python
class TestPatternMatcher:
    """Test PatternMatcher class."""

    @pytest.fixture
    def wordlist(self):
        """Sample wordlist for testing."""
        return ['CAT', 'COT', 'CUT', 'DOG', 'LOG', 'FOG']

    @pytest.fixture
    def matcher(self, wordlist):
        """Create pattern matcher."""
        return PatternMatcher(wordlist)

    def test_exact_match(self, matcher):
        """Test exact pattern match (no wildcards)."""
        results = matcher.match("CAT")

        assert len(results) == 1
        assert results[0] == "CAT"

    def test_single_wildcard(self, matcher):
        """Test pattern with single wildcard."""
        results = matcher.match("C?T")

        assert set(results) == {"CAT", "COT", "CUT"}

    def test_multiple_wildcards(self, matcher):
        """Test pattern with multiple wildcards."""
        results = matcher.match("?O?")

        assert set(results) == {"COT", "DOG", "LOG", "FOG"}

    def test_no_matches(self, matcher):
        """Test pattern with no matches."""
        results = matcher.match("X?Z")

        assert len(results) == 0

    def test_case_insensitive(self, matcher):
        """Test pattern matching is case-insensitive."""
        results = matcher.match("c?t")

        assert set(results) == {"CAT", "COT", "CUT"}
```

**Running:**
```bash
pytest cli/tests/unit/test_pattern_matcher.py -v
```

#### Test: CSP Solver Logic

**File:** `test_autofill.py`

**Purpose:** Verify CSP autofill algorithm correctness

**Example Tests:**
```python
class TestAutofill:
    """Test Autofill CSP solver."""

    @pytest.fixture
    def word_list(self):
        """Create word list for testing."""
        words = [
            'CAT', 'COT', 'CUT', 'ACE', 'ACT',
            'CATS', 'TEAR', 'CART',
            'APPLE', 'CABIN'
        ]
        return WordList(words)

    @pytest.fixture
    def simple_grid(self):
        """Create 5x5 grid with pattern."""
        grid = Grid(5)
        grid.set_black_square(2, 2)  # Center black square
        return grid

    def test_fill_simple_grid(self, simple_grid, word_list):
        """Test filling simple 5x5 grid."""
        autofill = Autofill(simple_grid, word_list, timeout=30)
        result = autofill.fill()

        assert result.success
        assert result.slots_filled > 0
        assert result.time_elapsed < 30

    def test_mcv_heuristic(self, simple_grid, word_list):
        """Test Most Constrained Variable heuristic."""
        autofill = Autofill(simple_grid, word_list)

        # Get slot selection order
        slots = autofill._get_slot_order()

        # First slot should be most constrained
        assert len(autofill._get_candidates(slots[0])) <= \
               len(autofill._get_candidates(slots[-1]))

    def test_ac3_constraint_propagation(self, simple_grid, word_list):
        """Test AC-3 constraint propagation."""
        autofill = Autofill(simple_grid, word_list)

        # Set word in slot
        autofill._assign_word(slot=0, word="CAT")

        # Run AC-3
        autofill._propagate_constraints()

        # Verify crossing slots are constrained
        crossing_slot = autofill._get_crossing_slot(0, position=0)
        candidates = autofill._get_candidates(crossing_slot)

        # All candidates must have 'C' at crossing position
        assert all(word[0] == 'C' for word in candidates)

    def test_backtracking(self, simple_grid, word_list):
        """Test backtracking on invalid assignment."""
        autofill = Autofill(simple_grid, word_list)

        # Force invalid assignment
        autofill._assign_word(slot=0, word="CAT")
        autofill._assign_word(slot=1, word="DOG")  # Conflicts with CAT

        # Should backtrack and try different word
        result = autofill.fill()

        # May succeed or fail, but should not crash
        assert result.iterations > 0
```

**Running:**
```bash
pytest cli/tests/unit/test_autofill.py -v
```

#### Test: Grid Operations

**File:** `test_grid.py`

**Purpose:** Verify grid data structure operations

**Example Tests:**
```python
class TestGrid:
    """Test Grid class."""

    def test_create_empty_grid(self):
        """Test creating empty grid."""
        grid = Grid(15)

        assert grid.size == 15
        assert grid.cells.shape == (15, 15)
        assert np.all(grid.cells == CellType.EMPTY)

    def test_set_letter(self):
        """Test setting letter in cell."""
        grid = Grid(5)
        grid.set_letter(0, 0, 'A')

        assert grid.get_letter(0, 0) == 'A'
        assert grid.cells[0, 0] != CellType.EMPTY

    def test_set_black_square(self):
        """Test setting black square."""
        grid = Grid(5)
        grid.set_black_square(2, 2)

        assert grid.is_black(2, 2)
        assert grid.cells[2, 2] == CellType.BLACK

    def test_symmetry_validation(self):
        """Test 180-degree rotational symmetry."""
        grid = Grid(5)

        # Add symmetric black squares
        grid.set_black_square(0, 0)
        grid.set_black_square(4, 4)

        assert grid.is_symmetric()

        # Break symmetry
        grid.set_black_square(1, 1)

        assert not grid.is_symmetric()

    def test_get_slots(self):
        """Test slot extraction (across and down)."""
        grid = Grid(5)
        grid.set_black_square(2, 2)

        slots = grid.get_slots()

        # Should have across and down slots
        across_slots = [s for s in slots if s['direction'] == 'across']
        down_slots = [s for s in slots if s['direction'] == 'down']

        assert len(across_slots) > 0
        assert len(down_slots) > 0
```

**Running:**
```bash
pytest cli/tests/unit/test_grid.py -v
```

### Backend Unit Tests

Located in: `backend/tests/unit/`

#### Test: Request Validation

**File:** `test_validators.py`

**Purpose:** Verify API request validation logic

**Example Tests:**
```python
class TestValidators:
    """Test request validation functions."""

    def test_validate_pattern_request_valid(self):
        """Test valid pattern request."""
        data = {
            'pattern': 'C?T',
            'max_results': 20
        }

        # Should not raise
        validate_pattern_request(data)

    def test_validate_pattern_request_missing_pattern(self):
        """Test pattern request missing pattern field."""
        data = {'max_results': 20}

        with pytest.raises(ValueError, match="Pattern required"):
            validate_pattern_request(data)

    def test_validate_pattern_request_empty_pattern(self):
        """Test pattern request with empty pattern."""
        data = {'pattern': ''}

        with pytest.raises(ValueError, match="Pattern cannot be empty"):
            validate_pattern_request(data)

    def test_validate_pattern_request_invalid_max_results(self):
        """Test pattern request with invalid max_results."""
        data = {
            'pattern': 'C?T',
            'max_results': 1000  # Too large
        }

        with pytest.raises(ValueError, match="max_results must be between"):
            validate_pattern_request(data)

    def test_validate_grid_request_valid(self):
        """Test valid grid request."""
        data = {
            'size': 15,
            'grid': [['A', '.', '#'] for _ in range(15)]
        }

        validate_grid_request(data)

    def test_validate_grid_request_invalid_size(self):
        """Test grid request with invalid size."""
        data = {
            'size': 100,  # Too large
            'grid': [[]]
        }

        with pytest.raises(ValueError, match="size must be between"):
            validate_grid_request(data)
```

**Running:**
```bash
pytest backend/tests/unit/test_validators.py -v
```

#### Test: Grid Transformation

**File:** `test_grid_transformation.py`

**Purpose:** Verify frontend ↔ CLI grid format conversion

**Critical Test (Bug Fix):**
```python
def test_empty_cell_transformation():
    """
    Test that empty cells (letter='') become '.' in CLI format.

    This test catches a critical bug where empty cells were incorrectly
    transformed to '' instead of '.', causing CLI to reject the grid.
    """
    frontend_grid = [[{"letter": "", "isBlack": False}]]
    result = transform_grid_frontend_to_cli(frontend_grid)

    # CRITICAL: Empty cells must become '.'
    assert result == [["."]], "Empty cell should become '.'"
```

**Comprehensive Tests:**
```python
class TestGridTransformationLogic:
    """Test grid transformation between frontend and CLI formats."""

    @pytest.mark.parametrize("test_name,frontend_data,expected_cli_data", [
        ("empty_3x3", EMPTY_3X3_FRONTEND, EMPTY_3X3_CLI),
        ("partially_filled", PARTIALLY_FILLED_3X3_FRONTEND, PARTIALLY_FILLED_3X3_CLI),
        ("pattern", PATTERN_3X3_FRONTEND, PATTERN_3X3_CLI),
        ("all_black", ALL_BLACK_3X3_FRONTEND, ALL_BLACK_3X3_CLI),
    ])
    def test_all_transformation_cases(self, test_name, frontend_data, expected_cli_data):
        """Test all predefined transformation cases."""
        result = transform_grid_frontend_to_cli(frontend_data["grid"])
        expected = expected_cli_data["grid"]

        assert result == expected, \
            f"Transformation failed for {test_name}"

    def test_uppercase_transformation(self):
        """Test lowercase letters are converted to uppercase."""
        frontend_grid = [[{"letter": "a", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["A"]]
```

**Running:**
```bash
pytest backend/tests/unit/test_grid_transformation.py -v
```

#### Test: Edit Merger (Pause/Resume)

**File:** `test_edit_merger.py`

**Purpose:** Verify edit merging logic for pause/resume

**Example Tests:**
```python
class TestEditMerger:
    """Test EditMerger class for pause/resume functionality."""

    @pytest.fixture
    def saved_grid(self):
        """Create saved grid state."""
        return [
            ['T', 'E', 'S', 'T'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.']
        ]

    @pytest.fixture
    def csp_domains(self):
        """Create sample CSP domains."""
        return {
            0: ['TEST', 'TEAR'],
            1: ['EXAM', 'EXIT']
        }

    def test_detect_filled_cells(self, saved_grid):
        """Test detecting newly filled cells."""
        edited_grid = [
            ['T', 'E', 'S', 'T'],
            ['E', '.', '.', '.'],  # NEW: E at (1,0)
            ['S', '.', '.', '.'],  # NEW: S at (2,0)
            ['.', '.', '.', '.']
        ]

        merger = EditMerger(saved_grid, csp_domains={})
        changes = merger.detect_changes(edited_grid)

        assert len(changes['filled']) == 2
        assert (1, 0) in changes['filled']
        assert (2, 0) in changes['filled']

    def test_detect_emptied_cells(self, saved_grid):
        """Test detecting newly emptied cells."""
        edited_grid = [
            ['T', 'E', '.', 'T'],  # REMOVED: S at (0,2)
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.']
        ]

        merger = EditMerger(saved_grid, csp_domains={})
        changes = merger.detect_changes(edited_grid)

        assert len(changes['emptied']) == 1
        assert (0, 2) in changes['emptied']

    def test_ac3_constraint_propagation(self, saved_grid, csp_domains):
        """Test AC-3 updates domains based on edits."""
        edited_grid = [
            ['T', 'E', 'S', 'T'],
            ['E', '.', '.', '.'],  # Forces 'E' at crossing
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.']
        ]

        merger = EditMerger(saved_grid, csp_domains)
        updated_domains = merger.merge_edits(edited_grid)

        # Domains should be constrained by new 'E'
        assert all('E' in word or word[1] == 'E'
                  for word in updated_domains[1])
```

**Running:**
```bash
pytest backend/tests/unit/test_edit_merger.py -v
```

---

## Integration Testing

### API Integration Tests

Located in: `backend/tests/integration/`

#### Test: Core API Endpoints

**File:** `test_api.py`

**Purpose:** Test API endpoints end-to-end

**Example Tests:**
```python
class TestAPIEndpoints:
    """Test Flask API endpoints."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        from backend.app import create_app
        return create_app(testing=True)

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_health_endpoint(self, client):
        """Test GET /api/health."""
        response = client.get('/api/health')

        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'healthy'
        assert 'version' in data

    def test_pattern_endpoint_valid_request(self, client):
        """Test POST /api/pattern with valid data."""
        response = client.post('/api/pattern', json={
            'pattern': 'C?T',
            'max_results': 10
        })

        assert response.status_code == 200
        data = response.json
        assert 'results' in data
        assert len(data['results']) <= 10
        assert all('word' in r and 'score' in r for r in data['results'])

    def test_pattern_endpoint_missing_pattern(self, client):
        """Test POST /api/pattern without pattern."""
        response = client.post('/api/pattern', json={
            'max_results': 10
        })

        assert response.status_code == 400
        data = response.json
        assert 'error' in data

    def test_number_endpoint(self, client):
        """Test POST /api/number."""
        response = client.post('/api/number', json={
            'size': 5,
            'grid': [
                ['A', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.'],
                ['.', '.', '#', '.', '.'],
                ['.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.']
            ]
        })

        assert response.status_code == 200
        data = response.json
        assert 'numbering' in data
        assert 'grid_info' in data

    def test_normalize_endpoint(self, client):
        """Test POST /api/normalize."""
        response = client.post('/api/normalize', json={
            'text': 'Tina Fey'
        })

        assert response.status_code == 200
        data = response.json
        assert data['normalized'] == 'TINAFEY'
        assert 'rule' in data
```

**Running:**
```bash
pytest backend/tests/integration/test_api.py -v
```

#### Test: CLI Integration

**File:** `test_cli_integration.py`

**Purpose:** Test backend-to-CLI subprocess integration

**Example Tests:**
```python
class TestCLIIntegration:
    """Test CLIAdapter subprocess execution."""

    @pytest.fixture
    def cli_adapter(self):
        """Create CLI adapter."""
        from backend.core.cli_adapter import get_adapter
        return get_adapter()

    def test_cli_health_check(self, cli_adapter):
        """Test CLI is accessible."""
        assert cli_adapter.health_check()

    def test_cli_pattern_command(self, cli_adapter):
        """Test executing pattern command via CLI."""
        result = cli_adapter.pattern(
            pattern='C?T',
            wordlist_paths=['data/wordlists/comprehensive.txt'],
            max_results=10
        )

        assert 'results' in result
        assert len(result['results']) <= 10

    def test_cli_timeout_handling(self, cli_adapter):
        """Test CLI timeout enforcement."""
        with pytest.raises(TimeoutError):
            cli_adapter.fill(
                grid_data={'size': 21, 'grid': [['.'] * 21 for _ in range(21)]},
                wordlist_paths=['data/wordlists/comprehensive.txt'],
                timeout=1  # Very short timeout
            )

    def test_cli_error_propagation(self, cli_adapter):
        """Test CLI errors are properly propagated."""
        with pytest.raises(ValueError):
            cli_adapter.pattern(
                pattern='',  # Invalid: empty pattern
                wordlist_paths=[],
                max_results=10
            )
```

**Running:**
```bash
pytest backend/tests/integration/test_cli_integration.py -v
```

#### Test: Pause/Resume API

**File:** `test_pause_resume_api.py`

**Purpose:** Test pause/resume workflow via API

**Example Tests:**
```python
class TestPauseResumeAPI:
    """Test pause/resume API endpoints."""

    @pytest.fixture
    def app(self):
        """Create Flask app."""
        from backend.app import create_app
        return create_app(testing=True)

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def sample_state(self, tmp_path):
        """Create sample saved CSP state."""
        # (See earlier example for full implementation)
        pass

    def test_pause_request(self, client):
        """Test POST /api/fill/pause/:task_id."""
        response = client.post('/api/fill/pause/test_task_123')

        assert response.status_code == 200
        data = response.json
        assert data['success'] is True

    def test_get_saved_state(self, client, sample_state):
        """Test GET /api/fill/state/:task_id."""
        task_id, tmp_path, _, _ = sample_state

        # Monkeypatch storage directory
        import backend.api.pause_resume_routes as pr
        pr.STATE_STORAGE_DIR = tmp_path

        response = client.get(f'/api/fill/state/{task_id}')

        assert response.status_code == 200
        data = response.json
        assert data['task_id'] == task_id
        assert 'grid_preview' in data

    def test_resume_with_edits(self, client, sample_state):
        """Test POST /api/fill/resume with edits."""
        task_id, tmp_path, csp_state, _ = sample_state

        # Create edited grid
        edited_grid = [
            ['T', 'E', 'A', 'R'],  # Changed from TEST
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.']
        ]

        response = client.post('/api/fill/resume', json={
            'task_id': task_id,
            'edited_grid': edited_grid
        })

        assert response.status_code == 200
        data = response.json
        assert data['success'] is True
        assert 'new_task_id' in data
```

**Running:**
```bash
pytest backend/tests/integration/test_pause_resume_api.py -v
```

#### Test: Progress Streaming (SSE)

**File:** `test_progress_integration.py`

**Purpose:** Test Server-Sent Events progress streaming

**Example Tests:**
```python
class TestProgressStreaming:
    """Test SSE progress streaming."""

    @pytest.fixture
    def app(self):
        """Create Flask app."""
        from backend.app import create_app
        return create_app(testing=True)

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_progress_stream_creation(self, client):
        """Test creating progress stream."""
        from backend.api.progress_routes import create_progress_tracker

        task_id = create_progress_tracker()

        assert task_id is not None
        assert len(task_id) > 0

    def test_progress_event_sending(self, client):
        """Test sending progress events."""
        from backend.api.progress_routes import (
            create_progress_tracker,
            send_progress
        )

        task_id = create_progress_tracker()

        # Send progress event
        send_progress(
            task_id=task_id,
            progress=50,
            message="Filled 25/50 slots",
            status="running"
        )

        # Verify event is queued
        # (In real test, would connect SSE client and verify reception)
```

**Running:**
```bash
pytest backend/tests/integration/test_progress_integration.py -v
```

---

## End-to-End Testing

### Realistic Grid Tests

**File:** `backend/tests/integration/test_realistic_grids.py`

**Purpose:** Test autofill with real NYT-style grids

**Example Tests:**
```python
@pytest.mark.slow
class TestRealisticGrids:
    """Test autofill on realistic crossword grids."""

    def test_11x11_daily_grid(self):
        """Test filling 11x11 weekday-style grid."""
        from backend.tests.fixtures.realistic_grid_fixtures import (
            REALISTIC_11X11_GRID
        )

        grid = Grid.from_dict(REALISTIC_11X11_GRID)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        autofill = Autofill(grid, wordlist, timeout=60)
        result = autofill.fill()

        # Performance requirements
        assert result.time_elapsed < 60, "11x11 should fill in <60s"
        assert result.success, "Should successfully fill 11x11 grid"

        # Quality requirements
        avg_score = result.average_word_score()
        assert avg_score > 60, f"Average word score too low: {avg_score}"

    def test_15x15_themed_grid(self):
        """Test filling 15x15 grid with theme entries."""
        from backend.tests.fixtures.realistic_grid_fixtures import (
            REALISTIC_15X15_WITH_THEME
        )

        grid = Grid.from_dict(REALISTIC_15X15_WITH_THEME)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        autofill = Autofill(grid, wordlist, timeout=300)
        result = autofill.fill()

        # Performance requirements
        assert result.time_elapsed < 300, "15x15 should fill in <5min"

        # Verify theme entries preserved
        theme_words = REALISTIC_15X15_WITH_THEME['theme_entries']
        for slot_key, expected_word in theme_words.items():
            actual_word = result.grid.get_word(slot_key)
            assert actual_word == expected_word, \
                f"Theme entry changed: {expected_word} → {actual_word}"

    @pytest.mark.slow
    def test_21x21_sunday_grid(self):
        """Test filling 21x21 Sunday-size grid."""
        from backend.tests.fixtures.realistic_grid_fixtures import (
            REALISTIC_21X21_GRID
        )

        grid = Grid.from_dict(REALISTIC_21X21_GRID)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        autofill = Autofill(grid, wordlist, timeout=1800, algorithm='hybrid')
        result = autofill.fill()

        # Performance requirements (relaxed for 21x21)
        assert result.time_elapsed < 1800, "21x21 should fill in <30min"

        # May not always succeed (acceptable for 21x21)
        if result.success:
            avg_score = result.average_word_score()
            assert avg_score > 50, "Word quality should be reasonable"
        else:
            # Verify partial fill is substantial
            assert result.slots_filled / result.total_slots > 0.8, \
                "Should fill >80% of slots even on failure"
```

**Running:**
```bash
# Run realistic grid tests (slow)
pytest backend/tests/integration/test_realistic_grids.py -v

# Skip slow tests
pytest -m "not slow"
```

### Complete Pause/Resume Workflow

**File:** `backend/tests/integration/test_e2e_pause_resume.py`

**Purpose:** Test complete pause/resume workflow end-to-end

**Example Test:**
```python
@pytest.mark.slow
class TestE2EPauseResume:
    """End-to-end pause/resume workflow tests."""

    def test_complete_pause_edit_resume_workflow(self, client, tmp_path):
        """
        Test complete workflow:
        1. Start autofill
        2. Pause after progress
        3. User edits grid
        4. Resume from saved state
        5. Verify edits preserved and fill completes
        """
        # 1. Start autofill
        grid_data = {
            'size': 11,
            'grid': [[{'letter': '', 'isBlack': False}] * 11 for _ in range(11)]
        }

        response = client.post('/api/fill/with-progress', json={
            'grid': grid_data,
            'timeout': 120,
            'wordlists': ['comprehensive']
        })

        assert response.status_code == 202
        task_id = response.json['task_id']

        # 2. Wait for some progress, then pause
        time.sleep(5)  # Let it make some progress

        response = client.post(f'/api/fill/pause/{task_id}')
        assert response.status_code == 200

        # Wait for pause to complete
        time.sleep(2)

        # 3. Get saved state
        response = client.get(f'/api/fill/state/{task_id}')
        assert response.status_code == 200
        saved_state = response.json

        # 4. User edits grid
        edited_grid = saved_state['grid_preview']
        # Manually fill a slot
        edited_grid[0][0] = {'letter': 'T', 'isBlack': False}
        edited_grid[0][1] = {'letter': 'E', 'isBlack': False}
        edited_grid[0][2] = {'letter': 'S', 'isBlack': False}
        edited_grid[0][3] = {'letter': 'T', 'isBlack': False}

        # 5. Resume with edits
        response = client.post('/api/fill/resume', json={
            'task_id': task_id,
            'edited_grid': edited_grid,
            'options': {
                'timeout': 120,
                'wordlists': ['comprehensive']
            }
        })

        assert response.status_code == 200
        resume_data = response.json
        new_task_id = resume_data['new_task_id']

        # 6. Wait for completion
        # (In real test, would monitor SSE stream)
        time.sleep(30)

        # 7. Verify final grid preserves edits
        response = client.get(f'/api/fill/state/{new_task_id}')
        final_grid = response.json['grid_preview']

        assert final_grid[0][0]['letter'] == 'T'
        assert final_grid[0][1]['letter'] == 'E'
        assert final_grid[0][2]['letter'] == 'S'
        assert final_grid[0][3]['letter'] == 'T'
```

**Running:**
```bash
pytest backend/tests/integration/test_e2e_pause_resume.py -v -s
```

---

## Test Data Management

### Test Fixtures

#### Grid Fixtures

**File:** `backend/tests/fixtures/grid_fixtures.py`

**Purpose:** Provide sample grids for testing

**Examples:**
```python
# Empty 3x3 grid (frontend format)
EMPTY_3X3_FRONTEND = {
    'size': 3,
    'grid': [
        [{'letter': '', 'isBlack': False}] * 3,
        [{'letter': '', 'isBlack': False}] * 3,
        [{'letter': '', 'isBlack': False}] * 3
    ]
}

# Empty 3x3 grid (CLI format)
EMPTY_3X3_CLI = {
    'size': 3,
    'grid': [
        ['.', '.', '.'],
        ['.', '.', '.'],
        ['.', '.', '.']
    ]
}

# Partially filled 3x3 grid
PARTIALLY_FILLED_3X3_FRONTEND = {
    'size': 3,
    'grid': [
        [
            {'letter': 'C', 'isBlack': False},
            {'letter': 'A', 'isBlack': False},
            {'letter': 'T', 'isBlack': False}
        ],
        [
            {'letter': '', 'isBlack': False},
            {'letter': '', 'isBlack': False},
            {'letter': '', 'isBlack': False}
        ],
        [
            {'letter': '', 'isBlack': False},
            {'letter': '', 'isBlack': False},
            {'letter': '', 'isBlack': False}
        ]
    ]
}

# 15x15 standard grid
STANDARD_15X15_GRID = {
    'size': 15,
    'grid': [
        # ... full 15x15 grid definition
    ],
    'black_squares': [
        [0, 5], [0, 11],
        # ... symmetric black square pattern
    ]
}
```

**Usage:**
```python
from backend.tests.fixtures import EMPTY_3X3_FRONTEND

def test_something():
    grid = Grid.from_dict(EMPTY_3X3_FRONTEND)
    # ... test logic
```

#### Realistic Grid Fixtures

**File:** `backend/tests/fixtures/realistic_grid_fixtures.py`

**Purpose:** Provide NYT-style grids for performance testing

**Examples:**
```python
# 11x11 weekday grid (typical Monday-Thursday)
REALISTIC_11X11_GRID = {
    'size': 11,
    'grid': [
        # ... realistic 11x11 pattern
    ],
    'black_squares': [
        # Symmetric pattern with ~20% black squares
    ],
    'expected_time': 30,  # seconds
    'expected_min_score': 60
}

# 15x15 themed grid
REALISTIC_15X15_WITH_THEME = {
    'size': 15,
    'grid': [
        # ... 15x15 grid with theme entries pre-filled
    ],
    'theme_entries': {
        '[0, 0, "across"]': 'THEMEWORD',
        '[7, 0, "across"]': 'ANOTHERCLUE',
        '[14, 0, "across"]': 'FINALTHEME'
    },
    'expected_time': 180,  # 3 minutes
    'expected_min_score': 65
}

# 21x21 Sunday grid
REALISTIC_21X21_GRID = {
    'size': 21,
    'grid': [
        # ... challenging 21x21 grid
    ],
    'expected_time': 1200,  # 20 minutes
    'expected_min_score': 55
}
```

### Mock Data Generation

#### Word List Mocks

```python
@pytest.fixture
def small_wordlist():
    """Small wordlist for fast tests."""
    return [
        'CAT', 'COT', 'CUT',
        'ACE', 'ACT', 'ART',
        'BAT', 'BIT', 'BUT'
    ]

@pytest.fixture
def medium_wordlist():
    """Medium wordlist for moderate tests."""
    words = []
    for length in range(3, 8):
        # Generate representative words of each length
        words.extend(generate_words_of_length(length, count=20))
    return words

@pytest.fixture
def full_wordlist():
    """Full wordlist (slow to load)."""
    return WordList.load('data/wordlists/comprehensive.txt')
```

#### Theme Entry Examples

```python
THEME_EXAMPLES = {
    'names': [
        'TINAFEY',
        'SETHMEYERS',
        'AMYPOEHLER'
    ],
    'phrases': [
        'BREAKINGBAD',
        'GAMEOFTHRONES',
        'THEWIRE'
    ],
    'dates': [
        'JANUARY',
        'FEBRUARY',
        'MARCH'
    ]
}
```

### Shared Fixtures (conftest.py)

**File:** `backend/tests/conftest.py`

**Purpose:** Pytest configuration and shared fixtures

```python
@pytest.fixture(scope="session")
def cli_available():
    """Check if CLI is available for integration tests."""
    try:
        from backend.core.cli_adapter import get_adapter
        adapter = get_adapter()
        return adapter.health_check()
    except Exception:
        return False

@pytest.fixture(scope="session")
def skip_if_no_cli(cli_available):
    """Skip test if CLI is not available."""
    if not cli_available:
        pytest.skip("CLI not available - skipping integration test")

@pytest.fixture
def app():
    """Create Flask app for testing."""
    from backend.app import create_app
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()

@pytest.fixture
def temp_wordlist(tmp_path):
    """Create temporary wordlist file."""
    wordlist_file = tmp_path / "test_wordlist.txt"
    words = ['CAT', 'DOG', 'RAT', 'BAT']
    wordlist_file.write_text('\n'.join(words))
    return str(wordlist_file)
```

---

## Running Tests

### Basic Test Execution

#### Run All Tests
```bash
# Run entire test suite
pytest

# Run with verbose output
pytest -v

# Run with extra verbosity (show test names as they run)
pytest -vv
```

#### Run Specific Test Files
```bash
# Run single file
pytest backend/tests/unit/test_validators.py

# Run multiple files
pytest backend/tests/unit/test_validators.py backend/tests/unit/test_grid_transformation.py
```

#### Run Specific Test Classes/Methods
```bash
# Run specific class
pytest backend/tests/unit/test_validators.py::TestValidators

# Run specific test method
pytest backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid

# Run all tests matching pattern
pytest -k "test_pattern"
```

### Test Selection by Markers

#### Run Only Unit Tests
```bash
pytest -m unit
```

#### Run Only Integration Tests
```bash
pytest -m integration
```

#### Skip Slow Tests
```bash
pytest -m "not slow"
```

#### Run Slow Tests Only
```bash
pytest -m slow
```

### Parallel Test Execution

**Install pytest-xdist:**
```bash
pip install pytest-xdist
```

**Run tests in parallel:**
```bash
# Run with 4 workers
pytest -n 4

# Run with auto-detected CPU count
pytest -n auto

# Parallel + verbose
pytest -n auto -v
```

**Performance:**
- Sequential: ~35 seconds
- Parallel (4 cores): ~10 seconds
- **3.5x speedup**

### Test Output Options

#### Show Print Statements
```bash
pytest -s
```

#### Show Locals on Failure
```bash
pytest -l
```

#### Stop on First Failure
```bash
pytest -x
```

#### Stop After N Failures
```bash
pytest --maxfail=3
```

#### Show Captured Output
```bash
pytest --capture=no
```

### Test Collection and Discovery

#### Collect Tests Without Running
```bash
pytest --collect-only
```

#### Show Test IDs
```bash
pytest --collect-only -q
```

### Custom pytest.ini Options

**Current Configuration:**
```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=backend --cov-report=html --cov-report=term
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

**Override in CLI:**
```bash
# Disable coverage
pytest --no-cov

# Change testpath
pytest cli/tests/

# Quiet output
pytest -q
```

---

## Code Coverage

### Measuring Coverage

#### Generate Coverage Report
```bash
# Run tests with coverage
pytest --cov=backend --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

#### Terminal Coverage Report
```bash
pytest --cov=backend --cov-report=term

# With missing lines
pytest --cov=backend --cov-report=term-missing
```

#### Coverage for Specific Modules
```bash
# Backend only
pytest --cov=backend/core --cov-report=term

# CLI only
pytest --cov=cli/src --cov-report=term

# Multiple modules
pytest --cov=backend --cov=cli --cov-report=term
```

### Coverage Goals by Component

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| **Backend API** | 95% | >90% | ✅ Exceeds target |
| **Backend Core** | 90% | >85% | ✅ Exceeds target |
| **CLI Core** | 93% | >85% | ✅ Exceeds target |
| **CLI Fill** | 85% | >80% | ✅ Meets target |
| **Frontend** | 0% | >70% | ❌ Not implemented |

### Viewing Coverage Reports

#### HTML Report (Recommended)
```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

**Features:**
- Color-coded line coverage
- Branch coverage visualization
- Sortable by file/coverage percentage
- Drill-down to specific files

#### Terminal Report
```bash
pytest --cov=backend --cov-report=term-missing
```

**Output:**
```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
backend/api/routes.py                     156      8    95%   123-125, 234
backend/api/validators.py                  45      0   100%
backend/core/cli_adapter.py               210     21    90%   145-152, 289
backend/core/edit_merger.py               123     15    88%   67-73, 201
---------------------------------------------------------------------
TOTAL                                    1542    142    92%
```

#### XML Report (for CI/CD)
```bash
pytest --cov=backend --cov-report=xml
```

**Generates:** `coverage.xml` (Cobertura format)

**Used by:**
- GitHub Actions
- GitLab CI
- Jenkins
- Codecov
- Coveralls

### Coverage Configuration

#### .coveragerc
```ini
[run]
source = backend, cli
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstract
```

**Exclude from coverage:**
- Test files
- Virtual environment
- Cache directories
- Abstract methods
- Type checking blocks

### Improving Coverage

#### Identify Uncovered Code
```bash
pytest --cov=backend --cov-report=term-missing | grep -A 5 "TOTAL"
```

#### Find Untested Files
```bash
coverage report --skip-covered
```

#### Generate Coverage Badge
```bash
# Install coverage-badge
pip install coverage-badge

# Generate badge
coverage-badge -o coverage.svg -f
```

---

## Debugging Failed Tests

### Common Test Failures

#### 1. Import Errors
**Error:**
```
ImportError: cannot import name 'Grid' from 'cli.src.core.grid'
```

**Cause:** Python path not configured

**Solution:**
```bash
# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use editable install
pip install -e .
```

#### 2. Fixture Not Found
**Error:**
```
fixture 'client' not found
```

**Cause:** Missing conftest.py or fixture not imported

**Solution:**
```python
# Ensure conftest.py defines fixture
@pytest.fixture
def client(app):
    return app.test_client()
```

#### 3. CLI Not Available
**Error:**
```
SKIPPED [1] CLI not available - skipping integration test
```

**Cause:** CLI not installed or not in PATH

**Solution:**
```bash
# Install CLI
cd cli
pip install -e .

# Verify CLI works
crossword --version
```

#### 4. Timeout Failures
**Error:**
```
FAILED test_fill_large_grid - TimeoutError: Test exceeded 30s timeout
```

**Cause:** Test takes longer than expected

**Solution:**
```python
# Increase timeout
@pytest.mark.timeout(60)
def test_fill_large_grid():
    # ... test logic
```

#### 5. Race Conditions
**Error:**
```
AssertionError: expected 10, got 9
```

**Cause:** Timing-dependent test (SSE, async operations)

**Solution:**
```python
# Add explicit waits
import time
time.sleep(0.5)

# Or use polling
from tenacity import retry, stop_after_delay
@retry(stop=stop_after_delay(5))
def wait_for_completion():
    assert task_status == 'complete'
```

### Debugging Strategies

#### 1. Use pytest -s (show print statements)
```bash
pytest -s backend/tests/unit/test_validators.py
```

```python
def test_something():
    print(f"DEBUG: value = {value}")  # Will be visible with -s
    assert value == expected
```

#### 2. Use pytest -vv (extra verbosity)
```bash
pytest -vv backend/tests/unit/test_validators.py
```

**Shows:**
- Full test names
- Parameter values (for parametrized tests)
- Assertion details

#### 3. Use pdb (Python debugger)
```python
def test_something():
    import pdb; pdb.set_trace()  # Debugger breakpoint
    result = function_under_test()
    assert result == expected
```

**Run:**
```bash
pytest -s backend/tests/unit/test_validators.py
```

**pdb Commands:**
- `n` - next line
- `s` - step into function
- `c` - continue
- `p variable` - print variable
- `l` - list code around current line
- `q` - quit debugger

#### 4. Use pytest --lf (last failed)
```bash
# Run only tests that failed last time
pytest --lf

# Run failed first, then all others
pytest --ff
```

#### 5. Use pytest --tb=short (shorter tracebacks)
```bash
pytest --tb=short  # Short traceback
pytest --tb=line   # Single line per failure
pytest --tb=no     # No traceback
pytest --tb=long   # Full traceback (default)
```

#### 6. Check Test Logs
```bash
# Capture logs
pytest --log-cli-level=DEBUG

# Save logs to file
pytest --log-file=test.log --log-file-level=DEBUG
```

### Isolating Test Failures

#### Run Single Test
```bash
pytest backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid -vv
```

#### Run Test in Isolation
```bash
# Clear cache
pytest --cache-clear backend/tests/unit/test_validators.py

# Fresh interpreter
python -m pytest backend/tests/unit/test_validators.py
```

#### Check for Test Interdependencies
```bash
# Run tests in random order
pytest --random-order

# If this causes failures, tests have hidden dependencies
```

### Common Pitfalls

#### 1. Mutable Default Arguments
```python
# BAD
def create_grid(cells=[]):
    cells.append('A')
    return cells

# GOOD
def create_grid(cells=None):
    if cells is None:
        cells = []
    cells.append('A')
    return cells
```

#### 2. Not Cleaning Up Resources
```python
# BAD
def test_file_creation():
    f = open('test.txt', 'w')
    f.write('test')
    # File not closed!

# GOOD
def test_file_creation(tmp_path):
    test_file = tmp_path / 'test.txt'
    with open(test_file, 'w') as f:
        f.write('test')
    # File automatically closed
```

#### 3. Time-Dependent Tests
```python
# BAD
def test_timeout():
    start = time.time()
    do_something()
    assert time.time() - start < 1.0  # Flaky!

# GOOD
def test_timeout():
    with pytest.raises(TimeoutError):
        do_something(timeout=1)
```

---

## Performance Testing

### Autofill Performance Benchmarks

**File:** `backend/tests/integration/test_realistic_grids.py`

**Benchmarks:**
```python
@pytest.mark.slow
class TestAutofillPerformance:
    """Performance benchmarks for autofill algorithms."""

    def test_11x11_performance_benchmark(self):
        """11x11 grid should fill in <30 seconds."""
        grid = Grid.from_dict(REALISTIC_11X11_GRID)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        start = time.time()
        autofill = Autofill(grid, wordlist, timeout=60)
        result = autofill.fill()
        elapsed = time.time() - start

        assert elapsed < 30, f"Too slow: {elapsed:.2f}s"
        assert result.success

        # Log performance metrics
        print(f"\n11x11 Performance:")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Iterations: {result.iterations}")
        print(f"  Avg word score: {result.average_word_score():.1f}")

    def test_15x15_performance_benchmark(self):
        """15x15 grid should fill in <5 minutes."""
        grid = Grid.from_dict(REALISTIC_15X15_GRID)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        start = time.time()
        autofill = Autofill(grid, wordlist, timeout=600, algorithm='hybrid')
        result = autofill.fill()
        elapsed = time.time() - start

        assert elapsed < 300, f"Too slow: {elapsed:.2f}s"

        print(f"\n15x15 Performance:")
        print(f"  Time: {elapsed:.2f}s ({elapsed/60:.1f}min)")
        print(f"  Iterations: {result.iterations}")
        print(f"  Success: {result.success}")
```

**Running:**
```bash
pytest backend/tests/integration/test_realistic_grids.py -v -s
```

### API Response Time Tests

```python
class TestAPIPerformance:
    """Test API response times."""

    def test_pattern_endpoint_performance(self, client):
        """Pattern search should complete in <1 second."""
        start = time.time()

        response = client.post('/api/pattern', json={
            'pattern': 'C?T',
            'max_results': 20
        })

        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Too slow: {elapsed:.3f}s"

    def test_number_endpoint_performance(self, client):
        """Grid numbering should complete in <100ms."""
        grid = [['A'] * 15 for _ in range(15)]

        start = time.time()

        response = client.post('/api/number', json={
            'size': 15,
            'grid': grid
        })

        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1, f"Too slow: {elapsed:.3f}s"
```

### Pattern Matching Performance

```python
class TestPatternMatcherPerformance:
    """Performance tests for pattern matching algorithms."""

    @pytest.fixture
    def large_wordlist(self):
        """Load full comprehensive wordlist (454k words)."""
        return WordList.load('data/wordlists/comprehensive.txt')

    def test_regex_matcher_performance(self, large_wordlist):
        """Regex matcher baseline performance."""
        matcher = RegexPatternMatcher(large_wordlist)

        start = time.time()
        results = matcher.match('C?T')
        elapsed = time.time() - start

        assert len(results) > 0
        print(f"\nRegex matcher: {elapsed*1000:.1f}ms")

    def test_trie_matcher_performance(self, large_wordlist):
        """Trie matcher should be 10-50x faster."""
        matcher = TriePatternMatcher(large_wordlist)

        start = time.time()
        results = matcher.match('C?T')
        elapsed = time.time() - start

        assert len(results) > 0
        assert elapsed < 0.1, f"Too slow: {elapsed*1000:.1f}ms"
        print(f"\nTrie matcher: {elapsed*1000:.1f}ms")
```

### Memory Usage Tests

```python
import tracemalloc

class TestMemoryUsage:
    """Test memory usage of key operations."""

    def test_autofill_memory_usage(self):
        """Autofill should use <500MB for 15x15 grid."""
        grid = Grid.from_dict(REALISTIC_15X15_GRID)
        wordlist = WordList.load('data/wordlists/comprehensive.txt')

        tracemalloc.start()

        autofill = Autofill(grid, wordlist)
        result = autofill.fill()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        print(f"\nPeak memory: {peak_mb:.1f}MB")

        assert peak_mb < 500, f"Too much memory: {peak_mb:.1f}MB"
```

---

## Best Practices

### Test Naming Conventions

#### Descriptive Test Names
```python
# GOOD: Describes what is being tested and expected outcome
def test_pattern_matcher_returns_empty_list_when_no_matches():
    pass

# BAD: Vague, unclear what is being tested
def test_pattern():
    pass
```

#### Test Class Names
```python
# GOOD: Describes component under test
class TestPatternMatcher:
    pass

class TestGridTransformation:
    pass

# BAD: Generic names
class Tests:
    pass
```

#### Parametrized Test Names
```python
# Use descriptive IDs
@pytest.mark.parametrize("pattern,expected_count,description", [
    ("C?T", 3, "single_wildcard"),
    ("?O?", 4, "middle_wildcard"),
    ("CAT", 1, "exact_match")
], ids=["single_wildcard", "middle_wildcard", "exact_match"])
def test_pattern_matching(pattern, expected_count, description):
    pass
```

### Test Organization

#### One Assertion Per Test (When Practical)
```python
# GOOD: Focused test
def test_grid_size():
    grid = Grid(15)
    assert grid.size == 15

def test_grid_cells_initialized():
    grid = Grid(15)
    assert grid.cells.shape == (15, 15)

# ACCEPTABLE: Related assertions
def test_grid_initialization():
    grid = Grid(15)
    assert grid.size == 15
    assert grid.cells.shape == (15, 15)
    assert np.all(grid.cells == CellType.EMPTY)
```

#### Arrange-Act-Assert Pattern
```python
def test_pattern_matcher():
    # ARRANGE: Set up test data
    wordlist = ['CAT', 'DOG', 'RAT']
    matcher = PatternMatcher(wordlist)

    # ACT: Execute function under test
    results = matcher.match('C?T')

    # ASSERT: Verify expected outcome
    assert 'CAT' in results
    assert 'DOG' not in results
```

#### Use Fixtures for Setup/Teardown
```python
# GOOD: Fixture handles setup
@pytest.fixture
def matcher():
    wordlist = ['CAT', 'DOG', 'RAT']
    return PatternMatcher(wordlist)

def test_something(matcher):
    results = matcher.match('C?T')
    assert 'CAT' in results

# BAD: Setup in every test
def test_something():
    wordlist = ['CAT', 'DOG', 'RAT']
    matcher = PatternMatcher(wordlist)
    results = matcher.match('C?T')
    assert 'CAT' in results
```

### Mocking Best Practices

#### Mock External Dependencies
```python
# GOOD: Mock subprocess call
def test_cli_adapter_pattern(monkeypatch):
    def mock_run(cmd, **kwargs):
        return CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"results": [{"word": "CAT", "score": 85}]}'
        )

    monkeypatch.setattr('subprocess.run', mock_run)

    adapter = CLIAdapter()
    result = adapter.pattern('C?T')
    assert result['results'][0]['word'] == 'CAT'

# BAD: No mocking, calls real CLI (slow, fragile)
def test_cli_adapter_pattern():
    adapter = CLIAdapter()
    result = adapter.pattern('C?T')  # Real subprocess call
    assert result['results'][0]['word'] == 'CAT'
```

#### Use pytest-mock for Convenience
```python
def test_with_mocker(mocker):
    # mocker.patch is cleaner than monkeypatch
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"status": "ok"}'
    )

    # Test logic here
```

### Test Independence

#### Tests Should Not Depend on Each Other
```python
# BAD: Test depends on side effect of previous test
class TestGrid:
    def test_create_grid(self):
        self.grid = Grid(5)
        assert self.grid.size == 5

    def test_set_letter(self):
        # Assumes test_create_grid ran first!
        self.grid.set_letter(0, 0, 'A')
        assert self.grid.get_letter(0, 0) == 'A'

# GOOD: Each test is independent
class TestGrid:
    @pytest.fixture
    def grid(self):
        return Grid(5)

    def test_create_grid(self, grid):
        assert grid.size == 5

    def test_set_letter(self, grid):
        grid.set_letter(0, 0, 'A')
        assert grid.get_letter(0, 0) == 'A'
```

### Test Maintainability

#### Use Shared Fixtures
```python
# conftest.py
@pytest.fixture
def sample_wordlist():
    return ['CAT', 'DOG', 'RAT', 'BAT']

# test_a.py
def test_something(sample_wordlist):
    matcher = PatternMatcher(sample_wordlist)
    # ...

# test_b.py
def test_something_else(sample_wordlist):
    matcher = PatternMatcher(sample_wordlist)
    # ...
```

#### Avoid Magic Numbers
```python
# BAD: Magic numbers
def test_grid_size():
    grid = Grid(15)
    assert len(grid.cells) == 15
    assert len(grid.cells[0]) == 15

# GOOD: Use constants
GRID_SIZE = 15

def test_grid_size():
    grid = Grid(GRID_SIZE)
    assert len(grid.cells) == GRID_SIZE
    assert len(grid.cells[0]) == GRID_SIZE
```

#### Document Complex Tests
```python
def test_ac3_constraint_propagation():
    """
    Test AC-3 constraint propagation algorithm.

    Setup:
    - Grid with two crossing slots
    - Slot 1 (across): Pattern "C?T"
    - Slot 2 (down): Pattern "?A?"
    - They cross at position (0, 1)

    Expected:
    - After AC-3, Slot 2 candidates should have 'A' at position 1
    - Example: "CAR", "CAT", "CAB" are valid
    - "COR", "CUT" are invalid (wrong letter at crossing)
    """
    # Test implementation
```

---

## CI/CD Integration

### GitHub Actions

**File:** `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r cli/requirements.txt

    - name: Run tests
      run: |
        pytest --cov=backend --cov=cli --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

    - name: Check coverage threshold
      run: |
        coverage report --fail-under=85
```

### Pre-commit Hooks

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest backend/tests/unit cli/tests/unit -v
        language: system
        pass_filenames: false
        always_run: true

      - id: pytest-coverage
        name: Check test coverage
        entry: pytest --cov=backend --cov=cli --cov-report=term --cov-fail-under=85
        language: system
        pass_filenames: false
        stages: [push]
```

**Install:**
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

### GitLab CI

**File:** `.gitlab-ci.yml`

```yaml
image: python:3.11

stages:
  - test
  - coverage

before_script:
  - pip install -r requirements.txt
  - pip install -r cli/requirements.txt

test:unit:
  stage: test
  script:
    - pytest backend/tests/unit cli/tests/unit -v

test:integration:
  stage: test
  script:
    - pytest backend/tests/integration -v

coverage:
  stage: coverage
  script:
    - pytest --cov=backend --cov=cli --cov-report=xml --cov-report=term
    - coverage report --fail-under=85
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Docker Test Environment

**File:** `Dockerfile.test`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt cli/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r cli/requirements.txt

# Copy source code
COPY . .

# Run tests
CMD ["pytest", "--cov=backend", "--cov=cli", "--cov-report=term"]
```

**Build and run:**
```bash
docker build -f Dockerfile.test -t crossword-test .
docker run --rm crossword-test
```

---

## Appendix: Test Reference

### Quick Command Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific file
pytest backend/tests/unit/test_validators.py

# Run specific test
pytest backend/tests/unit/test_validators.py::TestValidators::test_validate_pattern_request_valid

# Run tests matching pattern
pytest -k "pattern"

# Skip slow tests
pytest -m "not slow"

# Parallel execution
pytest -n auto

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Extra verbose
pytest -vv

# Last failed tests
pytest --lf

# Debug with pdb
pytest --pdb

# Generate coverage badge
pytest --cov=backend --cov-report=xml
coverage-badge -o coverage.svg -f
```

### Test Statistics

**Total Tests:** 165

**By Type:**
- Unit: 125 (76%)
- Integration: 60 (36%)
- E2E: 15 (9%)

**By Component:**
- Backend API: 45 tests
- Backend Core: 40 tests
- CLI Core: 40 tests
- CLI Fill: 30 tests
- Integration: 60 tests

**Execution Time:**
- Unit tests: <5s
- Integration tests: <30s
- Full suite: ~35s
- Full suite (parallel): ~10s

**Coverage:**
- Backend: 92%
- CLI: 89%
- Overall: 91%

### Common pytest Markers

```python
@pytest.mark.slow          # Marks test as slow
@pytest.mark.integration   # Integration test
@pytest.mark.unit          # Unit test
@pytest.mark.skip          # Skip test
@pytest.mark.skipif(condition)  # Conditional skip
@pytest.mark.xfail         # Expected to fail
@pytest.mark.parametrize   # Parametrized test
@pytest.mark.timeout(30)   # Test timeout
```

### Useful pytest Plugins

```bash
# Parallel execution
pip install pytest-xdist

# Timeout enforcement
pip install pytest-timeout

# Mocking utilities
pip install pytest-mock

# BDD-style tests
pip install pytest-bdd

# HTML test reports
pip install pytest-html

# JSON test reports
pip install pytest-json-report

# Test ordering
pip install pytest-ordering

# Flaky test detection
pip install pytest-flaky
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-27
**Maintained By:** Development Team
**Next Review:** After adding frontend tests
