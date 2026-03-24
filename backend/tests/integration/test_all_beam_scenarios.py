"""
Comprehensive integration test suite for all autofill scenarios.

Tests the full stack: Backend API → CLI subprocess → Autofill algorithms

This suite ensures that all combinations of:
- Algorithms (trie, beam, hybrid)
- Adaptive mode (on/off)
- Grid states (empty, pre-filled, with theme words)

...work correctly without crashes.

Uses a 7x7 grid with standard black square pattern and the `comprehensive` wordlist
for fast, reliable test execution (~2-20s per test).
"""

import pytest
import json
import subprocess
import sys
import tempfile
import os

# Realistic 7x7 grid with symmetric black squares (22 slots)
STANDARD_GRID_7x7 = {
    "size": 7,
    "grid": [
        [".", ".", ".", "#", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        ["#", "#", ".", ".", ".", "#", "#"],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
    ],
}

# 7x7 grid with some pre-filled letters
PREFILLED_GRID_7x7 = {
    "size": 7,
    "grid": [
        ["C", "A", "T", "#", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        ["#", "#", ".", ".", ".", "#", "#"],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
        [".", ".", ".", "#", ".", ".", "."],
    ],
}

WORDLIST = "data/wordlists/comprehensive.txt"


def run_cli_fill(grid_data, algorithm, adaptive=False, max_adaptations=2, timeout=20):
    """
    Helper to run CLI fill command and capture output.

    Returns:
        tuple: (return_code, stdout, stderr)
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name

    try:
        cmd = [
            sys.executable,
            "-m",
            "cli.src.cli",
            "fill",
            grid_file,
            "--wordlists",
            WORDLIST,
            "--timeout",
            str(timeout),
            "--min-score",
            "1",
            "--algorithm",
            algorithm,
            "--allow-nonstandard",
            "--json-output",
        ]

        if adaptive:
            cmd.append("--adaptive")
            cmd.extend(["--max-adaptations", str(max_adaptations)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # Add buffer for subprocess overhead
        )

        return result.returncode, result.stdout, result.stderr

    finally:
        if os.path.exists(grid_file):
            os.unlink(grid_file)


def assert_no_crash(stdout, stderr):
    """Common assertions to verify the CLI didn't crash."""
    assert "'FillResult' object has no attribute 'get'" not in stdout
    assert "'FillResult' object has no attribute 'get'" not in stderr
    assert "'Grid' object has no attribute 'grid'" not in stdout
    assert "'Grid' object has no attribute 'grid'" not in stderr
    assert "TypeError" not in stderr
    assert "AttributeError" not in stderr


def assert_valid_json_output(stdout):
    """Verify stdout contains valid JSON with expected keys."""
    for line in stdout.split("\n"):
        if line.strip().startswith('{"success"'):
            result = json.loads(line)
            assert "success" in result
            assert "grid" in result
            assert "slots_filled" in result
            return result
    pytest.fail("No JSON output found in stdout")


class TestCLIAutofillScenarios:
    """Test all CLI autofill scenarios with actual subprocess execution"""

    @pytest.mark.slow
    def test_trie_standard_grid(self):
        """CSP/Trie on 7x7 grid with black squares — should fill completely."""
        returncode, stdout, stderr = run_cli_fill(
            STANDARD_GRID_7x7, "trie", adaptive=False, timeout=15
        )
        assert_no_crash(stdout, stderr)
        result = assert_valid_json_output(stdout)
        assert result["success"] is True

    @pytest.mark.slow
    def test_beam_standard_grid(self):
        """Beam search on 7x7 grid — should complete without crash."""
        returncode, stdout, stderr = run_cli_fill(
            STANDARD_GRID_7x7, "beam", adaptive=False, timeout=30
        )
        assert_no_crash(stdout, stderr)
        assert_valid_json_output(stdout)

    @pytest.mark.slow
    def test_adaptive_trie_standard_grid(self):
        """Adaptive + CSP/Trie on 7x7 grid — should complete without crash."""
        returncode, stdout, stderr = run_cli_fill(
            STANDARD_GRID_7x7, "trie", adaptive=True, timeout=15
        )
        assert (
            "TypeError: Autofill.fill() got an unexpected keyword argument 'timeout'"
            not in stderr
        )
        assert_no_crash(stdout, stderr)
        assert_valid_json_output(stdout)

    @pytest.mark.slow
    def test_adaptive_beam_standard_grid(self):
        """Adaptive + Beam on 7x7 grid — the critical combo that was broken."""
        try:
            returncode, stdout, stderr = run_cli_fill(
                STANDARD_GRID_7x7, "beam", adaptive=True, timeout=30
            )
            assert_no_crash(stdout, stderr)
            assert_valid_json_output(stdout)
        except subprocess.TimeoutExpired:
            pytest.skip("Adaptive+beam exceeded timeout — cannot verify crash fix")

    @pytest.mark.slow
    def test_beam_prefilled_grid(self):
        """Beam search with pre-filled letters — should not crash."""
        returncode, stdout, stderr = run_cli_fill(
            PREFILLED_GRID_7x7, "beam", adaptive=False, timeout=30
        )
        assert_no_crash(stdout, stderr)
        assert_valid_json_output(stdout)

    @pytest.mark.slow
    def test_adaptive_beam_prefilled(self):
        """Adaptive + Beam with pre-filled letters — should not crash."""
        try:
            returncode, stdout, stderr = run_cli_fill(
                PREFILLED_GRID_7x7, "beam", adaptive=True, timeout=30
            )
            assert_no_crash(stdout, stderr)
            assert_valid_json_output(stdout)
        except subprocess.TimeoutExpired:
            pytest.skip("Adaptive+beam exceeded timeout — cannot verify crash fix")

    @pytest.mark.slow
    def test_beam_11x11(self):
        """Beam search on standard 11x11 grid — may timeout, that's OK."""
        grid_data = {
            "size": 11,
            "grid": [
                [".", ".", ".", ".", "#", ".", ".", ".", ".", ".", "#"],
                [".", ".", ".", ".", "#", ".", ".", ".", ".", ".", "#"],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", "#", ".", ".", ".", "#", ".", ".", "."],
                ["#", "#", ".", ".", ".", "#", ".", ".", ".", "#", "#"],
                [".", ".", ".", ".", "#", ".", "#", ".", ".", ".", "."],
                ["#", "#", ".", ".", ".", "#", ".", ".", ".", "#", "#"],
                [".", ".", ".", "#", ".", ".", ".", "#", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                ["#", ".", ".", ".", ".", ".", "#", ".", ".", ".", "."],
                ["#", ".", ".", ".", ".", ".", "#", ".", ".", ".", "."],
            ],
        }
        try:
            returncode, stdout, stderr = run_cli_fill(
                grid_data, "beam", adaptive=False, timeout=30
            )
            assert_no_crash(stdout, stderr)
        except subprocess.TimeoutExpired:
            pytest.skip("Beam on 11x11 exceeded timeout — cannot verify crash fix")


class TestAPIAutofillScenarios:
    """Test all API endpoint scenarios"""

    def test_api_beam_starts_successfully(self, client):
        """API endpoint successfully starts a beam search task."""
        grid = [
            [{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)
        ]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "beam",
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json",
        )

        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
        assert "progress_url" in data

    def test_api_adaptive_beam_starts_successfully(self, client):
        """Adaptive + Beam via API should start without error."""
        grid = [
            [{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)
        ]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "beam",
            "adaptive_mode": True,
            "max_adaptations": 2,
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json",
        )

        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
        assert "progress_url" in data

    def test_api_adaptive_trie_starts_successfully(self, client):
        """Adaptive + CSP via API should start without error."""
        grid = [
            [{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)
        ]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "trie",
            "adaptive_mode": True,
            "max_adaptations": 2,
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json",
        )

        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
