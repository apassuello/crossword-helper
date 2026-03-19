"""
Comprehensive integration test suite for all autofill scenarios.

Tests the full stack: Backend API → CLI subprocess → Autofill algorithms

This suite ensures that all combinations of:
- Algorithms (trie, beam, hybrid)
- Adaptive mode (on/off)
- Grid states (empty, pre-filled, with theme words)
- Grid sizes (11×11, 15×15)

...work correctly without crashes.
"""

import pytest
import json
import subprocess
import tempfile
import os
from backend.app import create_app


@pytest.fixture
def client():
    """Create Flask test client"""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_empty_grid(size):
    """Helper to create empty grid"""
    return {
        "size": size,
        "grid": [
            ["." for _ in range(size)] for _ in range(size)
        ]
    }


def run_cli_fill(grid_data, algorithm, adaptive=False, max_adaptations=2, timeout=30):
    """
    Helper to run CLI fill command and capture output.

    Returns:
        tuple: (return_code, stdout, stderr)
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name

    try:
        cmd = [
            "python", "-m", "cli.src.cli", "fill",
            grid_file,
            "--wordlists", "data/wordlists/comprehensive.txt",
            "--timeout", str(timeout),
            "--min-score", "10",
            "--algorithm", algorithm,
            "--json-output"
        ]

        if adaptive:
            cmd.append("--adaptive")
            cmd.extend(["--max-adaptations", str(max_adaptations)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10  # Add buffer
        )

        return result.returncode, result.stdout, result.stderr

    finally:
        if os.path.exists(grid_file):
            os.unlink(grid_file)


class TestCLIAutofillScenarios:
    """Test all CLI autofill scenarios with actual subprocess execution"""

    def test_baseline_trie_empty_11x11(self):
        """
        Baseline: CSP/Trie algorithm on empty 11×11 grid (no adaptive)
        Expected: Should complete without crash (partial fill OK)
        """
        grid_data = create_empty_grid(11)
        returncode, stdout, stderr = run_cli_fill(grid_data, "trie", adaptive=False)

        # Should not crash
        assert "'FillResult' object has no attribute 'get'" not in stdout
        assert "'FillResult' object has no attribute 'get'" not in stderr
        assert "'Grid' object has no attribute 'grid'" not in stdout
        assert "'Grid' object has no attribute 'grid'" not in stderr
        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr

        # Should have valid JSON output
        try:
            # Find JSON output (last line that looks like JSON)
            for line in stdout.split('\n'):
                if line.strip().startswith('{"success"'):
                    result = json.loads(line)
                    assert "success" in result
                    assert "grid" in result
                    assert "slots_filled" in result
                    break
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}")

    @pytest.mark.slow
    def test_beam_only_empty_11x11(self):
        """
        Beam search only on empty 11×11 grid (no adaptive)
        Expected: Should complete without crash
        """
        grid_data = create_empty_grid(11)
        returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=False, timeout=30)

        # Should not crash
        assert "'FillResult' object has no attribute 'get'" not in stdout
        assert "'FillResult' object has no attribute 'get'" not in stderr
        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr

        # Should have JSON output
        assert '"success"' in stdout
        assert '"grid"' in stdout

    def test_adaptive_trie_empty_11x11(self):
        """
        Adaptive mode with CSP/Trie on empty 11×11 grid
        Expected: Should complete without crash (THIS WAS BROKEN BEFORE)
        """
        grid_data = create_empty_grid(11)
        returncode, stdout, stderr = run_cli_fill(grid_data, "trie", adaptive=True, timeout=30)

        # KEY ASSERTION: No TypeError about 'timeout' parameter
        assert "TypeError: Autofill.fill() got an unexpected keyword argument 'timeout'" not in stderr
        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr

        # Should have valid JSON output
        assert '"success"' in stdout
        assert '"grid"' in stdout

    @pytest.mark.slow
    def test_adaptive_beam_empty_11x11(self):
        """
        **THE CRITICAL TEST**: Adaptive mode + Beam search on empty 11×11 grid
        Expected: Should complete without crash (THIS WAS THE MAIN FAILURE CASE)
        """
        grid_data = create_empty_grid(11)
        returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=True, timeout=30)

        # KEY ASSERTIONS: No crashes
        assert "TypeError: Autofill.fill() got an unexpected keyword argument 'timeout'" not in stderr
        assert "'FillResult' object has no attribute 'get'" not in stdout
        assert "'FillResult' object has no attribute 'get'" not in stderr
        assert "'FillResult' object has no attribute 'success'" not in stderr
        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr

        # Should have valid JSON output
        assert '"success"' in stdout
        assert '"grid"' in stdout

        print("\n✅ SUCCESS: Adaptive + Beam search works without crashing!")

    @pytest.mark.slow
    def test_beam_prefilled_grid(self):
        """
        Beam search with pre-filled letters
        Expected: Should complete without crash
        """
        grid_data = {
            "size": 11,
            "grid": [
                ["C", "A", "T", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
            ]
        }

        returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=False, timeout=30)

        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr
        assert '"success"' in stdout

    @pytest.mark.slow
    def test_adaptive_beam_prefilled(self):
        """
        Adaptive + Beam with pre-filled letters
        Expected: Should complete without crash
        """
        grid_data = {
            "size": 11,
            "grid": [
                ["C", "A", "T", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
            ]
        }

        returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=True, timeout=30)

        assert "TypeError" not in stderr
        assert "AttributeError" not in stderr
        assert '"success"' in stdout

    @pytest.mark.slow
    def test_beam_15x15(self):
        """
        Beam search on larger 15×15 grid
        Expected: Should complete without crash (may timeout, that's OK)
        """
        grid_data = create_empty_grid(15)

        try:
            returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=False, timeout=30)

            # Even if timeout or partial fill, should not crash
            assert "TypeError" not in stderr
            assert "AttributeError" not in stderr

        except subprocess.TimeoutExpired:
            # Timeout is acceptable for 15×15 grid
            print("\n⚠️ 15×15 beam search timed out (expected for complex grid)")
            pass

    @pytest.mark.slow
    def test_adaptive_beam_15x15(self):
        """
        Adaptive + Beam on larger 15×15 grid
        Expected: Should complete without crash (may timeout, that's OK)
        """
        grid_data = create_empty_grid(15)

        try:
            returncode, stdout, stderr = run_cli_fill(grid_data, "beam", adaptive=True, timeout=30)

            # Even if timeout or partial fill, should not crash
            assert "TypeError" not in stderr
            assert "AttributeError" not in stderr

        except subprocess.TimeoutExpired:
            # Timeout is acceptable for 15×15 grid
            print("\n⚠️ 15×15 adaptive+beam timed out (expected for complex grid)")
            pass


class TestAPIAutofillScenarios:
    """Test all API endpoint scenarios"""

    def test_api_beam_starts_successfully(self, client):
        """
        Test that API endpoint successfully starts a beam search task
        """
        grid = [[{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "beam"
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        # Should return 202 (task started)
        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
        assert "progress_url" in data

    def test_api_adaptive_beam_starts_successfully(self, client):
        """
        **CRITICAL API TEST**: Adaptive + Beam via API should start without error
        """
        grid = [[{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "beam",
            "adaptive_mode": True,
            "max_adaptations": 2
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        # Should return 202 (task started) - NOT 500 (crash)
        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
        assert "progress_url" in data

        print(f"\n✅ SUCCESS: API adaptive+beam started with task_id={data['task_id']}")

    def test_api_adaptive_trie_starts_successfully(self, client):
        """
        Test that API endpoint successfully starts an adaptive + CSP task
        """
        grid = [[{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)]

        request_data = {
            "size": 11,
            "grid": grid,
            "wordlists": ["comprehensive"],
            "timeout": 30,
            "min_score": 10,
            "algorithm": "trie",
            "adaptive_mode": True,
            "max_adaptations": 2
        }

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(request_data),
            content_type="application/json"
        )

        # Should return 202 (task started)
        assert response.status_code == 202
        data = response.json
        assert "task_id" in data
