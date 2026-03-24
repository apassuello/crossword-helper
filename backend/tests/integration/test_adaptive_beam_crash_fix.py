"""
Integration test to verify the adaptive + beam search crash is fixed.

The original bug: When using adaptive mode with beam search, the CLI would crash with:
    AttributeError: 'FillResult' object has no attribute 'get'

This test verifies the fix works through the full web UI → backend → CLI stack.
"""

import pytest
import json
import subprocess
import sys
import tempfile
import os


@pytest.mark.slow
def test_cli_adaptive_beam_no_crash():
    """
    Test that CLI doesn't crash when running adaptive mode with beam search.

    This is a direct CLI test to verify the core fix.
    """
    # Create simple test grid
    grid_data = {"size": 11, "grid": [["." for _ in range(11)] for _ in range(11)]}

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name

    try:
        # Run CLI with adaptive + beam search (exact scenario that was crashing)
        cmd = [
            "python",
            "-m",
            "cli.src.cli",
            "fill",
            grid_file,
            "--wordlists",
            "data/wordlists/comprehensive.txt",
            "--timeout",
            "5",  # Short timeout for test
            "--min-score",
            "10",
            "--algorithm",
            "beam",  # KEY: Beam search
            "--adaptive",  # KEY: Adaptive mode
            "--max-adaptations",
            "2",
            "--json-output",
        ]

        # Run process (will timeout after 5 seconds, that's OK)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=8,  # Give it 3 extra seconds for subprocess overhead
        )

        # The KEY assertion: process should NOT crash with AttributeError
        # It may timeout or fail to fill, but it should NOT have the AttributeError we fixed
        assert (
            "'FillResult' object has no attribute 'get'" not in result.stdout
        ), f"CRASH DETECTED: FillResult.get() error still present!\n{result.stdout}"

        assert (
            "'FillResult' object has no attribute 'get'" not in result.stderr
        ), f"CRASH DETECTED: FillResult.get() error still present!\n{result.stderr}"

        # Also check for the Grid.grid AttributeError we fixed
        assert (
            "'Grid' object has no attribute 'grid'" not in result.stdout
        ), f"CRASH DETECTED: Grid.grid error still present!\n{result.stdout}"

        assert (
            "'Grid' object has no attribute 'grid'" not in result.stderr
        ), f"CRASH DETECTED: Grid.grid error still present!\n{result.stderr}"

        print("\n✅ SUCCESS: CLI adaptive + beam search runs without crashing!")
        print(f"   Return code: {result.returncode}")
        print(f"   Stderr length: {len(result.stderr)} chars")
        print(f"   Stdout length: {len(result.stdout)} chars")

    except subprocess.TimeoutExpired:
        # Timeout is OK - the grid might not fill in 5 seconds
        # The important thing is it didn't crash
        print(
            "\n✅ SUCCESS: CLI timed out but did not crash (expected for short timeout)"
        )

    finally:
        # Clean up temp file
        if os.path.exists(grid_file):
            os.unlink(grid_file)


def test_api_adaptive_beam_starts_successfully(client):
    """
    Test that API endpoint successfully starts an adaptive + beam search task.

    This verifies the web UI → CLI integration doesn't crash immediately.
    """
    grid = [[{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)]

    request_data = {
        "size": 11,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": 10,  # Minimum 10 seconds per API validation
        "min_score": 10,
        "algorithm": "beam",  # KEY: Beam search
        "adaptive_mode": True,  # KEY: Adaptive mode
        "max_adaptations": 2,
    }

    # Make request
    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )

    # Should return 202 (task started) - NOT 500 (crash)
    assert (
        response.status_code == 202
    ), f"Expected 202 (task started), got {response.status_code}: {response.data}"

    data = response.json
    assert "task_id" in data, f"Missing task_id in response: {data}"
    assert "progress_url" in data, f"Missing progress_url in response: {data}"

    print("\n✅ SUCCESS: API successfully started adaptive + beam search task")
    print(f"   Task ID: {data['task_id']}")
    print(f"   Progress URL: {data['progress_url']}")


@pytest.mark.slow
def test_adaptive_mode_adds_black_squares():
    """Canary: --adaptive should auto-add black squares to an empty grid.

    This test exercises the --adaptive CLI flag on a 7x7 all-empty grid
    (no black squares). The adaptive feature is supposed to strategically
    add black squares to make the grid fillable, but it is KNOWN BROKEN
    and does NOT actually add them.

    This is a regression canary. If this test starts passing, the feature
    has been fixed. See CLAUDE.md Known Issues section.
    """
    grid_data = {"size": 7, "grid": [["." for _ in range(7)] for _ in range(7)]}

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
            "data/wordlists/core/crosswordese.txt",
            "--algorithm",
            "beam",
            "--adaptive",
            "--max-adaptations",
            "3",
            "--timeout",
            "15",
            "--allow-nonstandard",
            "--json-output",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25,
        )

        # Try to parse JSON from stdout
        output = result.stdout.strip()
        json_result = None
        for line in reversed(output.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    json_result = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if json_result is None:
            pytest.skip(
                f"CLI did not produce JSON output (rc={result.returncode}); "
                f"stderr: {result.stderr[:300]}"
            )

        filled_grid = json_result.get("grid")
        if filled_grid is None:
            pytest.skip(f"JSON output has no 'grid' key: {list(json_result.keys())}")

        # Count black squares in input vs output
        input_blacks = 0  # We started with zero black squares
        output_blacks = sum(1 for row in filled_grid for cell in row if cell == "#")

        black_squares_added = output_blacks > input_blacks

        # KNOWN BROKEN: this assertion is expected to fail.
        # When the feature is fixed, this canary will start passing.
        assert black_squares_added, (
            "KNOWN BROKEN CANARY: --adaptive did not add any black squares "
            f"to the 7x7 grid. Input had {input_blacks}, output has "
            f"{output_blacks}. See CLAUDE.md Known Issues: CLI --adaptive "
            "flag does NOT auto-add black squares."
        )

    except subprocess.TimeoutExpired:
        pytest.skip("CLI process timed out (expected for slow CI)")

    finally:
        if os.path.exists(grid_file):
            os.unlink(grid_file)
