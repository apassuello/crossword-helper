"""Unit tests for the pattern CLI command.

Regression tests for:
- scored wordlists (WORD;SCORE and word,score) silently returning 0 matches
- invalid patterns silently returning 0 results instead of an error
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_pattern(args, cwd=None):
    """Helper: run the pattern CLI command and return (stdout, stderr, returncode)."""
    if cwd is None:
        cwd = PROJECT_ROOT
    cmd = [sys.executable, "-m", "cli.src.cli", "pattern"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode


@pytest.fixture
def scored_semicolon_wordlist():
    """Temp wordlist in WORD;SCORE format (with comment header)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("# Format: WORD;SCORE\nCAT;50\nCOT;42\nCUT;77\nDOG;10\n")
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def scored_comma_wordlist():
    """Temp wordlist in word,score CSV format (with header row)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("word,score\ncat,55\ncob,33\ncup,60\n")
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestScoredWordlists:
    """Scored wordlist formats must produce pattern matches with file scores."""

    def test_semicolon_scored_wordlist_matches(self, scored_semicolon_wordlist):
        """WORD;SCORE wordlists used to silently return 0 matches."""
        stdout, stderr, rc = run_pattern(["C?T", "-w", scored_semicolon_wordlist, "--json-output"])
        assert rc == 0, f"Command failed (rc={rc}): {stderr}"
        data = json.loads(stdout.strip())
        assert data["meta"]["total_found"] == 3
        words = {r["word"]: r["score"] for r in data["results"]}
        assert words == {"CAT": 50, "COT": 42, "CUT": 77}

    def test_comma_scored_wordlist_matches(self, scored_comma_wordlist):
        """word,score CSV wordlists (broda.owl style) must also work."""
        stdout, stderr, rc = run_pattern(["C??", "-w", scored_comma_wordlist, "--json-output"])
        assert rc == 0, f"Command failed (rc={rc}): {stderr}"
        data = json.loads(stdout.strip())
        words = {r["word"]: r["score"] for r in data["results"]}
        assert words == {"CAT": 55, "COB": 33, "CUP": 60}

    def test_regex_and_trie_return_identical_results(self, scored_semicolon_wordlist):
        """Both algorithms must return the same matches for scored lists."""
        results = {}
        for algo in ("regex", "trie"):
            stdout, stderr, rc = run_pattern(["C?T", "-w", scored_semicolon_wordlist, "-a", algo, "--json-output"])
            assert rc == 0, f"{algo} failed (rc={rc}): {stderr}"
            data = json.loads(stdout.strip())
            results[algo] = sorted((r["word"], r["score"]) for r in data["results"])

        assert results["regex"] == results["trie"]
        assert results["regex"] == [("CAT", 50), ("COT", 42), ("CUT", 77)]


class TestInvalidPatterns:
    """Invalid patterns must error out instead of silently returning 0 results."""

    def test_digit_in_pattern_errors(self, scored_semicolon_wordlist):
        stdout, stderr, rc = run_pattern(["C1T", "-w", scored_semicolon_wordlist])
        assert rc != 0
        assert "Invalid character" in stderr

    def test_symbol_in_pattern_errors_json(self, scored_semicolon_wordlist):
        stdout, stderr, rc = run_pattern(["C-T", "-w", scored_semicolon_wordlist, "--json-output"])
        assert rc != 0
        data = json.loads(stdout.strip())
        assert data["success"] is False
        assert "Invalid character" in data["error"]

    def test_too_short_pattern_errors(self, scored_semicolon_wordlist):
        stdout, stderr, rc = run_pattern(["??", "-w", scored_semicolon_wordlist])
        assert rc != 0
        assert "out of range" in stderr

    def test_too_long_pattern_errors(self, scored_semicolon_wordlist):
        stdout, stderr, rc = run_pattern(["?" * 25, "-w", scored_semicolon_wordlist])
        assert rc != 0
        assert "out of range" in stderr

    def test_dot_wildcard_still_valid(self, scored_semicolon_wordlist):
        """'.' is a documented wildcard alias and must not be rejected."""
        stdout, stderr, rc = run_pattern(["C.T", "-w", scored_semicolon_wordlist, "--json-output"])
        assert rc == 0, f"Command failed (rc={rc}): {stderr}"
        data = json.loads(stdout.strip())
        assert data["meta"]["total_found"] == 3


class TestUnloadableWordlist:
    """Spec O1 (#44): a list that cannot load is reported, the others still searched."""

    def test_json_output_lists_errors_and_searches_other_lists(self, scored_semicolon_wordlist, tmp_path):
        missing = str(tmp_path / "nope.txt")
        out, _err, rc = run_pattern(["C?T", "-w", scored_semicolon_wordlist, "-w", missing, "--json-output"])
        assert rc == 0
        data = json.loads(out)
        assert {r["word"] for r in data["results"]} == {"CAT", "COT", "CUT"}
        assert len(data["errors"]) == 1
        assert data["errors"][0]["wordlist"] == missing
        assert isinstance(data["errors"][0]["message"], str) and data["errors"][0]["message"]

    def test_json_output_errors_empty_when_all_load(self, scored_semicolon_wordlist):
        out, _err, rc = run_pattern(["C?T", "-w", scored_semicolon_wordlist, "--json-output"])
        assert rc == 0
        assert json.loads(out)["errors"] == []

    def test_text_output_prints_one_warning_line_per_list(self, scored_semicolon_wordlist, tmp_path):
        missing = str(tmp_path / "nope.txt")
        out, err, rc = run_pattern(["C?T", "-w", scored_semicolon_wordlist, "-w", missing])
        assert rc == 0
        warnings = [ln for ln in (out + err).splitlines() if ln.startswith("Warning:") and missing in ln]
        assert len(warnings) == 1
        assert "CAT" in out
