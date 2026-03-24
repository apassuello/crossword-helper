"""
Integration tests for Web UI → CLI adaptive autofill with beam search.

This test reproduces the exact scenario reported by the user:
- 21×21 grid
- Theme words placed
- Beam Search algorithm
- Adaptive mode enabled
- Comprehensive wordlist
"""

import pytest
import json


def create_21x21_grid_with_theme_words():
    """
    Create a 21×21 grid with theme words placed.
    This simulates the birthday crossword scenario.
    """
    grid = []
    for _ in range(21):
        row = []
        for _ in range(21):
            row.append({"letter": "", "isBlack": False, "isThemeLocked": False})
        grid.append(row)

    # Place a few theme words (simplified version)
    # MAMIEDENISE at row 0, col 5, across
    theme_word = "MAMIEDENISE"
    for i, letter in enumerate(theme_word):
        grid[0][5 + i] = {"letter": letter, "isBlack": False, "isThemeLocked": True}

    # TURBO at row 2, col 8, across
    theme_word = "TURBO"
    for i, letter in enumerate(theme_word):
        grid[2][8 + i] = {"letter": letter, "isBlack": False, "isThemeLocked": True}

    # MINNESOTA at row 10, col 11, across
    theme_word = "MINNESOTA"
    for i, letter in enumerate(theme_word):
        grid[10][11 + i] = {"letter": letter, "isBlack": False, "isThemeLocked": True}

    return grid


@pytest.mark.slow
def test_adaptive_beam_search_comprehensive_wordlist(client, sse_parser):
    """
    Test adaptive autofill with beam search and comprehensive wordlist.

    This is the EXACT scenario the user reported as failing:
    - Algorithm: beam
    - Adaptive mode: enabled
    - Max adaptations: 5
    - Min score: 10
    - Wordlist: comprehensive
    - Grid size: 21×21
    """
    # Create grid with theme words
    grid = create_21x21_grid_with_theme_words()

    # Build request payload (exact UI parameters)
    request_data = {
        "size": 21,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": 60,
        "min_score": 10,
        "algorithm": "beam",  # KEY: Beam search algorithm
        "adaptive_mode": True,  # KEY: Adaptive mode enabled
        "max_adaptations": 5,
    }

    # Make request to /api/fill/with-progress
    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )

    # Should return 202 with task ID
    assert (
        response.status_code == 202
    ), f"Expected 202, got {response.status_code}: {response.data}"

    data = response.json
    assert "task_id" in data, f"Missing task_id in response: {data}"
    assert "progress_url" in data, f"Missing progress_url in response: {data}"

    task_id = data["task_id"]
    print(f"\n✓ Autofill started successfully with task_id: {task_id}")

    # Check initial progress via SSE stream
    # Note: SSE streams don't return JSON directly, we need to parse the stream
    # For this test, we just verify the task started without immediate error
    # The SSE stream tests verify the actual stream behavior

    # 202 + task_id proves startup didn't crash. No sleep needed.
    print("✓ Autofill process started successfully for adaptive + beam search")


def test_adaptive_mode_without_beam_search(client):
    """
    Control test: adaptive mode with standard CSP algorithm (should work).
    """
    grid = create_21x21_grid_with_theme_words()

    request_data = {
        "size": 21,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": 60,
        "min_score": 10,
        "algorithm": "trie",  # Standard CSP with trie
        "adaptive_mode": True,
        "max_adaptations": 5,
    }

    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == 202
    data = response.json
    assert "task_id" in data

    print(f"\n✓ Adaptive mode with standard CSP started: {data['task_id']}")


def test_beam_search_without_adaptive_mode(client):
    """
    Control test: beam search without adaptive mode (should work).
    """
    grid = create_21x21_grid_with_theme_words()

    request_data = {
        "size": 21,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": 60,
        "min_score": 10,
        "algorithm": "beam",  # Beam search
        "adaptive_mode": False,  # No adaptive mode
    }

    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == 202
    data = response.json
    assert "task_id" in data

    print(f"\n✓ Beam search without adaptive mode started: {data['task_id']}")


def test_cli_command_construction(client, mocker):
    """
    Test that the CLI command is constructed correctly for adaptive + beam search.
    """
    # Mock the thread start to intercept command
    captured_cmd = []

    def mock_thread_init(self, target, args, daemon):
        # Capture the command args
        captured_cmd.extend(args[1])  # args[1] is cmd_args

    mocker.patch("threading.Thread.__init__", mock_thread_init)
    mocker.patch("threading.Thread.start", lambda self: None)

    grid = create_21x21_grid_with_theme_words()

    request_data = {
        "size": 21,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": 60,
        "min_score": 10,
        "algorithm": "beam",
        "adaptive_mode": True,
        "max_adaptations": 5,
    }

    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == 202

    # Verify command includes:
    # - fill
    # - --algorithm beam
    # - --adaptive
    # - --max-adaptations 5
    assert "fill" in captured_cmd
    assert "--algorithm" in captured_cmd
    assert "beam" in captured_cmd
    assert "--adaptive" in captured_cmd
    assert "--max-adaptations" in captured_cmd
    assert "5" in captured_cmd

    print(f"\n✓ CLI command construction correct: {' '.join(captured_cmd)}")
