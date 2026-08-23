"""Unit tests for the fill CLI command's process-level contract.

These tests pin the exit-code contract, which the backend depends on:
backend/core/cli_adapter.py raises CalledProcessError on any non-zero exit
(cli_adapter.py:80), so what fill exits with decides whether a legitimate
partial fill reaches the UI as a result or as an error.

Contract, deliberate:
- exit 0 - the solver ran and produced a result, INCLUDING a partial or
  unsuccessful fill. The JSON `success` field is the outcome signal, not the
  exit code.
- exit 1 - the run could not happen or could not finish: bad arguments,
  missing files, invalid theme entries, an out-of-range timeout.

A caller must never infer fill quality from the exit code.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_fill(args, cwd=None):
    """Helper: run the fill CLI command and return (stdout, stderr, returncode)."""
    if cwd is None:
        cwd = PROJECT_ROOT
    cmd = [sys.executable, "-m", "cli.src.cli", "fill"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    return result.stdout, result.stderr, result.returncode


def last_json(stdout):
    """Extract the final JSON object from stdout, which is mixed with progress lines."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


@pytest.fixture
def small_grid():
    """5x5 grid with symmetric black squares; every slot is 3-5 cells."""
    grid_data = {
        "size": 5,
        "grid": [
            [".", ".", ".", "#", "#"],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            ["#", ".", ".", ".", "."],
            ["#", "#", ".", ".", "."],
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(grid_data, f)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tiny_wordlist():
    """Too few words to fill the grid, so the fill completes but does not succeed."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("CAT\nDOG\nEMU\nABCDE\nFGHIJ\n")
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestFillExitCodes:
    """The process-level contract the backend adapter reads."""

    def test_timeout_below_floor_is_a_clean_error_not_a_traceback(self, small_grid, tiny_wordlist):
        """A -t below the repair algorithm's floor must fail like a CLI, not crash.

        iterative_repair.fill() enforces a 10-second floor with a raw `raise`.
        Uncaught, that reaches the user as a Python traceback.
        """
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "5", "--allow-nonstandard"])

        assert rc == 1, f"expected exit 1 for an out-of-range timeout, got {rc}"
        assert "Traceback" not in stderr, f"raw traceback leaked to the user:\n{stderr[-600:]}"
        combined = stdout + stderr
        assert "timeout" in combined.lower(), "the error should name the offending option"

    def test_timeout_below_floor_emits_json_error_when_json_output(self, small_grid, tiny_wordlist):
        """With --json-output the same failure must still be machine-readable."""
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "5", "--allow-nonstandard", "--json-output"])

        assert rc == 1
        assert "Traceback" not in stderr
        payload = last_json(stdout)
        assert payload is not None, f"no JSON on stdout; stderr was:\n{stderr[-400:]}"
        assert payload.get("success") is False
        assert "error" in payload

    def test_unsuccessful_fill_still_exits_zero(self, small_grid, tiny_wordlist):
        """A completed-but-unsuccessful fill is a result, not an error.

        This is deliberate. The backend renders partial fills as a normal
        outcome, and cli_adapter.py:80 turns any non-zero exit into an
        exception, so exiting non-zero here would break that path.
        """
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "10", "--allow-nonstandard", "--json-output"])

        payload = last_json(stdout)
        assert payload is not None, f"no JSON on stdout; stderr was:\n{stderr[-400:]}"
        assert payload["success"] is False, "fixture should not be fillable with this wordlist"
        assert rc == 0, "a completed run exits 0 regardless of fill success"

    def test_missing_wordlist_exits_one(self, small_grid):
        """Preflight failures are genuine errors and exit non-zero."""
        stdout, stderr, rc = run_fill([small_grid, "-w", "does/not/exist.txt", "-t", "10", "--allow-nonstandard"])

        assert rc == 1
        assert "Traceback" not in stderr
