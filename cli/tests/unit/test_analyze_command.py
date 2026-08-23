"""Unit tests for the analyze CLI command."""

import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_analyze(args, cwd=None):
    """Helper: run the analyze CLI command and return (stdout, stderr, returncode)."""
    if cwd is None:
        cwd = PROJECT_ROOT
    cmd = [sys.executable, "-m", "cli.src.cli", "analyze"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode


@pytest.fixture
def grid_file():
    """Create a temp 5x5 grid file."""
    grid_data = {
        "size": 5,
        "grid": [
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(grid_data, f)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def wordlist():
    """Path to a small wordlist."""
    return "data/wordlists/core/crosswordese.txt"


class TestAnalyzeCommand:

    def test_analyze_produces_json_output(self, grid_file, wordlist):
        """analyze --json-output returns valid JSON with constraints and summary."""
        stdout, stderr, rc = run_analyze([grid_file, "-w", wordlist, "--json-output"])
        assert rc == 0, f"Command failed (rc={rc}): {stderr}"
        data = json.loads(stdout.strip())
        assert "constraints" in data
        assert "summary" in data
        assert data["success"] is True

    def test_analyze_summary_keys(self, grid_file, wordlist):
        """Summary contains total_cells, critical_cells, average_min_options."""
        stdout, _, rc = run_analyze([grid_file, "-w", wordlist, "--json-output"])
        assert rc == 0
        data = json.loads(stdout.strip())
        summary = data["summary"]
        assert "total_cells" in summary
        assert "critical_cells" in summary
        assert "average_min_options" in summary

    def test_analyze_5x5_has_25_cells(self, grid_file, wordlist):
        """Empty 5x5 grid reports 25 white cells."""
        stdout, _, rc = run_analyze([grid_file, "-w", wordlist, "--json-output"])
        assert rc == 0
        data = json.loads(stdout.strip())
        assert data["summary"]["total_cells"] == 25

    def test_analyze_missing_wordlist_fails(self, grid_file):
        """analyze without -w flag exits with error."""
        stdout, stderr, rc = run_analyze([grid_file, "--json-output"])
        assert rc != 0

    def test_analyze_slot_without_word_fails(self, grid_file, wordlist):
        """--slot without --word exits with error."""
        stdout, stderr, rc = run_analyze([grid_file, "-w", wordlist, "--slot", "0,0,across,5", "--json-output"])
        assert rc != 0

    def test_analyze_placement_impact(self):
        """analyze with --word and --slot returns impacts dict."""
        # Use a wordlist we know contains common 5-letter words, and ERA as a 3-letter word.
        # Write a temp grid with a known 5-letter slot at row 0.
        grid_data = {
            "size": 5,
            "grid": [[".", ".", ".", ".", "."] for _ in range(5)],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            gf = f.name
        try:
            stdout, stderr, rc = run_analyze(
                [
                    gf,
                    "-w",
                    "data/wordlists/core/crosswordese.txt",
                    "--word",
                    "EARTH",
                    "--slot",
                    "0,0,across,5",
                    "--json-output",
                ]
            )
            assert rc == 0, f"Command failed (rc={rc}): stderr={stderr[:200]}"
            data = json.loads(stdout.strip())
            assert "impacts" in data, f"Expected 'impacts' key, got: {list(data.keys())}"
            assert "summary" in data
            assert data["summary"]["total_crossings"] > 0
        finally:
            os.unlink(gf)

    def test_analyze_word_without_slot_runs_grid_analysis(self, grid_file, wordlist):
        """--word without --slot silently falls back to grid-wide constraint analysis."""
        stdout, stderr, rc = run_analyze([grid_file, "-w", wordlist, "--word", "EARTH", "--json-output"])
        assert rc == 0
        data = json.loads(stdout.strip())
        # Should return grid-wide constraints, not impact (slot was not provided)
        assert "constraints" in data

    def test_analyze_human_readable_grid_output(self, grid_file, wordlist):
        """Without --json-output, analyze prints human-readable grid analysis."""
        stdout, stderr, rc = run_analyze([grid_file, "-w", wordlist])
        assert rc == 0, f"Command failed (rc={rc}): {stderr}"
        assert "Grid analysis:" in stdout, f"Expected 'Grid analysis:' in stdout, got: {stdout!r}"
        assert "Critical cells" in stdout
        assert "Average min options" in stdout

    def test_analyze_human_readable_placement_output(self):
        """Without --json-output, analyze with --word and --slot prints placement impact."""
        grid_data = {
            "size": 5,
            "grid": [[".", ".", ".", ".", "."] for _ in range(5)],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            gf = f.name
        try:
            stdout, stderr, rc = run_analyze(
                [
                    gf,
                    "-w",
                    "data/wordlists/core/crosswordese.txt",
                    "--word",
                    "EARTH",
                    "--slot",
                    "0,0,across,5",
                ]
            )
            assert rc == 0, f"Command failed (rc={rc}): {stderr}"
            assert (
                "Placement impact for EARTH:" in stdout
            ), f"Expected 'Placement impact for EARTH:' in stdout, got: {stdout!r}"
        finally:
            os.unlink(gf)
