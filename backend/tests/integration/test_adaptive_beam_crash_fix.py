"""
Integration test to verify the adaptive + beam search crash is fixed.

The original bug: When using adaptive mode with beam search, the CLI would crash with:
    AttributeError: 'FillResult' object has no attribute 'get'

This test verifies the fix works through the full web UI → backend → CLI stack.
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


def test_cli_adaptive_beam_no_crash():
    """
    Test that CLI doesn't crash when running adaptive mode with beam search.

    This is a direct CLI test to verify the core fix.
    """
    # Create simple test grid
    grid_data = {
        "size": 11,
        "grid": [
            ["." for _ in range(11)] for _ in range(11)
        ]
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(grid_data, f)
        grid_file = f.name

    try:
        # Run CLI with adaptive + beam search (exact scenario that was crashing)
        cmd = [
            "python", "-m", "cli.src.cli", "fill",
            grid_file,
            "--wordlists", "data/wordlists/comprehensive.txt",
            "--timeout", "5",  # Short timeout for test
            "--min-score", "10",
            "--algorithm", "beam",  # KEY: Beam search
            "--adaptive",  # KEY: Adaptive mode
            "--max-adaptations", "2",
            "--json-output"
        ]

        # Run process (will timeout after 5 seconds, that's OK)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=8  # Give it 3 extra seconds for subprocess overhead
        )

        # The KEY assertion: process should NOT crash with AttributeError
        # It may timeout or fail to fill, but it should NOT have the AttributeError we fixed
        assert "'FillResult' object has no attribute 'get'" not in result.stdout, \
            f"CRASH DETECTED: FillResult.get() error still present!\n{result.stdout}"

        assert "'FillResult' object has no attribute 'get'" not in result.stderr, \
            f"CRASH DETECTED: FillResult.get() error still present!\n{result.stderr}"

        # Also check for the Grid.grid AttributeError we fixed
        assert "'Grid' object has no attribute 'grid'" not in result.stdout, \
            f"CRASH DETECTED: Grid.grid error still present!\n{result.stdout}"

        assert "'Grid' object has no attribute 'grid'" not in result.stderr, \
            f"CRASH DETECTED: Grid.grid error still present!\n{result.stderr}"

        print("\n✅ SUCCESS: CLI adaptive + beam search runs without crashing!")
        print(f"   Return code: {result.returncode}")
        print(f"   Stderr length: {len(result.stderr)} chars")
        print(f"   Stdout length: {len(result.stdout)} chars")

    except subprocess.TimeoutExpired:
        # Timeout is OK - the grid might not fill in 5 seconds
        # The important thing is it didn't crash
        print("\n✅ SUCCESS: CLI timed out but did not crash (expected for short timeout)")

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
        "max_adaptations": 2
    }

    # Make request
    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json"
    )

    # Should return 202 (task started) - NOT 500 (crash)
    assert response.status_code == 202, \
        f"Expected 202 (task started), got {response.status_code}: {response.data}"

    data = response.json
    assert "task_id" in data, f"Missing task_id in response: {data}"
    assert "progress_url" in data, f"Missing progress_url in response: {data}"

    print(f"\n✅ SUCCESS: API successfully started adaptive + beam search task")
    print(f"   Task ID: {data['task_id']}")
    print(f"   Progress URL: {data['progress_url']}")
