# Testing Guide

**Version 3.0.0**
**Document Type:** Operations Guide

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

This document intentionally contains **no test counts, pass rates, or coverage
percentages**. Those numbers change every time a test is added and go stale
silently in prose. Wherever a number would normally appear, this guide gives
the command that produces it instead. Run the command to get the current
number.

---

## Overview

**[SPEC]**
- Three suites: `backend/tests/`, `cli/tests/`, `tests/` (see `pytest.ini` `testpaths`).
- Test types: unit (isolated, mocked), integration (real subprocess/file I/O,
  Flask test client), and a `slow` subset (marked `@pytest.mark.slow`) covering
  realistic-grid and end-to-end pause/resume scenarios.
- To see current test counts, pass rates, or timing, run the suite yourself —
  see [Running Tests](#running-tests). Do not trust a written-down number.

```bash
# How many tests exist right now, broken down by directory
pytest --collect-only -q

# How many tests exist in the fast (non-slow) default set
pytest -m "not slow" --collect-only -q
```

**[NOTE]** The project follows a test-driven approach: unit tests for
isolated logic, integration tests for API/CLI subprocess boundaries, and a
`slow`-marked layer for realistic 11×11/15×15/21×21 grids and full
pause/resume workflows. There is no committed frontend test suite yet.

---

## Test Environment Setup

**[SPEC]**
```bash
git clone <repo-url>
cd crossword-helper

python3 -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

`requirements.txt` at the repo root pulls in `pytest`, `pytest-cov`,
`pytest-xdist`, and `pytest-mock` for you — there is no separate
`cli/requirements.txt` install step and no pinned-version list to maintain
here. Check `requirements.txt` itself for exact versions.

```bash
# Verify pytest is installed and can discover tests
pytest --version
pytest --collect-only
```

### pytest.ini

**[SPEC]** This is the real, current file — copy it from here, don't
paraphrase it:

```ini
[pytest]
testpaths = backend/tests cli/tests tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
norecursedirs = tests/legacy .git __pycache__ *.egg-info dist build
addopts = -v -m "not slow"
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

Key points that differ from what you might expect:
- **No `--cov` in `addopts`.** Coverage is opt-in per invocation (`pytest
  --cov=backend --cov=cli ...`), not a default. Running plain `pytest` does
  not generate a coverage report.
- **`slow` tests are excluded by default** (`-m "not slow"` is baked into
  `addopts`). Run `pytest -m slow` explicitly to include them.
- **`unit` and `integration` markers are registered but not applied to any
  test function** — see the [BUG] block under [Markers](#markers).

---

## Directory Layout

**[SPEC]** Verified against the working tree:

```
backend/tests/
├── conftest.py                 # shared fixtures (cli_available, skip_if_no_cli, app, client)
├── test_api.py                 # core API endpoint tests
├── test_openapi_contract.py
├── fixtures/
│   ├── grid_fixtures.py            # small synthetic grids
│   └── realistic_grid_fixtures.py  # NYT-style grids for slow/perf tests
├── unit/
│   ├── test_validators.py
│   ├── test_edit_merger.py
│   ├── test_grid_transformation.py
│   ├── test_cli_adapter.py
│   ├── test_routes.py
│   ├── test_constraint_routes.py
│   ├── test_pause_resume_routes.py
│   ├── test_black_square_suggester.py
│   ├── test_theme_placer.py
│   └── test_wordlist_manager.py
└── integration/
    ├── conftest.py              # Flask client, SSE parser, grid/task helpers
    ├── test_cli_integration.py
    ├── test_pause_resume_api.py
    ├── test_progress_integration.py
    ├── test_realistic_grids.py
    ├── test_e2e_pause_resume.py
    ├── test_adaptive_beam_search_api.py
    ├── test_adaptive_beam_crash_fix.py
    ├── test_adaptive_on_backtrack.py
    ├── test_all_beam_scenarios.py
    ├── test_beam_search_pause_resume.py
    ├── test_constraint_integration.py
    ├── test_theme_placement_conflicts.py
    ├── test_theme_priority.py
    ├── test_wordlist_metadata.py
    ├── sse/
    └── workflows/

cli/tests/
├── unit/
├── integration/
└── performance/                 # manual benchmark scripts, not collected by pytest
```

**[NOTE]** `backend/tests/test_api.py` lives at the top of `backend/tests/`,
not under `integration/` — a previous revision of this doc pointed at
`backend/tests/integration/test_api.py`, which does not exist.

`cli/tests/performance/` holds manual benchmark scripts
(`benchmark_algorithms.py` and similar), not pytest tests — see
`cli/tests/performance/README.md`. They are run by hand, not by CI.

---

## Markers

**[SPEC]**
```python
@pytest.mark.slow          # excluded by default via addopts; opt in with -m slow
```

```bash
pytest -m slow             # run only slow tests
pytest -m "not slow"       # run only fast tests (the default)
```

**[BUG] `pytest -m unit` / `pytest -m integration` select nothing**
- **Symptom:** `pytest -m unit` and `pytest -m integration` both report every
  test deselected — 0 tests run.
- **Cause:** `unit` and `integration` are registered in `pytest.ini`
  `markers =` but no test function in the suite is actually decorated with
  `@pytest.mark.unit` or `@pytest.mark.integration`. Directory placement
  (`backend/tests/unit/` vs `backend/tests/integration/`) is what actually
  separates them — the markers are dead weight.
- **Fix:** none applied. To select unit vs. integration tests, target the
  directory instead:
  ```bash
  pytest backend/tests/unit cli/tests/unit
  pytest backend/tests/integration cli/tests/integration
  ```

---

## Running Tests

**[SPEC]**
```bash
# Full default suite (slow tests excluded per addopts)
pytest

# Include slow tests
pytest -m slow
pytest                      # (slow tests still excluded — combine explicitly)

# One file
pytest backend/tests/unit/test_validators.py

# One class / one test
pytest backend/tests/unit/test_validators.py::TestValidatePatternRequest
pytest backend/tests/unit/test_validators.py::TestValidatePatternRequest::test_valid_minimal

# By keyword
pytest -k "pattern"

# Directory-based unit/integration split (see Markers BUG above)
pytest backend/tests/unit cli/tests/unit
pytest backend/tests/integration cli/tests/integration

# Parallel (pytest-xdist)
pytest -n auto

# Coverage (opt-in — not in addopts)
pytest --cov=backend --cov=cli --cov-report=term-missing
pytest --cov=backend --cov=cli --cov-report=html   # then open htmlcov/index.html

# Stop on first failure / show prints / extra verbosity
pytest -x
pytest -s
pytest -vv

# Re-run only what failed last time
pytest --lf
pytest --ff

# Drop into pdb on failure
pytest --pdb
```

---

## Writing a Test Here

**[SPEC]** Shared fixtures, verified against the actual files:

`backend/tests/conftest.py`:
- `cli_available` (session-scoped) — pings `CLIAdapter.health_check()`.
- `skip_if_no_cli` — skips the test if `cli_available` is false.
- `app`, `client` — Flask app/test client via `create_app(testing=True)`.

`backend/tests/integration/conftest.py`:
- `client` — separate Flask test client for the integration package.
- `sse_parser` — parses raw SSE byte streams into a list of JSON message dicts.
- `create_test_grid(size)`, `start_fill_task(client, ...)` — module-level
  helpers (not fixtures) for building empty frontend-format grids and kicking
  off an autofill task.

`backend/tests/fixtures/`:
- `grid_fixtures.py` — small synthetic grids (3×3, 5×5) in both frontend and
  CLI formats, used for transformation tests.
- `realistic_grid_fixtures.py` — NYT-style 11×11/15×15/21×21 grids, used by
  the `slow`-marked realistic-grid and performance tests.

**[NOTE]** A real, current unit test (`backend/tests/unit/test_validators.py`)
for the shape to follow — no mocking needed, pure function under test:

```python
class TestValidatePatternRequest:
    """Tests for validate_pattern_request."""

    def test_valid_minimal(self):
        data = {"pattern": "C?T"}
        assert validate_pattern_request(data) is data

    def test_missing_pattern_raises(self):
        with pytest.raises(ValueError, match="'pattern' is required"):
            validate_pattern_request({"wordlists": ["a.txt"]})
```

A real regression test (`backend/tests/unit/test_grid_transformation.py`)
guarding a specific historical bug — empty cells must become `.`, not `''`,
or the CLI rejects the grid:

```python
def test_empty_cell_transformation(self):
    """Test that empty cells (letter='') become '.'"""
    frontend_grid = [[{"letter": "", "isBlack": False}]]
    result = transform_grid_frontend_to_cli(frontend_grid)

    assert result == [["."]], "Empty cell should become '.'"
```

For subprocess-backed integration tests (CLIAdapter, CLI commands), mock
`subprocess.run` for the fast unit-level cases and reserve real subprocess
calls for `backend/tests/integration/test_cli_integration.py`. See the
[BUG] block below before writing a *new* test that spawns a CLI child.

---

## Debugging Failed Tests

**[SPEC]**
```bash
pytest --tb=short          # shorter traceback
pytest --tb=line           # one line per failure
pytest -l                  # show local variables on failure
pytest --log-cli-level=DEBUG
```

**[BUG] Subprocess-spawning tests run ~4x slower and can time out — but only under `--cov`**
- **Symptom:** Tests that spawn a CLI child process (e.g. the fill-then-resume
  flow in `test_cli_integration.py`) run fine locally and in the non-coverage
  CI jobs, but time out or run dramatically slower specifically in the job
  that runs with `--cov`.
- **Cause:** `pytest-cov` installs a `.pth` file that calls
  `pytest_cov.embed.init()` in **every** Python subprocess whenever
  `COV_CORE_SOURCE` is set in the environment. A child process spawned via
  `subprocess.Popen`/`subprocess.run` inherits `os.environ`, so it inherits
  `COV_CORE_SOURCE` too and gets coverage-instrumented — even though nobody
  asked to measure coverage *inside* that child. Measured on one machine:
  the affected test took roughly 4x longer with `--cov` than without it,
  which on a loaded CI runner was enough to blow through the test's timeout.
- **Fix:** scrub `COV_CORE_*` from the child's environment before spawning it
  (or, per-test, via `monkeypatch.delenv` for the duration of the test). The
  parent process's own coverage collection is unaffected — the plugin
  collects in-process, and these environment variables only arm *new*
  interpreters.
  ```python
  for key in [k for k in os.environ if k.startswith("COV_CORE")]:
      monkeypatch.delenv(key, raising=False)
  ```
  Applied in `backend/tests/integration/test_cli_integration.py`
  (`test_pause_then_fill_with_resume`). Any new test that spawns a CLI child
  and cares about wall-clock timing should do the same.

**[NOTE]** Common non-project-specific failure modes (import errors from an
unconfigured `PYTHONPATH`, missing `conftest.py` fixtures, mutable default
arguments, tests that depend on execution order) apply here as in any pytest
project — nothing about this repo changes that guidance, so it isn't repeated
here.

---

## Continuous Integration

**[SPEC]** The real files, read directly — do not keep a copy of their
contents in this doc, since copies drift. Read the files themselves:

- **`.github/workflows/test.yml`** — `Tests & Coverage` workflow. Runs a
  `test` job across a Python version matrix (unit tests, then integration
  tests, coverage collected only on the last matrix entry and uploaded to
  Codecov), a separate `lint` job (flake8/black/isort), and a `docs` job that
  runs `scripts/docs-check.sh`.
- **`.pre-commit-config.yaml`** — formatting/lint hooks only: `black`,
  `isort`, `ruff`, `flake8`. There are no test-running or coverage
  pre-commit hooks in this repo.
- **`scripts/docs-check.sh`** — the guard that keeps *this* document honest:
  fails CI on dead relative links and on banned derivable-state patterns
  (test counts, pass rates, frozen completion-status lines, etc.) in any
  live doc.

```bash
# Install pre-commit hooks locally
pip install pre-commit
pre-commit install
```

**[?]** There is no GitLab CI config (`.gitlab-ci.yml`) and no
`Dockerfile.test` in this repository. An earlier revision of this document
described both in detail; neither exists, and there is no evidence either
was ever wired into this project's actual CI. Not documented here.

---

## Changelog

- **3.0.0** — Rewritten to remove all derivable-state claims (test counts,
  pass rates, coverage percentages) per the no-status-claims policy. Deleted
  the fabricated CI/CD Integration section (GitHub Actions YAML, GitLab CI,
  pre-commit config, Dockerfile.test that did not match any file in the
  repo) and replaced it with pointers to the real `.github/workflows/test.yml`
  and `.pre-commit-config.yaml`. Corrected `backend/tests/integration/test_api.py`
  → `backend/tests/test_api.py`. Documented the `pytest -m unit`/`-m
  integration` dead-marker bug and the `COV_CORE_SOURCE` subprocess-slowdown
  bug as `[BUG]` blocks. Converted to HADS format.
- **2.0.0** — prior revision (superseded; carried a frozen all-passing
  status line and a fabricated CI/CD section — see above).
